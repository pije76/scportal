# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.test import TestCase
from django.test.utils import override_settings
import pytz

from gridplatform.providers.models import Provider
from gridplatform.customers.models import Customer
from legacy.devices.models import Agent
from legacy.devices.models import Meter
from legacy.devices.models import PhysicalInput
from gridplatform.consumptions.models import Consumption
from gridplatform.consumptions.models import NonpulsePeriod

from .models import ConsumptionAccumulationAdapter


@override_settings(ENCRYPTION_TESTMODE=True)
class AccumulationAdapterTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.agent = Agent.objects.create(
            customer=self.customer,
            mac='BE:EF:FD:EA:D0:00')
        self.meter = Meter.objects.create(
            agent=self.agent,
            customer=self.customer,
            manufactoring_id=0,
            connection_type=Meter.GRIDPOINT,
            name_plain='METER_NAME',
        )
        self.physicalinput = PhysicalInput.objects.create(
            customer=self.customer,
            unit='milliwatt*hour',
            hardware_id='foobarbaz',
            name_plain='PHYSICAL_INPUT',
            type=PhysicalInput.ELECTRICITY,
            meter=self.meter,
            order=0)
        self.consumption = Consumption.objects.create(
            name_plain='CONSUMPTION_NAME',
            customer=self.customer,
            unit='joule')
        self.adapter = ConsumptionAccumulationAdapter(
            datasequence=self.consumption)

    def test_unicode_single_physical_input(self):
        NonpulsePeriod.objects.create(
            datasequence=self.consumption,
            datasource=self.physicalinput,
            from_timestamp=datetime.datetime(2014, 1, 1, tzinfo=pytz.utc))
        self.assertIn('PHYSICAL_INPUT', unicode(self.adapter))

    def test_unicode_multiple_physical_inputs(self):
        physicalinput2 = PhysicalInput.objects.create(
            customer=self.customer,
            unit='milliwatt*hour',
            hardware_id='foobarbaz',
            name_plain='PHYSICAL_INPUT',
            type=PhysicalInput.ELECTRICITY,
            meter=self.meter,
            order=0)
        NonpulsePeriod.objects.create(
            datasequence=self.consumption,
            datasource=self.physicalinput,
            from_timestamp=datetime.datetime(2014, 1, 1, tzinfo=pytz.utc),
            to_timestamp=datetime.datetime(2014, 1, 2, tzinfo=pytz.utc))
        NonpulsePeriod.objects.create(
            datasequence=self.consumption,
            datasource=physicalinput2,
            from_timestamp=datetime.datetime(2014, 1, 2, tzinfo=pytz.utc))
        self.assertIn('CONSUMPTION_NAME', unicode(self.adapter))

    def test_unicode_no_physical_input_but_named(self):
        self.assertIn('CONSUMPTION_NAME', unicode(self.adapter))
