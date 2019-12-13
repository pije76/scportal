# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Unittests for the rules package.
"""

import StringIO
import datetime
import inspect
import itertools
import urllib2
from mock import Mock, patch

from django.core import mail
from django.test import TestCase as DjangoTestCase
from django.test.utils import override_settings

import pytz

from gridplatform import trackuser
from gridplatform.customers.models import Customer
from legacy.devices.models import Agent, Meter
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.models import DataSeries
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.providers.models import Provider

from .models import (
    TriggeredRule,
    Action,
    RelayAction,
    Invariant,
    EmailAction,
    PhoneAction,
    InputInvariant,
    IndexInvariant,
    AgentRule,
    TURN_ON,
    TURN_OFF,
    agentserver)
from . import engine


class TestCase(DjangoTestCase):
    """
    Custom TestCase implementation, to provide module specific
    assertion methods.
    """

    def assertAny(self, l, f):
        """
        Custom assertion method, for checking if a function evaluates
        to true on at least one element in a list.

        @raise AssertionError: If C{f(e)} does not evaluate to C{True}
        for any element in C{c in l}, an C{AssertionError} is raised.
        """
        try:
            next(itertools.ifilter(f, l))
        except StopIteration:
            try:
                function = inspect.getsource(f)
            except IOError:
                function = repr(f)
            raise AssertionError("No element in %r was matched by\n%s" %
                                 (l, function))


class AgentRuleTest(TestCase):
    """
    Test the L{AgentRule} class.
    """
    def setUp(self):
        """
        Initializes self.meter and self.agent prior to each test.
        """
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.agent = Agent(
            mac='08:00:27:03:fe:c7',
            customer=self.customer)
        self.agent.save()

        self.meter = Meter(
            agent=self.agent,
            manufactoring_id=155173425101,
            connection_type=Meter.GRIDPOINT,
            customer=self.customer)
        self.meter.save()

    def test_unicode(self):
        """
        Test unicode operator.
        """
        unit1 = AgentRule(
            datetime.datetime(2012, 10, 4, 12, 00, tzinfo=pytz.utc),
            RelayAction(meter=self.meter, relay_action=TURN_OFF))
        unit2 = AgentRule(
            datetime.datetime(2012, 10, 4, 12, 00, tzinfo=pytz.utc),
            RelayAction(meter=self.meter, relay_action=TURN_ON))

        self.assertNotEqual(unicode(unit1), unicode(unit2))

    def test_representation(self):
        """
        Test representation operator.
        """
        unit1 = AgentRule(
            datetime.datetime(2012, 10, 4, 12, 00, tzinfo=pytz.utc),
            RelayAction(meter=self.meter, relay_action=TURN_OFF))

        unit2 = AgentRule(
            datetime.datetime(2012, 10, 4, 12, 00, tzinfo=pytz.utc),
            RelayAction(meter=self.meter, relay_action=TURN_ON))

        self.assertNotEqual(repr(unit1), repr(unit2))

    def test_comparison(self):
        """
        Test comparison operators
        """
        unit1 = AgentRule(
            datetime.datetime(2012, 10, 4, 12, 00, tzinfo=pytz.utc),
            RelayAction(relay_action=TURN_OFF))

        unit2 = AgentRule(
            datetime.datetime(2012, 10, 4, 12, 00, tzinfo=pytz.utc),
            RelayAction(relay_action=TURN_ON))

        self.assertTrue(unit1 < unit2)
        self.assertTrue(unit1 <= unit2)
        self.assertFalse(unit1 > unit2)
        self.assertFalse(unit1 >= unit2)
        self.assertEqual(unit1, unit1)
        self.assertTrue(unit1 != unit2)


class InvariantTest(TestCase):
    """
    Tests the L{Variant} specializations L{IndexInvariant} and
    L{InputInvariant}.
    """
    def test_input_invariant(self):
        """
        Test InputInvariant
        """
        unit = InputInvariant(value=10, operator=Invariant.LT, unit='watt')
        self.assertTrue(unit.compare_value(PhysicalQuantity(9, 'watt')))
        self.assertFalse(unit.compare_value(PhysicalQuantity(11, 'watt')))
        self.assertFalse(unit.compare_value(PhysicalQuantity(10, 'watt')))

    def test_input_invariant_absolute_fahrenheit(self):
        ds = DataSeries(
            role=DataRoleField.ABSOLUTE_TEMPERATURE,
            unit='millikelvin',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)
        unit = InputInvariant(
            data_series=ds, value=10, operator=Invariant.LT, unit='fahrenheit')
        # 10 F (absolute) = 260.93 K

        # 260 K < 260.93 K
        self.assertTrue(unit.compare_value(PhysicalQuantity(260, 'kelvin')))
        # 261 K >= 260.93 K
        self.assertFalse(unit.compare_value(PhysicalQuantity(261, 'kelvin')))

    def test_input_invariant_relative_fahrenheit(self):
        ds = DataSeries(
            role=DataRoleField.RELATIVE_TEMPERATURE,
            unit='millikelvin',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)
        unit = InputInvariant(
            data_series=ds, value=10, operator=Invariant.LT, unit='fahrenheit')

        self.assertTrue(unit.compare_value(PhysicalQuantity(9, 'rankine')))
        self.assertFalse(unit.compare_value(PhysicalQuantity(11, 'rankine')))

    def test_input_invariant_absolute_celsius(self):
        ds = DataSeries(
            role=DataRoleField.ABSOLUTE_TEMPERATURE,
            unit='millikelvin',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)
        unit = InputInvariant(
            data_series=ds, value=10, operator=Invariant.LT, unit='celsius')
        # 10 C (absolute) = 283.15 K

        # 283 K < 283.15 K
        self.assertTrue(unit.compare_value(PhysicalQuantity(283, 'kelvin')))
        # 284 K >= 283.15 K
        self.assertFalse(unit.compare_value(PhysicalQuantity(284, 'kelvin')))

    def test_input_invariant_relative_celsius(self):
        ds = DataSeries(
            role=DataRoleField.RELATIVE_TEMPERATURE,
            unit='millikelvin',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)
        unit = InputInvariant(
            data_series=ds, value=10, operator=Invariant.LT, unit='celsius')

        self.assertTrue(unit.compare_value(PhysicalQuantity(9, 'kelvin')))
        self.assertFalse(unit.compare_value(PhysicalQuantity(11, 'kelvin')))

    def test_index_invariant(self):
        """
        Test IndexInvariant
        """
        unit = IndexInvariant(value=10, operator=Invariant.LT,
                              unit='currency_dkk*watt^-1*hour^-1')
        self.assertTrue(
            unit.compare_value(
                PhysicalQuantity(9, 'currency_dkk*watt^-1*hour^-1')))
        self.assertFalse(
            unit.compare_value(
                PhysicalQuantity(11, 'currency_dkk*watt^-1*hour^-1')))
        self.assertFalse(
            unit.compare_value(
                PhysicalQuantity(10, 'currency_dkk*watt^-1*hour^-1')))


@override_settings(ENCRYPTION_TESTMODE=True)
class TestAction(TestCase):
    """
    Test various forms of Actions
    """

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.agent = Agent(
            mac='08:00:27:03:fe:c7',
            customer=self.customer)
        self.agent.save()
        self.meter1 = Meter(
            name_plain="Meter1",
            agent=self.agent,
            manufactoring_id=155173425101,
            connection_type=Meter.GRIDPOINT,
            customer=self.customer)
        self.meter1.save()
        self.meter2 = Meter(
            name_plain="Meter2",
            agent=self.agent,
            manufactoring_id=155173425221,
            connection_type=Meter.GRIDPOINT,
            customer=self.customer)
        self.meter2.save()

    def test_relay_action_internationalization(self):
        """
        Test that the unicode representation of L{RelayAction} reveals
        differences between TURN_OFF and TURN_ON, and the same action
        on two different meters.
        """
        unit1 = RelayAction(
            meter=self.meter1, relay_action=TURN_OFF)
        unit2 = RelayAction(
            meter=self.meter1, relay_action=TURN_ON)
        self.assertNotEqual(unicode(unit1), unicode(unit2))

        unit1 = RelayAction(
            meter=self.meter1, relay_action=TURN_OFF)
        unit2 = RelayAction(
            meter=self.meter2, relay_action=TURN_OFF)
        self.assertNotEqual(unicode(unit1), unicode(unit2))

    def test_email_action_internationalization(self):
        """
        Test that the unicode representation of L{EmailAction} reveals
        differences between different recipients and between different
        messages.
        """
        unit1 = EmailAction(recipient="test1@example.com", message="boo!")
        unit2 = EmailAction(recipient="test2@example.com", message="boo!")
        self.assertNotEqual(unicode(unit1), unicode(unit2))

        unit1 = EmailAction(recipient="test@example.com", message="boo!")
        unit2 = EmailAction(recipient="test@example.com", message="yay!")
        self.assertNotEqual(unicode(unit1), unicode(unit2))

    def test_phone_action_internationalization(self):
        """
        Test that the unicode representation of L{PhoneAction} reveals
        differences between different phone numbers and between different
        messages.
        """
        unit1 = PhoneAction(phone_number="555-BATPHONE", message="boo!")
        unit2 = PhoneAction(phone_number="1-800-U-SQUEAL", message="boo!")
        self.assertNotEqual(unicode(unit1), unicode(unit2))

        unit1 = PhoneAction(phone_number="555-BATPHONE", message="boo!")
        unit2 = PhoneAction(phone_number="555-BATPHONE", message="yay!")
        self.assertNotEqual(unicode(unit1), unicode(unit2))

    def test_abstract_method(self):
        """
        Test that relevant exception is raised when calling
        unimplemented C{execute()} method.
        """
        unit = Action()
        self.assertRaises(NotImplementedError, unit.execute)

    def test_email_action(self):
        """
        Test that as a consequence of executing an L{EmailAction}
        Django is convinced an email has been sent.
        """
        unit = EmailAction(recipient="test@grid-manager.com",
                           message="Message send from unit-test")
        self.assertEqual(len(mail.outbox), 0)
        unit.execute()
        self.assertEqual(len(mail.outbox), 1)

    def test_phone_action(self):
        """
        Test execution of PhoneAction.

        To avoid paying for a SMS text message everytime someone runs
        a unit-test (and to avoid requiring an internet connection), a
        C{UrlOpenShunt} is used.
        """
        class UrlOpenShunt(object):
            def __enter__(self):
                urllib2.install_opener(self)
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                urllib2.install_opener(None)
                return False

            def open(self, url, data, timeout):
                self.url = url
                return StringIO.StringIO("ID: URL open shunt")

        with UrlOpenShunt() as url_open_shunt:

            unit = PhoneAction(phone_number="555-BATPHONE",
                               message="Test message with + sign")
            unit.execute()

            self.assertEqual(
                url_open_shunt.url,
                "http://api.clickatell.com/http/sendmsg?"
                "user=gridmanager&password=1GridManager2Go"
                "&api_id=3191312&to=555-BATPHONE&"
                "text=Test+message+with+%2B+sign&concat=1")


@override_settings(ENCRYPTION_TESTMODE=True)
class TestEngine(TestCase):
    """
    Test the rule engine.
    """

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.agent = Agent.objects.create(
            mac=0xbeefbeefbeef,
            online=True,
            customer=self.customer)

        self.meter = Meter.objects.create(
            agent=self.agent,
            manufactoring_id=123456789,
            connection_type=Meter.GRIDPOINT,
            manual_mode=False,
            relay_on=False,
            online=True,
            relay_enabled=True,
            name_plain='Our test meter',
            customer=self.customer)

    def tearDown(self):
        pass

    @patch("legacy.rules.models.agentserver.relay_state", Mock())
    def test_celsius_triggered_rule(self):
        """
        Test a rule that triggers when a absolute celsius input crosses a
        threshold.
        """

        ds = DataSeries.objects.create(
            role=DataRoleField.ABSOLUTE_TEMPERATURE,
            unit='millikelvin',
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

        rule = TriggeredRule.objects.create(
            name_plain='test rule',
            timezone='Europe/Copenhagen',
            customer=self.customer)

        rule.inputinvariant_set.create(
            data_series=ds,
            value=1,
            operator=Invariant.LT,
            unit='celsius')

        RelayAction.objects.create(
            rule=rule,
            execution_time=Action.INITIAL,
            meter=self.meter,
            relay_action=TURN_ON)

        engine_rules = rule.generate_rules(
            datetime.datetime(2013, 1, 1, 1, tzinfo=pytz.utc))

        ds.stored_data.create(
            value=275000,
            timestamp=datetime.datetime(2013, 1, 1, 1, tzinfo=pytz.utc))

        start_time = datetime.datetime(2013, 1, 1, 1, tzinfo=pytz.utc)
        for rule in engine_rules:
            map(lambda action: action.execute(), rule.process(start_time))
        self.assertFalse(agentserver.relay_state.called)

        ds.stored_data.create(
            value=272000,
            timestamp=datetime.datetime(2013, 1, 1, 1, 2, tzinfo=pytz.utc))

        start_time = datetime.datetime(2013, 1, 1, 1, 2, 30, tzinfo=pytz.utc)
        for rule in engine_rules:
            map(lambda action: action.execute(), rule.process(start_time))
        self.assertTrue(agentserver.relay_state.called)
        agentserver.relay_state.assert_called_with(
            self.meter.agent.mac,
            [(self.meter.connection_type, self.meter.manufactoring_id)],
            TURN_ON)


@override_settings(ENCRYPTION_TESTMODE=True)
class TestEngineRefreshRules(TestCase):
    """
    Test the {engine.refresh_rules()} procedure
    """

    def setUp(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        self.customer = customer
        trackuser._set_customer(self.customer)

        agent = Agent.objects.create(
            mac=0xbeefbeefbeef,
            online=True,
            customer=self.customer)

        meter = Meter.objects.create(
            agent=agent,
            manufactoring_id=123456789,
            connection_type=Meter.GRIDPOINT,
            manual_mode=False,
            relay_on=False,
            online=True,
            relay_enabled=True,
            name_plain='Our test meter',
            customer=self.customer)

        ds = DataSeries.objects.create(
            role=DataRoleField.ABSOLUTE_TEMPERATURE,
            unit='millikelvin',
            customer=customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

        self.ds2 = DataSeries.objects.create(
            role=DataRoleField.ABSOLUTE_TEMPERATURE,
            unit='millikelvin',
            customer=customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

        rule = TriggeredRule.objects.create(
            name_plain='test rule',
            timezone='Europe/Copenhagen',
            customer=customer)

        self.input_invariant = rule.inputinvariant_set.create(
            data_series=ds,
            value=1,
            operator=Invariant.LT,
            unit='celsius')

        RelayAction.objects.create(
            rule=rule,
            execution_time=Action.INITIAL,
            meter=meter,
            relay_action=TURN_ON)

        self.hour = datetime.datetime(2013, 1, 1, tzinfo=pytz.utc)
        self.rules = set(engine.get_engine_rules(self.hour))

    def tearDown(self):
        trackuser._set_customer(None)

    def test_no_changes(self):
        self.assertEqual(
            self.rules,
            engine.refresh_rules(self.rules, self.hour))

    def test_changed_input_invariant_value(self):
        self.input_invariant.value = 2
        self.input_invariant.save()
        self.assertNotEqual(
            self.rules,
            engine.refresh_rules(self.rules, self.hour))

    def test_changed_input_invariant_operator(self):
        self.input_invariant.operator = Invariant.GT
        self.input_invariant.save()
        self.assertNotEqual(
            self.rules,
            engine.refresh_rules(self.rules, self.hour))

    def test_changed_input_invariant_unit(self):
        self.input_invariant.unit = 'fahrenheit'
        self.input_invariant.save()
        self.assertNotEqual(
            self.rules,
            engine.refresh_rules(self.rules, self.hour))

    def test_changed_input_invariant_data_series(self):
        self.input_invariant.data_series = self.ds2
        self.input_invariant.save()
        self.assertNotEqual(
            self.rules,
            engine.refresh_rules(self.rules, self.hour))
