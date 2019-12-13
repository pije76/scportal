# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.test.utils import override_settings
import pytz

from gridplatform.customer_datasources.models import CustomerDataSource
from gridplatform.datasources.models import RawData
from gridplatform.customers.models import Customer
from gridplatform.providers.models import Provider
from gridplatform.utils.samples import RangedSample
from gridplatform.utils.unitconversion import PhysicalQuantity

from .energyconversion import EnergyPerVolumeDataSequence
from .energyconversion import EnergyPerVolumePeriod


@override_settings(ENCRYPTION_TESTMODE=True)
class VolumeToEnergyConversionTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.timezone('Europe/Copenhagen'))
        self.conversion = EnergyPerVolumeDataSequence.objects.create(
            customer=self.customer)

    def test_value_sequence_no_periods(self):
        from_timestamp = self.customer.timezone.localize(
            datetime.datetime(2014, 1, 1))
        to_timestamp = self.customer.timezone.localize(
            datetime.datetime(2014, 1, 2))

        self.assertEqual(
            list(
                self.conversion.period_set.value_sequence(
                    from_timestamp, to_timestamp)),
            [])

    def test_value_sequence_data_before(self):
        from_timestamp = self.customer.timezone.localize(
            datetime.datetime(2014, 1, 1))
        to_timestamp = self.customer.timezone.localize(
            datetime.datetime(2014, 1, 2))

        datasource = CustomerDataSource.objects.create(
            customer=self.customer,
            unit='milliwatt*hour/meter^3')

        RawData.objects.bulk_create(
            [
                RawData(
                    datasource=datasource,
                    timestamp=from_timestamp - datetime.timedelta(hours=1),
                    value=3),
                RawData(
                    datasource=datasource,
                    timestamp=from_timestamp + datetime.timedelta(hours=7),
                    value=7)
            ])

        self.conversion.period_set.create(
            from_timestamp=from_timestamp,
            datasource=datasource)

        self.assertEqual(
            list(
                self.conversion.period_set.value_sequence(
                    from_timestamp, to_timestamp)),
            [
                RangedSample(
                    from_timestamp + datetime.timedelta(hours=h),
                    from_timestamp + datetime.timedelta(hours=h + 1),
                    PhysicalQuantity(3, 'milliwatt*hour/meter^3'))
                for h in range(7)] +
            [
                RangedSample(
                    from_timestamp + datetime.timedelta(hours=h),
                    from_timestamp + datetime.timedelta(hours=h + 1),
                    PhysicalQuantity(7, 'milliwatt*hour/meter^3'))
                for h in range(7, 24)])

    def test_value_sequence_data_before_missing(self):
        from_timestamp = self.customer.timezone.localize(
            datetime.datetime(2014, 1, 1))
        to_timestamp = self.customer.timezone.localize(
            datetime.datetime(2014, 1, 2))

        datasource = CustomerDataSource.objects.create(
            customer=self.customer,
            unit='milliwatt*hour/meter^3')

        RawData.objects.bulk_create(
            [
                RawData(
                    datasource=datasource,
                    timestamp=from_timestamp + datetime.timedelta(hours=1),
                    value=3),
                RawData(
                    datasource=datasource,
                    timestamp=from_timestamp + datetime.timedelta(hours=7),
                    value=7)
            ])

        self.conversion.period_set.create(
            from_timestamp=from_timestamp,
            datasource=datasource)

        self.assertEqual(
            list(
                self.conversion.period_set.value_sequence(
                    from_timestamp, to_timestamp)),
            [
                RangedSample(
                    from_timestamp + datetime.timedelta(hours=h),
                    from_timestamp + datetime.timedelta(hours=h + 1),
                    PhysicalQuantity(3, 'milliwatt*hour/meter^3'))
                for h in range(1, 7)] +
            [
                RangedSample(
                    from_timestamp + datetime.timedelta(hours=h),
                    from_timestamp + datetime.timedelta(hours=h + 1),
                    PhysicalQuantity(7, 'milliwatt*hour/meter^3'))
                for h in range(7, 24)])


@override_settings(ENCRYPTION_TESTMODE=True)
class VolumeToEnergyConversionPeriodTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.timezone('Europe/Copenhagen'))
        self.conversion = EnergyPerVolumeDataSequence.objects.create(
            customer=self.customer)

    def test_full_clean_detects_bad_unit(self):
        from_timestamp = self.customer.timezone.localize(
            datetime.datetime(2014, 1, 1))

        datasource = CustomerDataSource.objects.create(
            customer=self.customer,
            unit='milliwatt*hour')

        period = EnergyPerVolumePeriod(
            datasequence=self.conversion,
            from_timestamp=from_timestamp,
            datasource=datasource)

        with self.assertRaises(ValidationError):
            period.full_clean()
