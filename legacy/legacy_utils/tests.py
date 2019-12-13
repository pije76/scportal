# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from fractions import Fraction

from django.test import TestCase

from gridplatform.customers.models import Customer
from gridplatform import trackuser
from gridplatform.utils.preferredunits import AbsoluteCelsiusUnitConverter
from gridplatform.utils.preferredunits import AbsoluteFahrenheitUnitConverter
from gridplatform.utils.preferredunits import AreaENPIUnitConverter
from gridplatform.utils.preferredunits import PersonsENPIUnitConverter
from gridplatform.utils.preferredunits import PhysicalQuantity
from gridplatform.utils.preferredunits import PhysicalUnitConverter
from gridplatform.utils.preferredunits import RelativeCelsiusUnitConverter
from gridplatform.utils.preferredunits import RelativeFahrenheitUnitConverter
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.fields import DataRoleField

from .preferredunits import get_preferred_unit_converter


class GetPreferredUnitConverterCelsiusTest(TestCase):
    def setUp(self):
        self.customer = Customer(temperature='celsius')
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_relative(self):
        self.assertIsInstance(
            get_preferred_unit_converter(DataRoleField.RELATIVE_TEMPERATURE),
            RelativeCelsiusUnitConverter)

    def test_absolute(self):
        self.assertIsInstance(
            get_preferred_unit_converter(DataRoleField.ABSOLUTE_TEMPERATURE),
            AbsoluteCelsiusUnitConverter)


class GetPreferredUnitConverterFahrenheitTest(TestCase):
    def setUp(self):
        self.customer = Customer(temperature='fahrenheit')
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_relative(self):
        self.assertIsInstance(
            get_preferred_unit_converter(DataRoleField.RELATIVE_TEMPERATURE),
            RelativeFahrenheitUnitConverter)

    def test_absolute(self):
        self.assertIsInstance(
            get_preferred_unit_converter(DataRoleField.ABSOLUTE_TEMPERATURE),
            AbsoluteFahrenheitUnitConverter)


class GetPreferredUnitConverterMiscTest(TestCase):
    def setUp(self):
        self.customer = Customer()
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_cost(self):
        preferred_unit_converter = get_preferred_unit_converter(
            DataRoleField.COST, unit='currency_dkk')
        self.assertIsInstance(preferred_unit_converter, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit_converter.extract_value(
                PhysicalQuantity(1, 'currency_dkk')),
            1)

    def test_heating_degree_days(self):
        preferred_unit_converter = get_preferred_unit_converter(
            DataRoleField.HEATING_DEGREE_DAYS)
        self.assertIsInstance(preferred_unit_converter, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit_converter.extract_value(
                PhysicalQuantity(1, 'kelvin*day')),
            1)

    def test_co2(self):
        preferred_unit_converter = get_preferred_unit_converter(
            DataRoleField.CO2)
        self.assertIsInstance(preferred_unit_converter, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit_converter.extract_value(
                PhysicalQuantity(1, 'tonne')),
            1)


class GetPreferredUnitConverterUtilityTypeTest(object):
    def test_instantaneous(self):
        raise NotImplementedError()

    def test_consumption(self):
        raise NotImplementedError()

    def test_heating_degree_days_corrected_consumption(self):
        raise NotImplementedError()

    def test_energy_performance_indicator_persons(self):
        raise NotImplementedError()

    def test_energy_performance_indicator_area(self):
        raise NotImplementedError()


class GetPreferredUnitConverterElectricityTest(
        GetPreferredUnitConverterUtilityTypeTest, TestCase):
    def setUp(self):
        self.customer = Customer(
            electricity_consumption='kilowatt*hour',
            electricity_instantaneous='watt')
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_instantaneous(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.POWER, utilitytypes.METER_CHOICES.electricity)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'watt')),
            42)

    def test_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION,
            utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'kilowatt*hour')),
            42)

    def test_heating_degree_days_corrected_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION,
            utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'kilowatt*hour')),
            42)

    def test_energy_performance_indicator_persons(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
            utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.assertIsInstance(preferred_unit, PersonsENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'kilowatt*hour*person^-1*day^-1')),
            42)

    def test_energy_performance_indicator_area(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_AREA,
            utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.assertIsInstance(preferred_unit, AreaENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'kilowatt*hour*meter^-2*day^-1')),
            42)


