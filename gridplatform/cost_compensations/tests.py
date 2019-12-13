# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import pytz

from django.test import TestCase
from django.test.utils import override_settings
from django.core.exceptions import ValidationError

from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.samples import RangedSample
from gridplatform.providers.models import Provider
from gridplatform.customers.models import Customer

from .models import CostCompensation
from .models import Period
from .models import FixedCompensationPeriod


@override_settings(ENCRYPTION_TESTMODE=True)
class CostCompensationTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()

    def test_unit_dkk(self):
        costcompensation = CostCompensation(
            customer=Customer.objects.create(currency_unit='currency_dkk'))
        self.assertTrue(PhysicalQuantity.compatible_units(
            'currency_dkk*joule^-1', costcompensation.unit))

    def test_unit_eur(self):
        costcompensation = CostCompensation(
            customer=Customer.objects.create(currency_unit='currency_eur'))
        self.assertTrue(PhysicalQuantity.compatible_units(
            'currency_eur*joule^-1', costcompensation.unit))


class PeriodTest(TestCase):
    def test_unicode_is_pure_virtual(self):
        period = Period()
        with self.assertRaises(NotImplementedError):
            unicode(period)


@override_settings(ENCRYPTION_TESTMODE=True)
class FixedCompensationPeriodTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(currency_unit='currency_dkk')
        self.costcompensation = CostCompensation(customer=self.customer)

    def test_unicode_without_to_timestamp(self):
        period = FixedCompensationPeriod(
            unit='currency_eur*kilowatt^-1*hour^-1',
            value=42,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)))

        self.assertNotIn('None', unicode(period))

    def test_unicode_with_to_timestamp(self):
        period = FixedCompensationPeriod(
            unit='currency_eur*kilowatt^-1*hour^-1',
            value=42,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))

        self.assertNotIn('None', unicode(period))

    def test_clean_happy(self):
        period = FixedCompensationPeriod(
            datasequence=self.costcompensation,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            value=42,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))
        period.clean()

    def test_clean_bad_unit(self):
        period = FixedCompensationPeriod(
            datasequence=self.costcompensation,
            unit='currency_eur*kilowatt^-1*hour^-1',
            value=42,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))
        with self.assertRaises(ValidationError) as raise_context:
            period.clean()
        self.assertIn('unit', raise_context.exception.error_dict)

    def test_value_sequence_integration(self):
        from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 2))
        period = FixedCompensationPeriod(
            datasequence=self.costcompensation,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            value=42,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp)
        self.assertEqual(
            [
                RangedSample(
                    from_timestamp + datetime.timedelta(hours=h),
                    from_timestamp + datetime.timedelta(hours=h + 1),
                    PhysicalQuantity(42, 'currency_dkk*kilowatt^-1*hour^-1'))
                for h in range(24)
            ],
            list(
                period._value_sequence(from_timestamp, to_timestamp)))
