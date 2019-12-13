# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module contains tests for the display_indexes Django app.
"""

from decimal import Decimal
import datetime

from django.test.utils import override_settings
from django.test import TestCase

from mock import patch
import pytz
import unittest

from gridplatform.customers.models import Customer
from gridplatform.encryption.shell import Request
from legacy.indexes.models import Index
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.users.models import User
from gridplatform.utils import condense
from gridplatform.utils import utilitytypes
from gridplatform.utils.relativetimedelta import RelativeTimeDelta

from .views import graph_task


@override_settings(ENCRYPTION_TESTMODE=True)
class ViewTest(TestCase):
    """
    Tests for the view module.
    """
    fixtures = ["manage_indexes_test.json"]

    def setUp(self):
        """
        Setup test fixture as if we are logged in as some user called
        super.
        """
        self.client.post('/login/', {"username": "super",
                                     'password': "123"})
        self.customer = User.objects.get(
            id=self.client.session["_auth_user_id"]).customer
        self.request = Request('super', '123')

    @unittest.skip("self.client session state cannot decrypt these objects...")
    def test_index_view(self):
        self.index_el = Index.objects.create(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="Test electricity index for customer",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SEASONS,
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            timezone='Europe/Copenhagen')

        self.another_customer_index = Index.objects.create(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="Test index for another customer",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SEASONS,
            customer=Customer.objects.create(),
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            timezone='Europe/Copenhagen')

        response = self.client.get('/overview/indexes/')
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, self.index_el.name)
        self.assertNotContains(response, self.another_customer_index.name)

    def test_detail_view_success(self):
        self.index_el = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="Test electricity index for customer",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SEASONS,
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            timezone=self.customer.timezone)
        self.index_el._exclude_field_from_validation = ['name']
        self.index_el.save()

        customer = Customer()
        customer.save()

        response = self.client.get('/overview/indexes/%s/' % self.index_el.id)
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, self.index_el.name)

    def test_graph(self):
        """
        Test that the Index graph displays the exact hourly tarriffs
        for the last 24 hours.  This test is expected to fail for part
        of a unfortunate single microsecond every hour, i.e. with
        probability M{< 1/3600000}.
        """
        # Create an index and populate it with some recognizable
        # values.
        timezone = pytz.timezone("Europe/Copenhagen")
        index = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="Nordpool spot-tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            timezone=timezone,
            data_format=Index.SPOT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        index.save()
        start_time = timezone.localize(
            datetime.datetime.now()).replace(
            hour=0, minute=0, second=0, microsecond=0)
        current_time = start_time
        for i in range(24):
            index.entry_set.create(
                from_timestamp=current_time,
                to_timestamp=current_time + datetime.timedelta(hours=1),
                value=Decimal(i))
            current_time += datetime.timedelta(hours=1)

        # Aquire the JSON data defining the graph.
        response = self.client.get("/overview/indexes/graph/%d/" % index.id)
        self.assertEqual(response.status_code, 200)

        # Verify that the recognizable values are held within the
        # graph.
        for i in range(24):
            self.assertIn(str(i), response.content)

    def test_async_graph_last_24h(self):
        class PhonyAsync:
            id = 42
            status = 'PHONY'

        timezone = pytz.timezone("Europe/Copenhagen")
        to_timestamp = condense.floor(
            datetime.datetime.now(pytz.utc) + RelativeTimeDelta(hours=1),
            RelativeTimeDelta(hours=1),
            timezone)
        from_timestamp = to_timestamp - RelativeTimeDelta(hours=24)
        index = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="Nordpool spot-tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            timezone=timezone,
            data_format=Index.SPOT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        index.save()

        with patch.object(graph_task, 'delay',
                          return_value=PhonyAsync()) as mock:
            result = self.client.post(
                '/overview/indexes/async_graph_last_24h/%d/' % index.id, {})
            self.assertContains(result, PhonyAsync.id)
            self.assertContains(result, PhonyAsync.status)

        mock.assert_called_with('%d' % index.id, from_timestamp, to_timestamp)

    def test_embedded_url_in_slide_in_menu(self):
        """
        This test validates that the links for the indexes in the
        slide-in menu contains the from_date and to_date in the url.
        """
        index = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="Test index",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SEASONS,
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            timezone='Europe/Copenhagen')
        index.save()

        response = self.client.get('/overview/indexes/')
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, index.name_plain)

        response = self.client.get(
            '/overview/indexes/%s/?from_date=2012-01-01&to_date=2012-12-31'
            % index.id)
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, index.name_plain)
        self.assertContains(
            response,
            '/overview/indexes/%s/?from_date=2012-01-01&to_date=2012-12-31'
            % index.id)