class GetPreferredUnitConverterHeatTest(
        GetPreferredUnitConverterUtilityTypeTest, TestCase):
    def setUp(self):
        self.customer = Customer(
            heat_consumption='kilowatt*hour',
            heat_instantaneous='watt')
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_instantaneous(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.POWER,
            utilitytypes.OPTIONAL_METER_CHOICES.district_heating)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'watt')),
            42)

    def test_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION,
            utilitytypes.OPTIONAL_METER_CHOICES.district_heating)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'kilowatt*hour')),
            42)

    def test_heating_degree_days_corrected_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION,
            utilitytypes.OPTIONAL_METER_CHOICES.district_heating)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'kilowatt*hour')),
            42)

    def test_energy_performance_indicator_persons(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
            utilitytypes.OPTIONAL_METER_CHOICES.district_heating)
        self.assertIsInstance(preferred_unit, PersonsENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'kilowatt*hour*person^-1*day^-1')),
            42)

    def test_energy_performance_indicator_area(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_AREA,
            utilitytypes.OPTIONAL_METER_CHOICES.district_heating)
        self.assertIsInstance(preferred_unit, AreaENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'kilowatt*hour*meter^-2*day^-1')),
            42)


class GetPreferredUnitConverterGasTest(
        GetPreferredUnitConverterUtilityTypeTest, TestCase):
    def setUp(self):
        self.customer = Customer(
            gas_consumption='meter*meter*meter',
            gas_instantaneous='meter*meter*meter*hour^-1')
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_instantaneous(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.VOLUME_FLOW, utilitytypes.OPTIONAL_METER_CHOICES.gas)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'meter^3*hour^-1')),
            42)

    def test_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION, utilitytypes.OPTIONAL_METER_CHOICES.gas)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'meter^3')),
            42)

    def test_heating_degree_days_corrected_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION,
            utilitytypes.OPTIONAL_METER_CHOICES.gas)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'meter^3')),
            42)

    def test_energy_performance_indicator_persons(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
            utilitytypes.OPTIONAL_METER_CHOICES.gas)
        self.assertIsInstance(preferred_unit, PersonsENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'meter^3*person^-1*day^-1')),
            42)

    def test_energy_performance_indicator_area(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_AREA,
            utilitytypes.OPTIONAL_METER_CHOICES.gas)
        self.assertIsInstance(preferred_unit, AreaENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'meter^3*meter^-2*day^-1')),
            42)


class GetPreferredUnitConverterWaterTest(
        GetPreferredUnitConverterUtilityTypeTest, TestCase):

    def setUp(self):
        self.customer = Customer(
            water_consumption='meter*meter*meter',
            water_instantaneous='meter*meter*meter*hour^-1')
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_instantaneous(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.VOLUME_FLOW, utilitytypes.METER_CHOICES.water)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'meter^3*hour^-1')),
            42)

    def test_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION, utilitytypes.METER_CHOICES.water)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'meter^3')),
            42)

    def test_heating_degree_days_corrected_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION,
            utilitytypes.OPTIONAL_METER_CHOICES.water)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'meter^3')),
            42)

    def test_energy_performance_indicator_persons(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
            utilitytypes.OPTIONAL_METER_CHOICES.water)
        self.assertIsInstance(preferred_unit, PersonsENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'meter^3*person^-1*day^-1')),
            42)

    def test_energy_performance_indicator_area(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_AREA,
            utilitytypes.OPTIONAL_METER_CHOICES.gas)
        self.assertIsInstance(preferred_unit, AreaENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'meter^3*meter^-2*day^-1')),
            42)


class GetPreferredUnitConverterOilTest(
        GetPreferredUnitConverterUtilityTypeTest, TestCase):
    def setUp(self):
        self.customer = Customer(
            oil_consumption='meter*meter*meter',
            oil_instantaneous='meter*meter*meter*hour^-1')
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_instantaneous(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.VOLUME_FLOW, utilitytypes.OPTIONAL_METER_CHOICES.oil)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'meter^3*hour^-1')),
            42)

    def test_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION, utilitytypes.OPTIONAL_METER_CHOICES.oil)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'meter^3')),
            42)

    def test_heating_degree_days_corrected_consumption(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION,
            utilitytypes.OPTIONAL_METER_CHOICES.oil)
        self.assertIsInstance(preferred_unit, PhysicalUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(42, 'meter^3')),
            42)

    def test_energy_performance_indicator_persons(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
            utilitytypes.OPTIONAL_METER_CHOICES.oil)
        self.assertIsInstance(preferred_unit, PersonsENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'meter^3*person^-1*day^-1')),
            42)

    def test_energy_performance_indicator_area(self):
        preferred_unit = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION_UTILIZATION_AREA,
            utilitytypes.OPTIONAL_METER_CHOICES.oil)
        self.assertIsInstance(preferred_unit, AreaENPIUnitConverter)
        self.assertEqual(
            preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(42, 365), 'meter^3*meter^-2*day^-1')),
            42)


class EfficiencyUnitConverterTest(TestCase):
    def setUp(self):
        self.customer = Customer()
        self.converter = get_preferred_unit_converter(
            DataRoleField.EFFICIENCY,
            customer=self.customer)

    def test_extract_value(self):
        quantity = PhysicalQuantity(1, 'millibar')
        self.assertEqual(
            Fraction(1, 1000), self.converter.extract_value(quantity))

    def test_display_unit(self):
        unicode(self.converter.get_display_unit())
