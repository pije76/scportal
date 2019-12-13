# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.test import TestCase
from django.test.utils import override_settings
import pytz

from gridplatform.datasources.models import DataSource
from gridplatform.datasources.models import RawData
from gridplatform.utils import utilitytypes
from gridplatform.utils.unitconversion import PhysicalQuantity
from legacy.measurementpoints.fields import DataRoleField

from .datasourceadapter import DataSourceTariffAdapter
from .datasourceadapter import DataSourceCo2ConversionAdapter


class DataSourceMock(DataSource):
    class Meta:
        proxy = True

    def __unicode__(self):
        return 'DATASOURCEMOCK'


@override_settings(ENCRYPTION_TESTMODE=True)
class DataSourceTariffAdapterTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.datasource = DataSourceMock.objects.create(
            unit='currency_dkk*gigawatt^-1*hour^-1')
        self.adapter = DataSourceTariffAdapter.objects.create(
            data_format=DataSourceTariffAdapter.DATASOURCEADAPTER,
            datasource=self.datasource,
            unit=self.datasource.unit,
            role=DataRoleField.ELECTRICITY_TARIFF,
            timezone=pytz.utc,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

    def test_get_samples_no_rawdata(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))
        self.assertEqual(
            [],
            list(self.adapter.get_samples(from_timestamp, to_timestamp)))

    def test_get_samples_rawdata(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        self.datasource.rawdata_set.bulk_create(
            [
                RawData(
                    timestamp=from_timestamp + datetime.timedelta(hours=h),
                    value=h,
                    datasource=self.datasource)
                for h in range(24)])

        self.assertEqual(
            [
                self.adapter.create_range_sample(
                    from_timestamp + datetime.timedelta(hours=h),
                    from_timestamp + datetime.timedelta(hours=h + 1),
                    PhysicalQuantity(h, self.adapter.unit))
                for h in range(24)],
            list(self.adapter.get_samples(from_timestamp, to_timestamp)))

    def test_unicode(self):
        unicode(self.adapter)

    def test_get_preferred_unit_converter_gives_dkk_pr_kwh(self):
        quantity = PhysicalQuantity(1, 'currency_dkk*kilowatt^-1*hour^-1')
        converter = self.adapter.get_preferred_unit_converter()
        self.assertEqual(1, converter.extract_value(quantity))
        unicode(converter.get_display_unit())


@override_settings(ENCRYPTION_TESTMODE=True)
class DataSourceCo2ConversionAdapterTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.datasource = DataSourceMock.objects.create(
            unit='gram*kilowatt^-1*hour^-1')
        self.adapter = DataSourceCo2ConversionAdapter.objects.create(
            data_format=DataSourceCo2ConversionAdapter.DATASOURCEADAPTER,
            datasource=self.datasource,
            unit=self.datasource.unit,
            role=DataRoleField.CO2_QUOTIENT,
            timezone=pytz.utc,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

    def test_get_samples_no_rawdata(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))
        self.assertEqual(
            [],
            list(self.adapter.get_samples(from_timestamp, to_timestamp)))

    def test_get_samples_rawdata(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        self.datasource.rawdata_set.bulk_create(
            [
                RawData(
                    timestamp=from_timestamp + datetime.timedelta(
                        minutes=5 * i),
                    value=i,
                    datasource=self.datasource)
                for i in range(24 * 60 / 5)])

        self.assertEqual(
            [
                self.adapter.create_range_sample(
                    from_timestamp + datetime.timedelta(minutes=5 * i),
                    from_timestamp + datetime.timedelta(minutes=5 * (i + 1)),
                    PhysicalQuantity(i, self.adapter.unit))
                for i in range(24 * 60 / 5)],
            list(self.adapter.get_samples(from_timestamp, to_timestamp)))

    def test_unicode(self):
        unicode(self.adapter)


@override_settings(ENCRYPTION_TESTMODE=True)
class AutocreateDataSourceAdapterTest(TestCase):
    def test_electricity_datasourceco2conversionadapter_created(self):
        self.datasource = DataSourceMock.objects.create(
            unit='gram*kilowatt^-1*hour^-1')

        self.assertTrue(
            DataSourceCo2ConversionAdapter.objects.subclass_only().filter(
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.
                electricity,
                datasource=self.datasource).exists())

    def test_district_heating_datasourceco2conversionadapter_created(self):
        self.datasource = DataSourceMock.objects.create(
            unit='gram*kilowatt^-1*hour^-1')

        self.assertTrue(
            DataSourceCo2ConversionAdapter.objects.subclass_only().filter(
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.
                district_heating,
                datasource=self.datasource).exists())

    def test_gas_datasourceco2conversionadapter_created(self):
        self.datasource = DataSourceMock.objects.create(
            unit='gram*meter^-3')

        self.assertTrue(
            DataSourceCo2ConversionAdapter.objects.subclass_only().filter(
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas,
                datasource=self.datasource).exists())

    def test_oil_datasourceco2conversionadapter_created(self):
        self.datasource = DataSourceMock.objects.create(
            unit='gram*meter^-3')

        self.assertTrue(
            DataSourceCo2ConversionAdapter.objects.subclass_only().filter(
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.oil,
                datasource=self.datasource).exists())

    def test_gas_datasourcetariffadapter_created(self):
        self.datasource = DataSourceMock.objects.create(
            unit='currency_dkk*meter^-3')

        self.assertTrue(
            DataSourceTariffAdapter.objects.subclass_only().filter(
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas,
                datasource=self.datasource).exists())

    def test_oil_datasourcetariffadapter_created(self):
        self.datasource = DataSourceMock.objects.create(
            unit='currency_dkk*meter^-3')

        self.assertTrue(
            DataSourceTariffAdapter.objects.subclass_only().filter(
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.oil,
                datasource=self.datasource).exists())

    def test_water_datasourcetariffadapter_created(self):
        self.datasource = DataSourceMock.objects.create(
            unit='currency_dkk*meter^-3')

        self.assertTrue(
            DataSourceTariffAdapter.objects.subclass_only().filter(
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water,
                datasource=self.datasource).exists())

    def test_electricity_datasourcetariffadapter_created(self):
        self.datasource = DataSourceMock.objects.create(
            unit='currency_dkk*kilowatt^-1*hour^-1')

        self.assertTrue(
            DataSourceTariffAdapter.objects.subclass_only().filter(
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
                datasource=self.datasource).exists())

    def test_district_heating_datasourcetariffadapter_created(self):
        self.datasource = DataSourceMock.objects.create(
            unit='currency_dkk*kilowatt^-1*hour^-1')

        self.assertTrue(
            DataSourceTariffAdapter.objects.subclass_only().filter(
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.
                district_heating,
                datasource=self.datasource).exists())
