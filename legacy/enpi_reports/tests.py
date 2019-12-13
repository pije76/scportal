# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test.utils import override_settings
from django.test import TestCase
from django.core.exceptions import ValidationError

import pytz

from gridplatform.trackuser import replace_customer
from gridplatform.customers.models import Customer
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.models import DataSeries
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.providers.models import Provider

from .models import ENPIReport
from .models import ENPIUseArea


@override_settings(ENCRYPTION_TESTMODE=True)
class ENPIReportRoleTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(timezone=pytz.utc)
        self.customer.save()
        with replace_customer(self.customer):
            self.mp = ConsumptionMeasurementPoint(
                customer=self.customer,
                name_plain='Test measurement point',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
            self.mp.consumption = DataSeries(
                customer=self.customer,
                role=DataRoleField.CONSUMPTION,
                unit='milliwatt*hour',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
            self.mp.save()

            self.enpi_report = ENPIReport(
                customer=self.customer,
                title_plain='Test energy use report')

    def test_employees(self):
        self.enpi_report.energy_driver_unit = 'personyear'
        self.enpi_report.save()
        with replace_customer(self.customer):
            employees = DataSeries.objects.create(
                role=DataRoleField.EMPLOYEES,
                unit='person',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

        self.enpi_use_area = ENPIUseArea.objects.create(
            report=self.enpi_report,
            name_plain='coffee production',
            energy_driver=employees)
        self.enpi_use_area.measurement_points.add(self.mp)

        self.assertEqual(
            self.enpi_report.energy_driver_role,
            DataRoleField.EMPLOYEES)

        self.assertEqual(
            self.enpi_report.enpi_role,
            DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES)

        self.assertTrue(
            PhysicalQuantity.compatible_units(
                self.enpi_report.enpi_unit,
                'kilowatt*hour*person^-1*second^-1'))

    def test_area(self):
        self.enpi_report.energy_driver_unit = 'squaremeteryear'
        self.enpi_report.save()

        with replace_customer(self.customer):
            area = DataSeries.objects.create(
                role=DataRoleField.AREA,
                unit='meter^2',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

        self.enpi_use_area = ENPIUseArea.objects.create(
            report=self.enpi_report,
            name_plain='coffee production',
            energy_driver=area)
        self.enpi_use_area.measurement_points.add(self.mp)

        self.assertEqual(
            self.enpi_report.energy_driver_role,
            DataRoleField.AREA)

        self.assertEqual(
            self.enpi_report.enpi_role,
            DataRoleField.CONSUMPTION_UTILIZATION_AREA)

        self.assertTrue(
            PhysicalQuantity.compatible_units(
                self.enpi_report.enpi_unit,
                'kilowatt*hour*meter^-2*second^-1'))

    def test_production(self):
        self.enpi_report.energy_driver_unit = 'production_a'
        self.enpi_report.save()

        with replace_customer(self.customer):
            production = DataSeries.objects.create(
                role=DataRoleField.PRODUCTION,
                unit='production_a',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

            self.enpi_use_area = ENPIUseArea.objects.create(
                report=self.enpi_report,
                name_plain='coffee production',
                energy_driver=production)
            self.enpi_use_area.measurement_points.add(self.mp)

            self.assertEqual(
                self.enpi_report.energy_driver_role,
                DataRoleField.PRODUCTION)

            self.assertEqual(
                self.enpi_report.enpi_role,
                DataRoleField.PRODUCTION_ENPI)

            self.assertTrue(
                PhysicalQuantity.compatible_units(
                    self.enpi_report.enpi_unit,
                    'kilowatt*hour*production_a^-1'))


@override_settings(ENCRYPTION_TESTMODE=True)
class ENPIUseAreaCleanTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(timezone=pytz.utc)
        self.customer.save()
        with replace_customer(self.customer):
            self.mp = ConsumptionMeasurementPoint(
                customer=self.customer,
                name_plain='Test measurement point',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
            self.mp.consumption = DataSeries(
                customer=self.customer,
                role=DataRoleField.CONSUMPTION,
                unit='milliwatt*hour',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
            self.mp.save()

            self.enpi_report = ENPIReport.objects.create(
                customer=self.customer,
                title_plain='Test energy use report',
                energy_driver_unit='person')

    def test_validates(self):
        with replace_customer(self.customer):
            employees = DataSeries.objects.create(
                role=DataRoleField.EMPLOYEES,
                unit='person',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

        self.enpi_use_area = ENPIUseArea(
            report=self.enpi_report,
            name_plain='coffee production',
            energy_driver=employees)

        self.enpi_use_area.full_clean()

    def test_bad_energy_driver_unit_validation_error(self):
        with replace_customer(self.customer):
            area = DataSeries.objects.create(
                role=DataRoleField.AREA,
                unit='meter*meter',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

        self.enpi_use_area = ENPIUseArea(
            report=self.enpi_report,
            name_plain='coffee production',
            energy_driver=area)

        with self.assertRaises(ValidationError):
            self.enpi_use_area.full_clean()
