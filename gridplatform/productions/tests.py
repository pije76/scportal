# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from mock import patch

import pytz
from django.test import TestCase
from django.test.utils import override_settings
from django.test import RequestFactory
from django.core.exceptions import ValidationError

from gridplatform.providers.models import Provider
from gridplatform.customers.models import Customer
from gridplatform.utils.samples import RangedSample
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import condense
from gridplatform.users.models import User
from gridplatform.rest.serializers import HyperlinkedIdentityField
from gridplatform.rest.serializers import HyperlinkedRelatedField
from gridplatform.trackuser import replace_customer

from .models import SingleValuePeriod
from .models import Production
from .models import ProductionGroup
from . import viewsets


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            production_b_unit_plain='Pöp Cørn',
            production_c_unit_plain='Ikeä')

        # simulate how ModelForm.instance would be initialized.
        with replace_customer(self.customer):
            self.production = Production()

    def test_unit_choices(self):
        self.assertNotIn('production_a', self.production.unit_choices)
        self.assertIn('production_b', self.production.unit_choices)

    def test_get_unit_display(self):
        self.production.unit = 'production_b'
        unicode(self.production.get_unit_display())

    def test_clean_happy(self):
        self.production.unit = 'production_b'
        self.production.clean()

    def test_clean_invalid_unit(self):
        self.production.unit = 'production_a'
        with self.assertRaises(ValidationError) as ctx:
            self.production.clean()
        self.assertIn('unit', ctx.exception.message_dict)

    def test_clean_unit_change(self):
        self.production.unit = 'production_c'
        self.production.save()
        self.production.unit = 'production_b'
        with self.assertRaises(ValidationError) as ctx:
            self.production.clean()
        self.assertIn('unit', ctx.exception.message_dict)


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionGroupTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()

    def test_production_sequence_integration(self):
        productiongroup = ProductionGroup.objects.create(
            customer=self.customer,
            unit='production_a')

        productiongroup.productions.add(
            Production.objects.create(
                unit='production_a',
                customer=self.customer))
        productiongroup.productions.add(
            Production.objects.create(
                unit='production_a',
                customer=self.customer))

        productions = list(productiongroup.productions.all())
        self.assertEqual(len(productions), 3)  # the above + historical

        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        patched_development_sequence = patch.object(
            Production,
            'development_sequence',
            return_value=[
                RangedSample(
                    from_timestamp, to_timestamp,
                    PhysicalQuantity(42, 'production_a'))],
            autospec=True)

        with patched_development_sequence as mock:
            result = list(
                productiongroup.production_sequence(
                    from_timestamp, to_timestamp, condense.DAYS))

        mock.assert_any_call(
            productions[0], from_timestamp, to_timestamp, condense.DAYS)
        mock.assert_any_call(
            productions[1], from_timestamp, to_timestamp, condense.DAYS)
        mock.assert_any_call(
            productions[2], from_timestamp, to_timestamp, condense.DAYS)

        self.assertEqual(mock.call_count, 3)

        self.assertEqual(
            [
                RangedSample(
                    from_timestamp, to_timestamp,
                    PhysicalQuantity(126, 'production_a'))],
            result)


def get_url_mock(self, obj, view_name, request, format):
    """Mock used to render HyperlinkedModelSerializer"""
    return "/%s" % view_name


@override_settings(
    ENCRYPTION_TESTMODE=True)
class ProductionGroupViewSetTest(TestCase):

    def setUp(self):
        self.provider = Provider.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.customer = Customer.objects.create(
            timezone=self.timezone,
            production_a_unit_plain='whatever')

        self.factory = RequestFactory()

        self.productiongroup = ProductionGroup.objects.create(
            customer=self.customer,
            name_plain='Die Produktionsgruppe',
            unit='production_a')

        production = Production.objects.create(
            unit='production_a',
            customer=self.customer)
        self.productiongroup.productions.add(production)

        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 10, 1)),
            datasequence=production,
            value=1024,
            unit='production_a')

    def test_get(self):
        request = self.factory.get('/', content_type='application/json')
        request.user = User(name_plain='test user')
        view = viewsets.ProductionGroup.as_view(actions={'get': 'list'})
        with patch.object(
            HyperlinkedIdentityField, 'get_url',
            get_url_mock), \
                patch.object(
                    HyperlinkedRelatedField, 'get_url',
                    get_url_mock):
            response = view(request, pk=self.productiongroup.id)
            self.assertContains(response, 'Die Produktionsgruppe')

    def test_get_hourly(self):
        request = self.factory.get(
            '/?date=2014-08-19', content_type='application/json')
        request.user = User(name_plain='test user')

        view = viewsets.ProductionGroup.as_view(actions={'get': 'hourly'})
        with patch.object(
            HyperlinkedIdentityField, 'get_url',
            get_url_mock), \
                patch.object(
                    HyperlinkedRelatedField, 'get_url',
                    get_url_mock):
            response = view(request, pk=self.productiongroup.id)
            self.assertContains(response, '2014-08-19T00:00:00+02:00')
