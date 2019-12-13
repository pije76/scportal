# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from datetime import datetime
from datetime import timedelta

from django.test.utils import override_settings
from django.test import TestCase
from django.db.models import ProtectedError

import pytz

from .models import Agent
from .models import Meter
from .models import PhysicalInput

from gridplatform.customers.models import Customer
from gridplatform import trackuser
from gridplatform.providers.models import Provider
from legacy.datasequence_adapters.models import NonaccumulationAdapter
from legacy.datasequence_adapters.models import ConsumptionAccumulationAdapter
from legacy.measurementpoints.models import Location


@override_settings(ENCRYPTION_TESTMODE=True)
class TestDevices(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)
        assert self.customer is trackuser.get_customer()

        self.location = Location.objects.create(
            name_plain='test location',
            customer=self.customer)
        self.location2 = Location.objects.create(
            name_plain='test location',
            customer=self.customer)

        self.agent = Agent(
            mac="AB:CD:DE:F0:12:34",
            online=True,
            location=self.location,
            customer=self.customer)
        self.agent.save()

        self.meter = Meter(
            agent=self.agent,
            manufactoring_id="1234567891234",
            connection_type=Meter.GRIDPOINT,
            manual_mode=False,
            relay_on=False,
            online=True,
            name_plain="test meter",
            customer=self.customer,
            location=self.location2)
        self.meter.save()

        self.input = self.meter.physicalinput_set.create(
            customer=self.customer,
            name_plain="input on test meter",
            unit='milliwatt*hour',
            type=PhysicalInput.ELECTRICITY,
            order=0)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_meter_dependency(self):
        self.assertRaises(
            ProtectedError, lambda: self.location2.delete())

    def test_agent_dependency(self):
        self.assertRaises(
            ProtectedError, lambda: self.location.delete())


@override_settings(ENCRYPTION_TESTMODE=True)
class MeterTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)
        assert self.customer is trackuser.get_customer()

        self.location = Location.objects.create(
            name_plain='test location',
            customer=self.customer)
        self.location2 = Location.objects.create(
            name_plain='test location',
            customer=self.customer)

        self.agent = Agent(
            mac="AB:CD:DE:F0:12:34",
            online=True,
            location=self.location,
            customer=self.customer)
        self.agent.save()

        self.meter = Meter(
            agent=self.agent,
            manufactoring_id="1234567891234",
            connection_type=Meter.GRIDPOINT,
            manual_mode=False,
            relay_on=False,
            online=True,
            name_plain="test meter",
            customer=self.customer,
            location=self.location2)
        self.meter.save()

        self.input = self.meter.physicalinput_set.create(
            customer=self.customer,
            name_plain="input on test meter",
            unit='milliwatt*hour',
            type=PhysicalInput.ELECTRICITY,
            order=0)

        # Added data for another meter to verify that connection_state only
        # checks latest data for itself. A bugfix solved this issue!
        self.another_meter = Meter(
            agent=self.agent,
            manufactoring_id="123123123",
            connection_type=Meter.GRIDPOINT,
            name_plain="another test meter",
            customer=self.customer,
            location=self.location)
        self.another_meter.save()

        self.another_input = self.another_meter.physicalinput_set.create(
            customer=self.customer,
            name_plain="input on another test meter",
            unit='milliwatt*hour',
            type=PhysicalInput.ELECTRICITY,
            order=0)
        self.another_input.rawdata_set.create(
            value=1, timestamp=datetime.now(pytz.utc))

    def tearDown(self):
        trackuser._set_customer(None)

    def test_connection_state_6_days_since_last_measurement(self):
        # Latest update is over 6 days old
        timestamp = datetime.now(pytz.utc) - timedelta(days=6)
        self.input.rawdata_set.create(
            value=1, timestamp=timestamp)
        self.assertEqual(
            self.meter._measurements_info,
            Meter.MEASUREMENTS_INFO.no_measurements_within_24_hours)

        latest_update = self.meter.latest_update
        self.assertEqual(latest_update, timestamp)

    def test_connection_state_15_minutes_since_last_measurement(self):
        # Warning, when least measurement is more than 24 hours old.
        self.input.rawdata_set.create(
            value=1, timestamp=datetime.now(pytz.utc) - timedelta(hours=24))
        self.assertEqual(
            self.meter._measurements_info,
            Meter.MEASUREMENTS_INFO.no_measurements_within_24_hours)

    def test_connection_state_24h_of_equal_measurements(self):
        # measurements for last 24 hours are all equal
        for i in range(24):
            self.input.rawdata_set.create(
                value=1, timestamp=datetime.now(pytz.utc)-timedelta(hours=i))
        self.assertEqual(self.meter._measurements_info,
                         Meter.MEASUREMENTS_INFO.no_change)

    def test_connection_state_agent_offline(self):
        # When agent is offline
        self.agent.online = False
        self.assertEqual(self.meter._connection_state,
                         Meter.CONNECTION_STATES.agent_offline)


@override_settings(ENCRYPTION_TESTMODE=True)
class AutocreateDataSequenceTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.timezone('Europe/Copenhagen'))

        self.agent = Agent.objects.create(
            mac='AB:CD:DE:F0:12:34',
            online=True,
            customer=self.customer)

        self.meter = Meter.objects.create(
            agent=self.agent,
            manufactoring_id='1234567891234',
            connection_type=Meter.GRIDPOINT,
            manual_mode=False,
            relay_on=False,
            online=True,
            name_plain='test meter',
            customer=self.customer)

    def test_millibar_autocreates_nonaccumulationadapter(self):
        physicalinput = self.meter.physicalinput_set.create(
            customer=self.customer,
            name_plain='input on test meter',
            unit='millibar',
            type=PhysicalInput.ELECTRICITY,
            order=0)

        # will raise if the adapter wasn't created
        nonaccumulationadapter = NonaccumulationAdapter.objects.filter(
            datasequence__period_set__datasource=physicalinput).get()

        # check that the created adapters unicode doesn't crash
        unicode(nonaccumulationadapter)

        # check that the intermediate nonaccumulationadapters unicode doesn't
        # crash
        unicode(nonaccumulationadapter.datasequence)

    def test_milliwatthour_autocreates_consumptionaccumulationadapter(self):
        physicalinput = self.meter.physicalinput_set.create(
            customer=self.customer,
            name_plain='input on test meter',
            unit='milliwatt*hour',
            type=PhysicalInput.ELECTRICITY,
            order=0)

        # will raise if the adapter wasn't created
        consumptionaccumulationadapter = \
            ConsumptionAccumulationAdapter.objects.filter(
                datasequence__period__nonpulseperiod__datasource=physicalinput).get()  # noqa

        # check that the created adapters unicode doesn't crash
        unicode(consumptionaccumulationadapter)

        # check that the intermediate nonaccumulationadapters unicode doesn't
        # crash
        unicode(consumptionaccumulationadapter.datasequence)
