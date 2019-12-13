# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module defines tests for the C{projects} app.
"""

from datetime import datetime
from datetime import timedelta
from mock import patch
from decimal import Decimal
from fractions import Fraction
import unittest

from django.forms import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.translation import ugettext_lazy as _

import pytz

from gridplatform import trackuser
from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.models import CollectionConstraint
from gridplatform.customers.models import Customer
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.indexes.models import Index
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.models import CostCalculation
from legacy.measurementpoints.models import DataSeries
from legacy.measurementpoints.tests import TestDataSeries
from gridplatform.trackuser import replace_customer
from gridplatform.trackuser import replace_user
from gridplatform.users.models import User
from gridplatform.utils import DATETIME_MAX
from gridplatform.utils import DATETIME_MIN
from gridplatform.utils import condense
from gridplatform.utils import unix_timestamp
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.providers.models import Provider

from .models import AdditionalSaving
from .models import BenchmarkProject
from .models import Cost
from .models import Stage
from .tasks import AnnualSavingsPotentialReportTask
from .views import FinalizeAnnualSavingsPotentialReportView
from .forms import AnnualSavingsPotentialReportGenerationForm


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectEncryptionTest(TestCase):
    """
    Test the encryption properties of the L{BenchmarkProject} model.
    """
    def setUp(self):
        """
        Create and store a L{BenchmarkProject}.
        """
        Provider.objects.create()
        self.customer = Customer(
            timezone=pytz.utc,
            currency_unit='currency_dkk')
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.unit = BenchmarkProject(
            name_plain='Some test project',
            background_plain='Some test description',
            expectations_plain='Some exspections',
            actions_plain='Some actions',
            comments_plain='Some comments',
            runtime=52,
            estimated_yearly_consumption_costs_before=Decimal('2000.33'),
            estimated_yearly_consumption_before=Decimal('2000.33'),
            estimated_co2_emissions_before=Decimal('2000.33'),
            expected_savings_in_yearly_total_costs=Decimal(
                '2000.33'),
            expected_savings_in_yearly_consumption_after=Decimal('2000.33'),
            expected_reduction_in_yearly_co2_emissions=Decimal('2000.33'),
            utility_type=utilitytypes.METER_CHOICES.electricity,
            baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))

        self.unit.save()

    def tearDown(self):
        trackuser._set_customer(None)
        trackuser._set_user(None)

    def test_basic_usage(self):
        """
        Test if storing and loading results in sensible values.
        """
        loaded_unit = BenchmarkProject.objects.get(id=self.unit.id)

        self.assertEqual(
            loaded_unit.name_plain, 'Some test project')
        self.assertEqual(
            loaded_unit.background_plain, 'Some test description')
        self.assertEqual(
            loaded_unit.expectations_plain, 'Some exspections')
        self.assertEqual(
            loaded_unit.actions_plain, 'Some actions')
        self.assertEqual(
            loaded_unit.comments_plain, 'Some comments')
        self.assertEqual(
            loaded_unit.runtime, 52)
        self.assertEqual(
            loaded_unit.estimated_yearly_consumption_costs_before,
            Decimal('2000.33'))
        self.assertEqual(
            loaded_unit.estimated_yearly_consumption_before,
            Decimal('2000.33'))
        self.assertEqual(
            loaded_unit.estimated_co2_emissions_before, Decimal('2000.33'))
        self.assertEqual(
            loaded_unit.expected_savings_in_yearly_total_costs,
            Decimal('2000.33'))
        self.assertEqual(
            loaded_unit.expected_savings_in_yearly_consumption_after,
            Decimal('2000.33'))
        self.assertEqual(
            loaded_unit.expected_reduction_in_yearly_co2_emissions,
            Decimal('2000.33'))

    def test_get_encryption_id(self):
        """
        Test that L{BenchmarkProject} has a conventional implementation of
        L{EncryptedModel.get_encryption_id()}
        """
        self.assertEqual(
            (Customer, self.customer.id),
            self.unit.get_encryption_id())


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectCleanCostCurrencyTest(TestCase):
    """
    Test the L{BenchmarkProject} class.
    """
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.utc,
            currency_unit='currency_dkk',)
        trackuser._set_customer(self.customer)
        self.user = User.objects.create_user(
            'test@gridportal.dk',
            'password222w2222',
            user_type=User.CUSTOMER_USER,
            customer=self.customer)

        self.project = BenchmarkProject.objects.create(
            name_plain='Some test project',
            background_plain='Some test description',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            baseline_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2013, 1, 2, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2013, 1, 1, 12, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2013, 1, 2, 13, tzinfo=pytz.utc),
            include_measured_costs=True)

    def test_conflict(self):
        consumption_mp = ConsumptionMeasurementPoint(
            name_plain='Test measurement point',
            role=ConsumptionMeasurementPoint.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        consumption_mp.consumption = DataSeries.objects.create(
            role=DataRoleField.CONSUMPTION,
            unit='kilowatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        consumption_mp.save()
        cost_graph = consumption_mp.graph_set.create(role=DataRoleField.COST)
        cost_graph.dataseries_set.create(
            role=DataRoleField.COST, unit='currency_eur',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.project.baseline_measurement_points.add(consumption_mp)

        self.assertTrue(self.project.cost_currency_conflicts())

    def test_no_conflicts(self):
        self.assertFalse(self.project.cost_currency_conflicts())


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectTest(TestCase):
    """
    Test the L{BenchmarkProject} class.
    """
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.utc,
            currency_unit='currency_dkk')
        self.user = User.objects.create_user(
            'test@gridportal.dk',
            'password222w2222',
            user_type=User.CUSTOMER_USER,
            customer=self.customer)
        trackuser._set_customer(self.customer)

        self.unit = BenchmarkProject.objects.create(
            name_plain='Some test project',
            background_plain='Some test description',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            baseline_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2013, 1, 2, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2013, 1, 1, 12, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2013, 1, 2, 13, tzinfo=pytz.utc))

        self.tariff1 = Index.objects.create(
            name_plain="test tariff",
            unit="currency_dkk*kilowatt^-1*hour^-1",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SPOT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            timezone='Europe/Copenhagen')
        self.tariff_entry = self.tariff1.entry_set.create(
            from_timestamp=DATETIME_MIN,
            to_timestamp=DATETIME_MAX,
            value=Decimal(10))

        self.measurement_point = ConsumptionMeasurementPoint(
            name_plain='Test measurement point',
            role=ConsumptionMeasurementPoint.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.consumption = TestDataSeries(
            role=DataRoleField.CONSUMPTION,
            unit='kilowatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.save()

        cost_graph = self.measurement_point.graph_set.create(
            role=DataRoleField.COST)
        cost = CostCalculation(
            graph=cost_graph,
            role=DataRoleField.COST,
            consumption=self.measurement_point.consumption,
            index=self.tariff1,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        cost.full_clean(exclude=['unit'])
        cost.save()

    def tearDown(self):
        trackuser._set_customer(None)
        trackuser._set_user(None)

    @unittest.skip('Warning currently not provided')
    def test_baseline_and_result_tariff_domain_warning(self):
        self.measurement_point.consumption.stored_data.create(
            value=1000, timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=2000, timestamp=datetime(2013, 1, 30, tzinfo=pytz.utc))
        self.unit.baseline_measurement_points.add(self.measurement_point)

        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = datetime(
            2013, 1, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_measurement_points.add(self.measurement_point)
        self.unit.result_from_timestamp = datetime(
            2013, 1, 15, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = datetime(2013, 1, 30, tzinfo=pytz.utc)
        self.unit.save()

        # Assign tariff which will not not be covering
        # the whole stage 1 consumption domain
        self.tariff_entry.from_timestamp = datetime(
            2013, 1, 10, tzinfo=pytz.utc)
        self.tariff_entry.save()

        # Change valid from date on tariff so that
        # no stages will have valid tariffs.
        self.tariff_entry.from_timestamp = datetime(
            2013, 1, 20, tzinfo=pytz.utc)
        self.tariff_entry.save()

        self.assertTrue(
            self.unit.baseline_stage.tariff_domain_warning_measurement_point_ids)  # noqa
        self.assertTrue(
            self.unit.result_stage.tariff_domain_warning_measurement_point_ids)  # noqa

    def test_no_tariff_domain_warning(self):
        self.measurement_point.consumption.stored_data.create(
            value=1000, timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=2000, timestamp=datetime(2013, 1, 30, tzinfo=pytz.utc))
        self.unit.baseline_measurement_points.add(self.measurement_point)

        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = datetime(
            2013, 1, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_measurement_points.add(self.measurement_point)
        self.unit.result_from_timestamp = datetime(
            2013, 1, 15, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = datetime(2013, 1, 30, tzinfo=pytz.utc)
        self.unit.save()

        self.assertFalse(
            self.unit.baseline_stage.tariff_domain_warning_measurement_point_ids)  # noqa
        self.assertFalse(
            self.unit.result_stage.tariff_domain_warning_measurement_point_ids)  # noqa

    @unittest.skip('Warning currently not provided')
    def test_baseline_tariff_domain_warning(self):
        self.measurement_point.consumption.stored_data.create(
            value=1000, timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=2000, timestamp=datetime(2013, 1, 30, tzinfo=pytz.utc))
        self.unit.baseline_measurement_points.add(self.measurement_point)

        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = datetime(
            2013, 1, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_measurement_points.add(self.measurement_point)
        self.unit.result_from_timestamp = datetime(
            2013, 1, 15, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = datetime(2013, 1, 30, tzinfo=pytz.utc)
        self.unit.save()

        # Assign tariff which will not not be covering
        # the whole stage 1 consumption domain
        self.tariff_entry.from_timestamp = datetime(
            2013, 1, 10, tzinfo=pytz.utc)
        self.tariff_entry.save()

        self.assertTrue(
            self.unit.baseline_stage.tariff_domain_warning_measurement_point_ids)  # noqa
        self.assertFalse(
            self.unit.result_stage.tariff_domain_warning_measurement_point_ids)  # noqa

    def test_active_and_done(self):
        """
        Test the L{BenchmarkProject.active_and_done()} method.
        """
        active = BenchmarkProject.active(
            datetime(2013, 1, 1, tzinfo=pytz.utc))
        done = BenchmarkProject.done(
            datetime(2013, 1, 1, tzinfo=pytz.utc))
        self.assertIn(self.unit, active)
        self.assertNotIn(self.unit, done)

        active = BenchmarkProject.active(
            datetime(2013, 1, 3, tzinfo=pytz.utc))
        done = BenchmarkProject.done(
            datetime(2013, 1, 3, tzinfo=pytz.utc))
        self.assertNotIn(self.unit, active)
        self.assertIn(self.unit, done)

        # Assuming today is later than January 3rd, 2013.
        active = BenchmarkProject.active()
        done = BenchmarkProject.done()
        self.assertNotIn(self.unit, active)
        self.assertIn(self.unit, done)

    def test_yearly_consumption_savings(self):
        """
        Test the L{BenchmarkProject.yearly_consumption_savings()} method.

        Create data so that the savings are 10 kWh pr day; 3650 kWh pr year.
        """
        self.measurement_point.consumption.stored_data.create(
            value=0, timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=1000, timestamp=datetime(2013, 1, 11, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=1900, timestamp=datetime(2013, 1, 21, tzinfo=pytz.utc))
        self.unit.baseline_measurement_points.add(self.measurement_point)

        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = datetime(2013, 1, 3, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_measurement_points.add(self.measurement_point)
        self.unit.result_from_timestamp = datetime(
            2013, 1, 11, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = datetime(2013, 1, 13, tzinfo=pytz.utc)
        self.unit.save()

        self.assertEqual(
            self.unit.yearly_measured_consumption_savings(),
            PhysicalQuantity(10 * 365, 'kilowatt*hour'))

    def test_yearly_consumption_savings_with_zero_consumption(self):
        """
        Test the L{BenchmarkProject.yearly_consumption_savings()} method with
        zero consumption, and thus zero savings.
        """
        self.assertEqual(
            self.unit.yearly_measured_consumption_savings(),
            PhysicalQuantity(0, 'kilowatt*hour'))

    def test_resulting_annual_cost_savings_with_zero_cost(self):
        """
        Test the L{BenchmarkProject.resulting_annual_cost_savings()} method
        with zero cost, and thus zero savings.
        """
        self.assertEqual(
            self.unit.yearly_measured_cost_savings(),
            PhysicalQuantity(0, 'currency_dkk'))

    def test_resulting_annual_cost_savings(self):
        """
        Test the L{BenchmarkProject.resulting_annual_cost_savings()} method.

        Create data so that the savings are 10 DKK pr day; 3650 DKK pr year.
        """
        self.measurement_point.consumption.stored_data.create(
            value=0, timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=100, timestamp=datetime(2013, 1, 11, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=190, timestamp=datetime(2013, 1, 21, tzinfo=pytz.utc))

        self.unit.baseline_measurement_points.add(self.measurement_point)
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = datetime(2013, 1, 3, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_measurement_points.add(self.measurement_point)
        self.unit.result_from_timestamp = datetime(
            2013, 1, 11, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = datetime(2013, 1, 13, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.include_measured_costs = True

        self.assertEqual(
            tuple(self.unit.yearly_measured_cost_savings()),
            tuple(PhysicalQuantity(10 * 365, 'currency_dkk')))

    def test_active_stages(self):
        """
        Test that the different stages are active at relevant times.
        """
        self.assertIn(
            _('Result'),
            self.unit.active_stages(datetime(2013, 1, 1, 20, tzinfo=pytz.utc)))

        self.assertIn(
            _('Result'),
            self.unit.active_stages(datetime(2013, 1, 1, 20, tzinfo=pytz.utc)))

        self.assertNotIn(
            _('Baseline'),
            self.unit.active_stages(datetime(2013, 1, 2, 2, tzinfo=pytz.utc)))

        self.assertIn(
            _('Result'),
            self.unit.active_stages(datetime(2013, 1, 2, 2, tzinfo=pytz.utc)))

        self.assertEqual(
            [],
            self.unit.active_stages(datetime(2013, 1, 20, tzinfo=pytz.utc)))

        self.assertEqual(
            [],
            self.unit.active_stages(datetime(2012, 12, 20, tzinfo=pytz.utc)))

        # Assume that now is later than January 3rd, 2013.
        self.assertEqual([], self.unit.active_stages())

    def test_yearly_consumption_savings_display(self):
        """
        Test that nothing bad happens when calling
        yearly_consumption_savings_display.
        """
        self.unit.yearly_consumption_savings_display()

    def test_resulting_annual_cost_savings_display(self):
        """
        Test that nothing bad happens when calling
        resulting_annual_cost_savings_display.
        """
        self.unit.resulting_annual_cost_savings_display()

    def test_duration(self):
        """
        Test the L{BenchmarkProject.duration} method.
        """
        unit = BenchmarkProject(
            name_plain='Some test project',
            background_plain='Some test description',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            baseline_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2013, 1, 2, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2013, 1, 1, 12, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2013, 1, 2, 13, tzinfo=pytz.utc))

        self.assertIsInstance(unit.from_timestamp, datetime)
        self.assertIsInstance(unit.to_timestamp, datetime)

        self.assertEqual(unit.from_timestamp,
                         datetime(2013, 1, 1, tzinfo=pytz.utc))

        self.assertEqual(unit.to_timestamp,
                         datetime(2013, 1, 2, 13, tzinfo=pytz.utc))

    def test_dependencies(self):
        self.unit.baseline_measurement_points.add(self.measurement_point)
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = datetime(2013, 1, 3, tzinfo=pytz.utc)
        self.unit.save()

        self.assertEqual(self.measurement_point.is_deletable(), False)


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectInvestmentTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer.objects.create(currency_unit='currency_dkk')
        self.project = BenchmarkProject.objects.create(
            name_plain='test project',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            runtime=1,
            include_measured_costs=False,
            estimated_yearly_consumption_before=Decimal('456.78'),
            customer=self.customer,
            baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))

    def test_empty(self):
        self.assertEqual(self.project.investment, 0)

    def test_nonempty_delegates_to_cost_get_total_costs(self):
        EXPECTED_COST = Decimal('678.91')
        UNUSED_COST = Decimal('123.45')

        self.project.cost_set.create(cost=UNUSED_COST)

        with patch.object(Cost, 'get_total_costs',
                          return_value=EXPECTED_COST) as get_total_costs_mock:

            self.assertEqual(self.project.investment, EXPECTED_COST)
            get_total_costs_mock.assert_called_with()


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectBaselineAnnualConsumptionTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(currency_unit='currency_dkk')
        self.customer.save()
        self.project = BenchmarkProject.objects.create(
            name_plain='test project',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            runtime=1,
            include_measured_costs=False,
            estimated_yearly_consumption_before=Decimal('456.78'),
            customer=self.customer,
            baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))

    def test_baseline_period_completed(self):
        self.project.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.project.baseline_to_timestamp = datetime(
            2013, 2, 1, tzinfo=pytz.utc)

        self.assertTrue(self.project.baseline_period_completed)

        with patch.object(Stage, 'mean_consumption_rate',
                          PhysicalQuantity(1, 'watt')):
            self.assertEqual(
                self.project.baseline_annual_consumption,
                self.project.get_preferred_consumption_unit_converter().
                extract_value(PhysicalQuantity(365, 'watt*day')))

    def test_baseline_incomplete(self):
        with patch.object(self.project, 'baseline_period_completed', False):
            self.assertEqual(
                self.project.baseline_annual_consumption,
                self.project.estimated_yearly_consumption_before)


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectBaselineAnnualCostsTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(currency_unit='currency_dkk')
        self.customer.save()

    def test_include_measured_costs(self):
        self.project = BenchmarkProject.objects.create(
            name_plain='test project',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            runtime=1,
            include_measured_costs=True,
            customer=self.customer,
            baseline_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2013, 2, 1, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))

        self.assertTrue(self.project.baseline_period_completed)

        with patch.object(Stage, 'mean_cost_rate',
                          PhysicalQuantity(1, 'currency_dkk*day^-1')):
            self.assertEqual(
                self.project.baseline_annual_costs,
                365)

    def test_exclude_calculated_cost(self):
        self.project = BenchmarkProject.objects.create(
            name_plain='test project',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            runtime=1,
            include_measured_costs=False,
            estimated_yearly_consumption_costs_before=Decimal('456.78'),
            customer=self.customer,
            baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))

        with patch.object(self.project, 'baseline_period_completed', True):
            self.assertEqual(
                self.project.baseline_annual_costs,
                self.project.estimated_yearly_consumption_costs_before)

    def test_baseline_period_incomplete(self):
        self.project = BenchmarkProject.objects.create(
            name_plain='test project',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            runtime=1,
            include_measured_costs=True,
            estimated_yearly_consumption_costs_before=Decimal('456.78'),
            customer=self.customer,
            baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))

        with patch.object(self.project, 'baseline_period_completed', False):
            self.assertEqual(
                self.project.baseline_annual_costs,
                self.project.estimated_yearly_consumption_costs_before)


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectAnnualCostSavingsTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        with replace_customer(self.customer):
            self.project = BenchmarkProject.objects.create(
                name_plain='test project',
                utility_type=utilitytypes.METER_CHOICES.electricity,
                runtime=1,
                include_measured_costs=False,
                estimated_yearly_consumption_before=Decimal('456.78'),
                baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
                baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
                result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
                result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))

    def test_project_completed(self):
        with patch.object(self.project, 'project_completed', True), \
                patch.object(
                    self.project, 'resulting_annual_cost_savings',
                    return_value=PhysicalQuantity(
                        1234, 'currency_dkk')):

            self.assertEqual(
                self.project.annual_cost_savings,
                self.project.resulting_annual_cost_savings().
                convert('currency_dkk'))

    def test_project_incomplete(self):
        with patch.object(self.project, 'project_completed', False):
            self.assertEqual(
                self.project.annual_cost_savings,
                self.project.
                expected_savings_in_yearly_total_costs)


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectPaybackPeriodTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.timezone('Europe/Copenhagen'))
        with replace_customer(self.customer):
            self.project = BenchmarkProject.objects.create(
                name_plain='test project',
                utility_type=utilitytypes.METER_CHOICES.electricity,
                runtime=1,
                include_measured_costs=False,
                subsidy=Decimal('456.78'),
                baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
                baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
                result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
                result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))

    def test_undefined(self):
        with patch.object(self.project, 'annual_cost_savings', 0):
            self.assertIsNone(self.project.payback_period_years)

    def test_welldefined(self):
        with patch.object(self.project, 'annual_cost_savings', 2), \
                patch.object(self.project, 'investment', 7):
            self.assertEquals(
                self.project.payback_period_years,
                (self.project.investment - Fraction(self.project.subsidy)) /
                self.project.annual_cost_savings)


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectGetGraphDataTest(TestCase):
    """
    Test the L{BenchmarkProject} class.
    """
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.utc,
            currency_unit='currency_dkk')
        trackuser._set_customer(self.customer)
        self.user = User.objects.create_user(
            'test@gridportal.dk',
            'password222w2222',
            user_type=User.CUSTOMER_USER,
            customer=self.customer)
        self.unit = BenchmarkProject.objects.create(
            name_plain='Some test project',
            background_plain='Some test description',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            baseline_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2013, 1, 3, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2013, 1, 11, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2013, 1, 13, tzinfo=pytz.utc))

        self.measurement_point = ConsumptionMeasurementPoint(
            name_plain='Test measurement point',
            role=ConsumptionMeasurementPoint.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.consumption = TestDataSeries(
            role=DataRoleField.CONSUMPTION,
            unit='kilowatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.save()

        self.measurement_point.consumption.stored_data.create(
            value=0, timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=10, timestamp=datetime(2013, 1, 1, 0, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=1000, timestamp=datetime(2013, 1, 11, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=1010, timestamp=datetime(2013, 1, 11, 0, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=1900, timestamp=datetime(2013, 1, 21, tzinfo=pytz.utc))

        self.unit.baseline_measurement_points.add(self.measurement_point)
        self.unit.result_measurement_points.add(self.measurement_point)

    def tearDown(self):
        trackuser._set_customer(None)
        trackuser._set_user(None)

    def test_samples_to_data_set(self):
        result = self.unit._samples_to_data_set(
            self.measurement_point,
            [
                self.measurement_point.rate.create_point_sample(
                    datetime(2013, 1, 2, tzinfo=pytz.utc),
                    PhysicalQuantity(42, self.measurement_point.rate.unit)),
            ],
            timedelta(minutes=4))
        self.assertEqual(
            result,
            [[unix_timestamp(datetime(2013, 1, 1, 23, 56, tzinfo=pytz.utc)),
              0.000042]])

    @unittest.skip('')
    def test_adjusted_start_time(self):
        data = self.unit.get_graph_data(self.measurement_point)

        # stage_1 should be rendered at duration start. Currently, rate
        # conversion will skip the first consumption sample it is made across,
        # hence the additional one minute.
        self.assertEqual(
            data['data'][0]['data'][0][0],
            unix_timestamp(self.unit.from_timestamp +
                           timedelta(minutes=1)))

        # stage 2 should be rendered at duration start. Currently, rate
        # conversion will skip the first consumption sample it is made across,
        # hence the additional one minute.
        self.assertEqual(
            data['data'][1]['data'][0][0],
            unix_timestamp(self.unit.from_timestamp +
                           timedelta(minutes=1)))

    def test_get_ticks_one_minute(self):
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = \
            datetime(2013, 1, 1, 0, 1, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_from_timestamp = datetime(2013, 1, 1, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = datetime(
            2013, 1, 1, 0, 1, tzinfo=pytz.utc)
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            self.assertEqual(
                ticks_list[0],
                [
                    unix_timestamp(
                        datetime(2013, 1, 1, 0, 0, tzinfo=pytz.utc)), 0])
            self.assertEqual(
                ticks_list[-1],
                [
                    unix_timestamp(
                        datetime(2013, 1, 1, 0, 1, tzinfo=pytz.utc)), 1])
            gettext_mock.assert_called_with('minutes')

    def test_get_ticks_59_minutes(self):
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = \
            datetime(2013, 1, 1, 0, 1, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_from_timestamp = \
            datetime(2013, 1, 1, 0, 20, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = \
            datetime(2013, 1, 1, 0, 59, tzinfo=pytz.utc)
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            tick_increment = 59 / 12
            for i in range(0, len(ticks_list)):
                self.assertEqual(
                    ticks_list[i],
                    [
                        unix_timestamp(
                            datetime(
                                2013, 1, 1, 0, i * tick_increment,
                                tzinfo=pytz.utc)), i * tick_increment])

            gettext_mock.assert_called_with('minutes')

    def test_get_ticks_1_hour_1_minute(self):
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = \
            datetime(2013, 1, 1, 0, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_from_timestamp = \
            datetime(2013, 1, 1, 0, 0, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = datetime(
            2013, 1, 1, 1, 1, tzinfo=pytz.utc)
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            tick_increment = 1
            for i in range(0, len(ticks_list)):
                self.assertEqual(
                    ticks_list[i],
                    [
                        unix_timestamp(
                            datetime(
                                2013, 1, 1, i * tick_increment,
                                tzinfo=pytz.utc)), i * tick_increment])

            gettext_mock.assert_called_with('hours')

    def test_get_ticks_23_hours_59_minutes(self):
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = \
            datetime(2013, 1, 1, 0, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_from_timestamp = \
            datetime(2013, 1, 1, 0, 0, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = \
            datetime(2013, 1, 1, 23, 59, tzinfo=pytz.utc)
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            tick_increment = 23 / 12 + 1
            for i in range(0, len(ticks_list) - 1):
                self.assertEqual(
                    ticks_list[i],
                    [
                        unix_timestamp(
                            datetime(
                                2013, 1, 1, i * tick_increment,
                                tzinfo=pytz.utc)), i * tick_increment])

            gettext_mock.assert_called_with('hours')

    def test_get_ticks_24_hours(self):
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = \
            datetime(2013, 1, 1, 0, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_from_timestamp = \
            datetime(2013, 1, 1, 0, 0, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = \
            datetime(2013, 1, 2, 0, 1, tzinfo=pytz.utc)
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            self.assertEqual(
                ticks_list[0],
                [
                    unix_timestamp(
                        datetime(2013, 1, 1, 0, tzinfo=pytz.utc)),
                    0])

            self.assertEqual(
                ticks_list[-1],
                [
                    unix_timestamp(
                        datetime(
                            2013, 1, 2, 0, tzinfo=pytz.utc)),
                    1])

            gettext_mock.assert_called_with('days')

    def test_get_ticks_29_days_23_hours_59_minutes(self):
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = \
            datetime(2013, 1, 1, 0, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_from_timestamp = datetime(2013, 1, 1, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = \
            datetime(2013, 1, 30, 23, 59, tzinfo=pytz.utc)
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            tick_increment = (30 / 12) + 1
            for i in range(0, len(ticks_list)):
                self.assertEqual(
                    ticks_list[i],
                    [
                        unix_timestamp(
                            self.unit.customer.timezone.localize(
                                datetime(2013, 1, 1 + i * tick_increment))),
                        i * tick_increment])

            gettext_mock.assert_called_with('days')

    def test_get_ticks_1_month(self):
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = \
            datetime(2013, 1, 1, 0, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_from_timestamp = \
            datetime(2013, 1, 1, 0, 0, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = \
            datetime(2013, 1, 31, 0, 0, tzinfo=pytz.utc)
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            self.assertEqual(
                ticks_list[0],
                [
                    unix_timestamp(
                        self.unit.customer.timezone.localize(
                            datetime(2013, 1, 1, 0))),
                    0])

            self.assertEqual(
                ticks_list[-1],
                [
                    unix_timestamp(
                        self.unit.customer.timezone.localize(
                            datetime(2013, 1, 31, 0))),
                    1])

            gettext_mock.assert_called_with('months')

    def test_get_ticks_1_year_minus_1_minute(self):
        self.unit.baseline_from_timestamp = self.unit.customer.timezone.\
            localize(datetime(2013, 1, 1))
        self.unit.baseline_to_timestamp = self.unit.customer.timezone.localize(
            datetime(2013, 1, 1, 0, 14))
        self.unit.save()

        self.unit.result_from_timestamp = self.unit.customer.timezone.localize(
            datetime(2013, 1, 1))
        self.unit.result_to_timestamp = self.unit.customer.timezone.localize(
            datetime(2013, 12, 31, 23, 59))
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            tick_increment = ((364 / 30) / 12) + 1

            for i in range(0, len(ticks_list)):
                self.assertEqual(
                    ticks_list[i],
                    [
                        unix_timestamp(
                            self.unit.customer.timezone.normalize(
                                self.unit.customer.timezone.localize(
                                    datetime(2013, 1, 1)) +
                                timedelta(days=30 * i * tick_increment))),
                        i * tick_increment])

            gettext_mock.assert_called_with('months')

    def test_get_ticks_1_year(self):
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = \
            datetime(2013, 1, 1, 0, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_from_timestamp = \
            datetime(2013, 1, 1, 0, 0, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = datetime(
            2014, 1, 1, 0, 0, tzinfo=pytz.utc)
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            self.assertEqual(
                ticks_list[0],
                [
                    unix_timestamp(
                        self.unit.customer.timezone.localize(
                            datetime(2013, 1, 1, 0))),
                    0])

            self.assertEqual(
                ticks_list[-1],
                [
                    unix_timestamp(
                        self.unit.customer.timezone.localize(
                            datetime(2014, 1, 1, 0))),
                    1])

            gettext_mock.assert_called_with('years')

    def test_get_ticks_42_years_two_minutes(self):
        self.unit.baseline_from_timestamp = datetime(
            2013, 1, 1, tzinfo=pytz.utc)
        self.unit.baseline_to_timestamp = \
            datetime(2013, 1, 1, 0, 14, tzinfo=pytz.utc)
        self.unit.save()

        self.unit.result_from_timestamp = \
            datetime(2013, 1, 1, 0, 0, tzinfo=pytz.utc)
        self.unit.result_to_timestamp = \
            datetime(2056, 1, 1, 0, 2, tzinfo=pytz.utc)
        self.unit.save()

        with patch('legacy.projects.models._') as gettext_mock:
            ticks_unit, ticks_list = self.unit._get_ticks()
            tick_increment = (42 / 12) + 1
            for i in range(0, len(ticks_list)):
                self.assertEqual(
                    ticks_list[i],
                    [
                        unix_timestamp(
                            self.unit.customer.timezone.localize(
                                datetime(2013, 1, 1) +
                                timedelta(days=365 * i * tick_increment))),
                        i * tick_increment])

            gettext_mock.assert_called_with('years')

    def test_get_resolution(self):
        """
        Assuming C{_get_resolution} will check its own post-conditions, this
        test will just invoke the method with border arguments.
        """
        some_datetime = datetime(2013, 1, 1, 1, 1, 1, tzinfo=pytz.utc)
        condense.floor(some_datetime, self.unit._get_resolution(
            duration_time=self.unit.CONDENSE_TO_HOURS -
            timedelta(seconds=1)), pytz.utc)
        condense.floor(some_datetime, self.unit._get_resolution(
            duration_time=self.unit.CONDENSE_TO_HOURS), pytz.utc)
        condense.floor(some_datetime, self.unit._get_resolution(
            duration_time=self.unit.CONDENSE_TO_DAYS -
            timedelta(seconds=1)), pytz.utc)
        condense.floor(some_datetime, self.unit._get_resolution(
            duration_time=self.unit.CONDENSE_TO_DAYS), pytz.utc)
        condense.floor(some_datetime, self.unit._get_resolution(
            duration_time=self.unit.CONDENSE_TO_MONTHS -
            timedelta(seconds=1)), pytz.utc)
        condense.floor(some_datetime, self.unit._get_resolution(
            duration_time=self.unit.CONDENSE_TO_MONTHS), pytz.utc)
        condense.floor(some_datetime, self.unit._get_resolution(
            duration_time=self.unit.CONDENSE_TO_YEARS -
            timedelta(seconds=1)), pytz.utc)
        condense.floor(some_datetime, self.unit._get_resolution(
            duration_time=self.unit.CONDENSE_TO_YEARS), pytz.utc)
        condense.floor(some_datetime, self.unit._get_resolution(
            duration_time=self.unit.CONDENSE_TO_YEARS
            * 42), pytz.utc)


@override_settings(ENCRYPTION_TESTMODE=True)
class TestStage(TestCase):
    """
    Test the L{Stage} model.
    """
    def setUp(self):
        """
        Instantiate a L{Stage} model for a C{Project}.
        """
        Provider.objects.create()
        self.customer = Customer(
            timezone=pytz.utc,
            currency_unit='currency_eur',
        )
        self.customer.save()
        trackuser._set_customer(self.customer)
        self.user = User.objects.create_user(
            'test@gridportal.dk',
            'password222w2222',
            user_type=User.CUSTOMER_USER,
            customer=self.customer)
        self.measurement_point = ConsumptionMeasurementPoint(
            name_plain='Test measurement point',
            role=ConsumptionMeasurementPoint.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.consumption = TestDataSeries.objects.create(
            role=DataRoleField.CONSUMPTION,
            unit='kilowatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.save()

        self.measurement_point.consumption.stored_data.create(
            value=0, timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=1000, timestamp=datetime(2013, 1, 5, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=2000, timestamp=datetime(2013, 1, 9, tzinfo=pytz.utc))

        self.project = BenchmarkProject.objects.create(
            name_plain='Some test project',
            background_plain='Some test description',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            baseline_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2013, 1, 5, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2013, 1, 5, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2013, 1, 9, tzinfo=pytz.utc))

        self.project.baseline_measurement_points.add(self.measurement_point)
        self.project.result_measurement_points.add(self.measurement_point)

    def tearDown(self):
        trackuser._set_customer(None)
        trackuser._set_user(None)

    def test_clean_duration_invalid(self):
        """
        Test the L{Stage.clean()} method.
        """
        self.project.baseline_from_timestamp = datetime(
            2013, 5, 23, 12, tzinfo=pytz.utc)
        self.project.baseline_to_timestamp = datetime(
            2013, 5, 23, 11, tzinfo=pytz.utc)

        with self.assertRaises(ValidationError):
            self.project.clean()

    def test_clean_valid(self):
        """
        Extend this test case as clean() validates more.
        """
        self.project.baseline_from_timestamp = datetime(
            2013, 5, 23, 12, tzinfo=pytz.utc)
        self.project.baseline_to_timestamp = datetime(
            2013, 5, 23, 13, tzinfo=pytz.utc)
        self.project.clean()

    def test_mean_consumption_rate(self):
        """
        Test mean_consumption_rate with various datateimes
        """
        # Testing where from time and to time has passed
        self.assertEqual(
            PhysicalQuantity(1000, 'kilowatt*hour') /
            PhysicalQuantity(4 * 24, 'hour'),
            self.project.baseline_stage.mean_consumption_rate)

        # Testing where now time is between from time and to time.
        time_now = datetime.now(pytz.utc).replace(
            minute=0, second=0, microsecond=0)
        from_timestamp = time_now - timedelta(days=4)
        to_timestamp = time_now + timedelta(days=1)

        self.measurement_point.consumption.stored_data.create(
            value=0, timestamp=from_timestamp)
        self.measurement_point.consumption.stored_data.create(
            value=1000, timestamp=to_timestamp)

        self.project.baseline_from_timestamp = from_timestamp
        self.project.baseline_to_timestamp = to_timestamp
        self.project.save()

        # Reloading project because of cache
        self.project = BenchmarkProject.objects.get(id=self.project.id)

        self.assertEqual(PhysicalQuantity(1000, 'kilowatt*hour') /
                         PhysicalQuantity(5 * 24, 'hour'),
                         self.project.baseline_stage.mean_consumption_rate)

        # Testing where whole stage is in the future
        self.project.baseline_from_timestamp = time_now + timedelta(days=1)
        self.project.baseline_to_timestamp = time_now + timedelta(days=5)
        self.project.save()

        # Reloading project because of cache
        self.project = BenchmarkProject.objects.get(id=self.project.id)

        self.assertEqual(
            PhysicalQuantity(0, 'kilowatt'),
            self.project.baseline_stage.mean_consumption_rate)

    def test_mean_cost_rate(self):
        """
        Test mean_cost_rate with various datateimes
        """
        tariff1 = Index.objects.create(
            name_plain="test tariff",
            unit="currency_eur*kilowatt^-1*hour^-1",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SPOT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            timezone='Europe/Copenhagen')
        tariff1.entry_set.create(
            from_timestamp=DATETIME_MIN,
            to_timestamp=DATETIME_MAX,
            value=Decimal(1))

        cost_graph = self.measurement_point.graph_set.create(
            role=DataRoleField.COST)
        cost = CostCalculation(
            graph=cost_graph,
            role=DataRoleField.COST,
            consumption=self.measurement_point.consumption,
            index=tariff1,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        cost.full_clean(exclude=['unit'])
        cost.save()

        # Testing where from time and to time has passed
        self.assertEqual(PhysicalQuantity(1000, 'currency_eur') /
                         PhysicalQuantity(4 * 24 * 60 * 60, 'second'),
                         self.project.baseline_stage.mean_cost_rate)

        # Testing where now time is between from time and to time.
        time_now = datetime.now(pytz.utc).replace(
            minute=0, second=0, microsecond=0)
        from_timestamp = time_now - timedelta(days=4)
        to_timestamp = time_now + timedelta(days=1)

        self.measurement_point.consumption.stored_data.create(
            value=0, timestamp=from_timestamp)
        self.measurement_point.consumption.stored_data.create(
            value=100, timestamp=to_timestamp)

        self.project.baseline_from_timestamp = from_timestamp
        self.project.baseline_to_timestamp = to_timestamp
        self.project.save()

        # Reloading project because of cache
        self.project = BenchmarkProject.objects.get(id=self.project.id)

        self.assertEqual(PhysicalQuantity(100, 'currency_eur') /
                         PhysicalQuantity(5 * 24 * 60 * 60, 'second'),
                         self.project.baseline_stage.mean_cost_rate)

        # Testing where whole stage is in the future
        self.project.baseline_from_timestamp = time_now + timedelta(days=1)
        self.project.baseline_to_timestamp = time_now + timedelta(days=5)
        self.project.save()

        # Reloading project because of cache
        self.project = BenchmarkProject.objects.get(id=self.project.id)

        self.assertEqual(PhysicalQuantity(0, 'second^-1*currency_eur'),
                         self.project.baseline_stage.mean_cost_rate)


@override_settings(ENCRYPTION_TESTMODE=True)
class TestAdditinalSaving(TestCase):
    """
    Test the L{AdditionalSaving} class.
    """
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(
            timezone=pytz.utc,
            currency_unit='currency_eur')
        self.customer.save()
        trackuser._set_customer(self.customer)
        self.project = BenchmarkProject.objects.create(
            name_plain='Some test project',
            background_plain='Some test description',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))
        self.project.save()

    def tearDown(self):
        trackuser._set_customer(None)
        trackuser._set_user(None)

    def test_save(self):
        self.unit = AdditionalSaving.objects.create(
            project=self.project,
            description_plain="Some description",
            before_energy=8,
            after_energy=7,
            before_cost=6,
            after_cost=5,
            before_co2=2,
            after_co2=1)

        loaded_unit = AdditionalSaving.objects.get(pk=self.unit.id)

        self.assertEqual(loaded_unit.project, self.project)
        self.assertEqual(loaded_unit.description_plain, "Some description")
        self.assertEqual(loaded_unit.before_energy, 8)
        self.assertEqual(loaded_unit.after_energy, 7)
        self.assertEqual(loaded_unit.before_cost, 6)
        self.assertEqual(loaded_unit.after_cost, 5)
        self.assertEqual(loaded_unit.before_co2, 2)
        self.assertEqual(loaded_unit.after_co2, 1)


@override_settings(ENCRYPTION_TESTMODE=True)
class TestCalculations(TestCase):
    """
    Test the different calculation methods on the L{BenchmarkProject} class
    """
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(
            timezone=pytz.utc,
            currency_unit='currency_eur')
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.measurement_point = ConsumptionMeasurementPoint(
            name_plain='Test measurement point',
            role=ConsumptionMeasurementPoint.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.consumption = TestDataSeries.objects.create(
            role=DataRoleField.CONSUMPTION,
            unit='kilowatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.save()

        self.measurement_point.consumption.stored_data.create(
            value=0, timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=1000, timestamp=datetime(2013, 1, 5, tzinfo=pytz.utc))
        self.measurement_point.consumption.stored_data.create(
            value=2000, timestamp=datetime(2013, 1, 9, tzinfo=pytz.utc))

        self.project = BenchmarkProject.objects.create(
            name_plain='Some test project',
            background_plain='Some test description',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            runtime=1,
            baseline_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2013, 1, 5, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2013, 1, 5, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2013, 1, 9, tzinfo=pytz.utc))

        self.project.baseline_measurement_points.add(self.measurement_point)
        self.project.result_measurement_points.add(self.measurement_point)

    def tearDown(self):
        trackuser._set_customer(None)
        trackuser._set_user(None)

    def test_save(self):
        self.unit = AdditionalSaving.objects.create(
            project=self.project,
            description_plain="Some description",
            before_energy=8,
            after_energy=7,
            before_cost=6,
            after_cost=5,
            before_co2=2,
            after_co2=1)

        loaded_unit = AdditionalSaving.objects.get(pk=self.unit.id)

        self.assertEqual(loaded_unit.project, self.project)
        self.assertEqual(loaded_unit.description_plain, "Some description")
        self.assertEqual(loaded_unit.before_energy, 8)
        self.assertEqual(loaded_unit.after_energy, 7)
        self.assertEqual(loaded_unit.before_cost, 6)
        self.assertEqual(loaded_unit.after_cost, 5)
        self.assertEqual(loaded_unit.before_co2, 2)
        self.assertEqual(loaded_unit.after_co2, 1)

    def test_co2_calculations(self):
        AdditionalSaving.objects.create(
            project=self.project,
            description_plain="Some description",
            before_energy=8,
            after_energy=7,
            before_cost=6,
            after_cost=5,
            before_co2=5,
            after_co2=1)

        AdditionalSaving.objects.create(
            project=self.project,
            description_plain="Some description",
            before_energy=8,
            after_energy=7,
            before_cost=6,
            after_cost=5,
            before_co2=5,
            after_co2=1)

        self.assertEqual(self.project.yearly_additional_co2(),
                         {'after': PhysicalQuantity(2, u'tonne'),
                          'before': PhysicalQuantity(10, u'tonne')})

        self.assertEqual(self.project.yearly_additional_co2_savings(),
                         PhysicalQuantity(8, u'tonne'))

        self.assertEqual(self.project.yearly_co2_savings(),
                         PhysicalQuantity(8, u'tonne'))

        self.assertEqual(self.project.yearly_co2_savings_pct(), 80)

        self.assertEqual(self.project.project_co2_savings(),
                         PhysicalQuantity(8, u'tonne') * (float(1) / 12))


@override_settings(
    ENCRYPTION_TESTMODE=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    CELERY_ALWAYS_EAGER=True,
    BROKER_BACKEND='memory')
class AnnualSavingsPotentialReportTaskTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.user = User.objects.create_user(
            'test@gridportal.dk',
            'password222w2222',
            user_type=User.CUSTOMER_USER,
            customer=self.customer)

    def test_empty_run(self):
        with replace_customer(self.customer), replace_user(self.user):
            task_status = AnnualSavingsPotentialReportTask.delay(
                {
                    'projects': dict(),
                })

        self.assertTrue(task_status.successful())

    def test_baselined_project(self):
        with replace_customer(self.customer), replace_user(self.user):
            project = BenchmarkProject.objects.create(
                name_plain='base-lined project',
                utility_type=utilitytypes.METER_CHOICES.electricity,
                runtime=1,
                include_measured_costs=False,
                estimated_yearly_consumption_costs_before=Decimal('456.78'),
                baseline_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
                baseline_to_timestamp=datetime(2013, 2, 1, tzinfo=pytz.utc),
                result_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
                result_to_timestamp=datetime(2014, 1, 1, tzinfo=pytz.utc))

            project.cost_set.create(
                cost=Decimal(246))

            with patch.object(Stage, 'mean_consumption_rate',
                              PhysicalQuantity(1, 'watt')), \
                    patch.object(BenchmarkProject,
                                 'resulting_annual_cost_savings',
                                 return_value=PhysicalQuantity(123,
                                                               'currency_dkk'),
                                 autospec=True):

                task_status = AnnualSavingsPotentialReportTask.delay(
                    {
                        'projects': {project.id: dict()},
                    })

            self.assertTrue(task_status.successful())

            self.assertEqual(
                task_status.result['projects'][project.id][
                    'baseline_annual_consumption'],
                project.get_preferred_consumption_unit_converter().
                extract_value(PhysicalQuantity(365, 'watt*day')))

            self.assertEqual(
                task_status.result['projects'][project.id][
                    'baseline_annual_costs'],
                project.estimated_yearly_consumption_costs_before)


@override_settings(ENCRYPTION_TESTMODE=True)
class FinalizeAnnualSavingsPotentialReportViewTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.utc,
            currency_unit='currency_eur')
        with replace_customer(self.customer):
            self.project = BenchmarkProject.objects.create(
                name_plain='test project',
                utility_type=utilitytypes.METER_CHOICES.electricity,
                runtime=1,
                include_measured_costs=False,
                estimated_yearly_consumption_before=Decimal('456.78'),
                baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
                baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
                result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
                result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))

    def test_generate_report(self):
        with replace_customer(self.customer):
            view = FinalizeAnnualSavingsPotentialReportView()
            view.generate_report(
                {
                    'projects': {
                        self.project.id: {
                            'baseline_annual_consumption': 592932,
                            'baseline_annual_costs': 563285,
                            'expected_annual_cost_savings': 337971,
                            'subsidy': 102743,
                            'investment': 850000,
                            'payback_period_years': 2.52,
                        },
                    },
                    'total_expected_annual_cost_savings': 1.23,
                    'total_subsidy': 6.66,
                    'total_investment': 9.99,
                    'total_payback_period': 2.34,
                },
                datetime.now(pytz.utc))


@override_settings(ENCRYPTION_TESTMODE=True)
class BenchmarkProjectManagerTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer.objects.create(
            currency_unit='currency_dkk')
        self.user = User.objects.create_user(
            'test@gridportal.dk',
            'password222w2222',
            user_type=User.CUSTOMER_USER,
            customer=self.customer)

        with replace_customer(self.customer), replace_user(self.user):
            self.measurement_point = ConsumptionMeasurementPoint(
                customer=self.customer,
                name_plain='Test measurement point',
                role=ConsumptionMeasurementPoint.CONSUMPTION_MEASUREMENT_POINT,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

            self.measurement_point.consumption = TestDataSeries.objects.create(
                customer=self.customer,
                role=DataRoleField.CONSUMPTION,
                unit='kilowatt*hour',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

            self.measurement_point.save()

            self.project = BenchmarkProject.objects.create(
                name_plain='Some test project',
                customer=self.customer,
                background_plain='Some test description',
                utility_type=utilitytypes.METER_CHOICES.electricity,
                runtime=1,
                baseline_from_timestamp=datetime(2013, 1, 1, tzinfo=pytz.utc),
                baseline_to_timestamp=datetime(2013, 1, 5, tzinfo=pytz.utc),
                result_from_timestamp=datetime(2013, 1, 5, tzinfo=pytz.utc),
                result_to_timestamp=datetime(2013, 1, 9, tzinfo=pytz.utc))

        self.project.baseline_measurement_points.add(self.measurement_point)
        self.project.result_measurement_points.add(self.measurement_point)

    def test_no_customer_and_no_user(self):
        self.assertEqual(
            self.project, BenchmarkProject.objects.get())

    def test_constraint_customer(self):
        with replace_customer(self.customer), replace_user(self.user):
            self.assertEqual(
                self.project, BenchmarkProject.objects.get())

    def test_constraint_wrong_customer(self):
        customer = Customer()
        customer.save()
        self.project.customer = customer
        self.project.save()
        with replace_customer(self.customer), replace_user(self.user):
            self.assertFalse(BenchmarkProject.objects.all().exists())

    def test_user_contraint(self):
        CollectionConstraint.objects.create(
            collection=self.measurement_point,
            userprofile=self.user.userprofile)
        with replace_customer(self.customer), replace_user(self.user):
            self.assertEqual(
                self.project, BenchmarkProject.objects.get())

    def test_wrong_user_constraint(self):
        self.user.userprofile.collections.clear()
        self.user.userprofile.save()

        group = Collection.objects.create(
            customer=self.customer,
            role=Collection.GROUP,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

        CollectionConstraint.objects.create(
            collection=group, userprofile=self.user.userprofile)
        with replace_customer(self.customer), replace_user(self.user):
            self.assertFalse(BenchmarkProject.objects.all().exists())


@override_settings(ENCRYPTION_TESTMODE=True)
class AnnualSavingsPotentialReportGenerationFormTest(TestCase):
    def test_projects_queryset(self):
        Provider.objects.create()
        customer = Customer(currency_unit='currency_dkk')
        customer.save()
        project = BenchmarkProject.objects.create(
            name_plain='test project',
            utility_type=utilitytypes.METER_CHOICES.electricity,
            runtime=1,
            include_measured_costs=False,
            estimated_yearly_consumption_before=Decimal('456.78'),
            customer=customer,
            baseline_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            baseline_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_from_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc),
            result_to_timestamp=datetime(2000, 1, 1, tzinfo=pytz.utc))
        form = AnnualSavingsPotentialReportGenerationForm()
        self.assertTrue(
            form.fields['projects'].queryset.filter(id=project.id).exists())
