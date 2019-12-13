# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.test import TestCase
from django.test.utils import override_settings
from django.core.exceptions import ValidationError

import pytz

from gridplatform.customers.models import Customer
from gridplatform.providers.models import Provider
from gridplatform.trackuser import replace_customer
from gridplatform.utils.unitconversion import PhysicalQuantity

from .models import TimeEnergyPerformance
from .models import EnergyPerformance
from .models import ProductionEnergyPerformance


@override_settings(ENCRYPTION_TESTMODE=True)
class EnergyPerformanceTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer()
        self.customer.save()

    def test_encryption_integration(self):
        enpi = EnergyPerformance.objects.create(
            customer=self.customer,
            name_plain='base enpi',
            description_plain='base enpi test')
        loaded = EnergyPerformance.objects.get(id=enpi.id)
        self.assertEqual(enpi.name_plain, loaded.name_plain)
        self.assertEqual(enpi.description_plain, loaded.description_plain)

    def test_unicode(self):
        enpi = EnergyPerformance.objects.create(
            customer=self.customer,
            name_plain='base enpi',
            description_plain='base enpi test')
        self.assertIn(enpi.name_plain, unicode(enpi))


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionEnergyPerformanceTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            production_a_unit_plain='kg is',
            timezone=pytz.timezone('Europe/Copenhagen'))

    def test_clean_illegal_production_unit(self):
        enpi = ProductionEnergyPerformance(
            customer=self.customer,
            name_plain='Øvrige energianvendelser pr kg is',
            description_plain='Dækker energianvendelser der ikke direkte er '
            'involveret i produktion',
            production_unit='production_b')
        with self.assertRaises(ValidationError):
            enpi.full_clean()

    def test_clean_illegal_production_unit_exclude(self):
        enpi = ProductionEnergyPerformance(
            customer=self.customer,
            name_plain='Øvrige energianvendelser pr kg is',
            description_plain='Dækker energianvendelser der ikke direkte er '
            'involveret i produktion',
            production_unit='production_b')
        enpi.full_clean(exclude='production_unit')

    def test_clean_legal_production_unit(self):
        enpi = ProductionEnergyPerformance(
            customer=self.customer,
            name_plain='Øvrige energianvendelser pr kg is',
            description_plain='Dækker energianvendelser der ikke direkte er '
            'involveret i produktion',
            production_unit='production_a')
        enpi.full_clean()

    def test_production_dataneed_is_added_upon_creation(self):
        ProductionEnergyPerformance.objects.create(
            customer=self.customer,
            name_plain='Øvrige energianvendelser pr kg is',
            description_plain='Dækker energianvendelser der ikke direkte er '
            'involveret i produktion',
            production_unit='production_a')

    def test_unit_converter_a(self):
        self.customer.production_a_unit_plain = 'Pöp Cørn'
        with replace_customer(self.customer):
            enpi = ProductionEnergyPerformance(
                customer=self.customer,
                name_plain='Øvrige energianvendelser pr kg is',
                description_plain='Dækker energianvendelser der ikke direkte '
                'er involveret i produktion',
                production_unit='production_a')
            self.assertEqual(
                'kWh/Pöp Cørn', enpi.unit_converter.get_display_unit())

    def test_unit_converter_b(self):
        self.customer.production_b_unit_plain = 'Sändwætch'
        with replace_customer(self.customer):
            enpi = ProductionEnergyPerformance(
                customer=self.customer,
                name_plain='Øvrige energianvendelser pr kg is',
                description_plain='Dækker energianvendelser der ikke direkte '
                'er involveret i produktion',
                production_unit='production_b')
            self.assertEqual(
                'kWh/Sändwætch', enpi.unit_converter.get_display_unit())

    def test_unit_converter_c(self):
        self.customer.production_c_unit_plain = 'Håmbürgør'
        with replace_customer(self.customer):
            enpi = ProductionEnergyPerformance(
                customer=self.customer,
                name_plain='Øvrige energianvendelser pr kg is',
                description_plain='Dækker energianvendelser der ikke direkte '
                'er involveret i produktion',
                production_unit='production_c')
            self.assertEquals(
                'kWh/Håmbürgør', enpi.unit_converter.get_display_unit())

    def test_unit_converter_d(self):
        self.customer.production_d_unit_plain = 'Fränch Friæs'
        with replace_customer(self.customer):
            enpi = ProductionEnergyPerformance(
                customer=self.customer,
                name_plain='Øvrige energianvendelser pr kg is',
                description_plain='Dækker energianvendelser der ikke direkte '
                'er involveret i produktion',
                production_unit='production_d')
            self.assertEquals(
                'kWh/Fränch Friæs', enpi.unit_converter.get_display_unit())

    def test_unit_converter_e(self):
        self.customer.production_e_unit_plain = 'Pän Cåkes'
        with replace_customer(self.customer):
            enpi = ProductionEnergyPerformance(
                customer=self.customer,
                name_plain='Øvrige energianvendelser pr kg is',
                description_plain='Dækker energianvendelser der ikke direkte '
                'er involveret i produktion',
                production_unit='production_e')
            self.assertEquals(
                'kWh/Pän Cåkes', enpi.unit_converter.get_display_unit())


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer(production_a_unit_plain='kg is')
        self.customer.save()
        self.enpi = ProductionEnergyPerformance.objects.create(
            customer=self.customer,
            name_plain='Øvrige energianvendelser pr kg is',
            description_plain='Dækker energianvendelser der ikke direkte er '
            'involveret i produktion',
            production_unit='production_a')


@override_settings(ENCRYPTION_TESTMODE=True)
class HistoricalProductionTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()


@override_settings(ENCRYPTION_TESTMODE=True)
class TimeEnergyPerformanceTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.energy_performance = TimeEnergyPerformance.objects.create(
            customer=self.customer,
            name_plain='årligt totalforbrug',
            description_plain='all energianvændelser samlet',
            unit='kilowatt*hour*year^-1')

    def test_compute_performance_compute_total_energy_integration(self):
        self.assertEqual(
            self.energy_performance.compute_performance(
                datetime.datetime(2014, 1, 1, tzinfo=pytz.utc),
                datetime.datetime(2015, 1, 1, tzinfo=pytz.utc)),
            PhysicalQuantity(0, 'watt'))

    def test_unit_converter(self):
        self.assertEqual(
            self.energy_performance.unit_converter.extract_value(
                PhysicalQuantity(42, 'kilowatt*hour*year^-1')),
            42)
