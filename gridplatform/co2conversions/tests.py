# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

import pytz
from django.test import TestCase
from django.test.utils import override_settings
from django.core.exceptions import ValidationError

from gridplatform.providers.models import Provider
from gridplatform.customers.models import Customer
from gridplatform.consumptions.models import MainConsumption
from gridplatform.utils.utilitytypes import ENERGY_UTILITY_TYPE_CHOICES
from gridplatform.datasources.models import DataSource
from gridplatform.datasources.models import RawData
from gridplatform.utils.samples import RangedSample
from gridplatform.utils.unitconversion import PhysicalQuantity

from .models import Co2Conversion
from .models import DynamicCo2Conversion
from .models import FixedCo2Conversion


@override_settings(ENCRYPTION_TESTMODE=True)
class Co2ConversionManagerTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')

        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))

    def test_value_sequence_no_conversions(self):
        result = list(
            self.mainconsumption.co2conversion_set.value_sequence(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))))

        self.assertEqual(result, [])


@override_settings(ENCRYPTION_TESTMODE=True)
class Co2ConversionTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(timezone=self.timezone)

        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))

    def test_unicode_pure_virtual(self):
        with self.assertRaises(NotImplementedError):
            unicode(
                Co2Conversion(
                    mainconsumption=self.mainconsumption,
                    from_timestamp=self.timezone.localize(
                        datetime.datetime(2014, 1, 1)),
                    to_timestamp=self.timezone.localize(
                        datetime.datetime(2014, 1, 2))))

    def test_value_sequence_pure_virtual(self):
        conversion = Co2Conversion(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))
        with self.assertRaises(NotImplementedError):
            list(
                conversion._value_sequence(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2))))

    def test_clean_blank(self):
        conversion = Co2Conversion(
            mainconsumption=self.mainconsumption)
        conversion.clean()

    def test_clean_detects_overlaps(self):
        Co2Conversion.objects.create(
            mainconsumption=self.mainconsumption,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2000, 1, 1)))

        conversion = Co2Conversion(
            mainconsumption=self.mainconsumption,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)))

        with self.assertRaises(ValidationError):
            conversion.clean()

    def test_clean_detects_from_timestamp_invalid_resolution(self):
        conversion = Co2Conversion(
            mainconsumption=self.mainconsumption,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1, 1, 1)))

        with self.assertRaises(ValidationError) as e:
            conversion.clean()

        self.assertIn('from_timestamp', e.exception.message_dict)

    def test_clean_detects_to_timestamp_invalid_resolution(self):
        conversion = Co2Conversion(
            mainconsumption=self.mainconsumption,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2, 1, 1)))

        with self.assertRaises(ValidationError) as e:
            conversion.clean()

        self.assertIn('to_timestamp', e.exception.message_dict)


class DataSourceMock(DataSource):
    class Meta:
        proxy = True

    def __unicode__(self):
        return 'DATASOURCEMOCK'


@override_settings(ENCRYPTION_TESTMODE=True)
class DynamicCo2ConversionTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(timezone=self.timezone)

        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))

        self.datasource = DataSourceMock.objects.create(
            unit='gram*kilowatt^-1*hour^-1')

    def test_unicode(self):
        conversion = DynamicCo2Conversion(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            mainconsumption=self.mainconsumption,
            datasource=self.datasource)
        self.assertIn('DATASOURCEMOCK', unicode(conversion))

    def test_clean_happy(self):
        conversion = DynamicCo2Conversion(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            mainconsumption=self.mainconsumption,
            datasource=self.datasource)
        conversion.clean()

    def test_clean_detects_bad_unit(self):
        self.datasource.unit = 'gram*liter^-1'
        conversion = DynamicCo2Conversion(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            mainconsumption=self.mainconsumption,
            datasource=self.datasource)
        with self.assertRaises(ValidationError) as e:
            conversion.clean()

        self.assertIn('datasource', e.exception.message_dict)

    def test_value_sequence_empty(self):
        DynamicCo2Conversion.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            mainconsumption=self.mainconsumption,
            datasource=self.datasource)
        self.assertEqual(
            [],
            list(
                self.mainconsumption.co2conversion_set.value_sequence(
                    self.timezone.localize(
                        datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(
                        datetime.datetime(2014, 1, 2)))))

    def test_value_sequence(self):
        from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))
        self.datasource.rawdata_set.bulk_create(
            [
                RawData(
                    datasource=self.datasource,
                    timestamp=from_timestamp + datetime.timedelta(
                        minutes=5 * i),
                    value=i % 20)
                for i in range(12 * 60 / 5)])

        DynamicCo2Conversion.objects.create(
            from_timestamp=from_timestamp,
            mainconsumption=self.mainconsumption,
            datasource=self.datasource)

        self.assertEqual(
            [
                RangedSample(
                    from_timestamp + datetime.timedelta(minutes=5 * i),
                    from_timestamp + datetime.timedelta(minutes=5 * (i + 1)),
                    PhysicalQuantity(i % 20, self.datasource.unit))
                for i in range(12 * 60 / 5)],
            list(
                self.mainconsumption.co2conversion_set.value_sequence(
                    self.timezone.localize(
                        datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(
                        datetime.datetime(2014, 1, 2)))))


@override_settings(ENCRYPTION_TESTMODE=True)
class FixedCo2ConversionTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(timezone=self.timezone)

        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))

        self.datasource = DataSource.objects.create(
            unit='gram*kilowatt^-1*hour^-1')

    def test_unicode(self):
        conversion = FixedCo2Conversion(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            mainconsumption=self.mainconsumption,
            value='123.456',
            unit='gram*kilowatt^-1*hour^-1')
        unicode(conversion)

    def test_clean_happy(self):
        conversion = FixedCo2Conversion(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            mainconsumption=self.mainconsumption,
            value='123.456',
            unit='gram*kilowatt^-1*hour^-1')
        conversion.clean()

    def test_clean_detects_bad_unit(self):
        conversion = FixedCo2Conversion(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            mainconsumption=self.mainconsumption,
            value='123.456',
            unit='gram*liter^-1')

        with self.assertRaises(ValidationError) as e:
            conversion.clean()

        self.assertIn('unit', e.exception.message_dict)

    def test_value_sequence(self):
        from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))

        FixedCo2Conversion.objects.create(
            from_timestamp=from_timestamp,
            mainconsumption=self.mainconsumption,
            value='123.456',
            unit='gram*kilowatt^-1*hour^-1')

        self.assertEqual(
            [
                RangedSample(
                    from_timestamp + datetime.timedelta(minutes=5 * i),
                    from_timestamp + datetime.timedelta(minutes=5 * (i + 1)),
                    PhysicalQuantity('123.456', 'gram*kilowatt^-1*hour^-1'))
                for i in range(24 * 60 / 5)],
            list(
                self.mainconsumption.co2conversion_set.value_sequence(
                    self.timezone.localize(
                        datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(
                        datetime.datetime(2014, 1, 2)))))
