# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from fractions import Fraction
from datetime import datetime
from datetime import date
from mock import patch
import unittest

from django.test.utils import override_settings
from django.test import TestCase

import pytz

from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.tests import TestDataSeries
from legacy.measurementpoints.models import CostCalculation
from gridplatform.customers.models import Customer
from gridplatform.users.models import User
from gridplatform.trackuser import replace_customer
from gridplatform.trackuser import replace_user
from gridplatform import trackuser
from gridplatform.providers.models import Provider

from .forms import GenerateEnergyUseReportForm
from .tasks import EnergyUseReportTask
from .tasks import AreaErrorCollector
from .models import EnergyUseArea
from .models import EnergyUseReport
from .views import FinalizeEnergyUseReportView


class mock_scheduled(object):
    def values(self):
        return []


@override_settings(ENCRYPTION_TESTMODE=True)
class GenerateEnergyUseReportFormTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(timezone=pytz.utc)
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.energy_use_report = EnergyUseReport.objects.create(
            customer=self.customer,
            title_plain='Test energy use report',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.energy_use_area = EnergyUseArea.objects.create(
            report=self.energy_use_report,
            name_plain='coffee production')

    def tearDown(self):
        trackuser._set_customer(None)

    def test_validation_failure(self):
        form = GenerateEnergyUseReportForm(
            {'energy_use_report': None,
             'from_date': None,
             'to_date': None})

        with patch('celery.task.control.inspect.scheduled',
                   new=mock_scheduled):
            self.assertFalse(form.is_valid())

    def test_date_validation_failure(self):
        form = GenerateEnergyUseReportForm(
            {'energy_use_report': self.energy_use_report.id,
             'from_date': '2013-02-01',
             'to_date': '2013-01-01'})

        with patch('legacy.energy_use_reports.forms._') as mock:
            self.assertFalse(form.is_valid())
            mock.assert_called_with(
                u'The start date must be before the end date.')

    def test_validation_success(self):
        form = GenerateEnergyUseReportForm(
            {
                'energy_use_report': self.energy_use_report.id,
                'from_date': '2013-01-01',
                'to_date': '2013-02-01',
                'previous_period_from_date': '2012-12-01',
                'previous_period_to_date': '2012-12-31',
            }
        )

        with patch('celery.task.control.inspect.scheduled',
                   new=mock_scheduled):
            self.assertTrue(form.is_valid())

    def test_single_day_validation_success(self):
        form = GenerateEnergyUseReportForm(
            {
                'energy_use_report': self.energy_use_report.id,
                'from_date': '2013-01-01',
                'to_date': '2013-01-01',
                'previous_period_from_date': '2012-12-31',
                'previous_period_to_date': '2012-12-31',
            }
        )

        with patch('celery.task.control.inspect.scheduled',
                   new=mock_scheduled):
            self.assertTrue(form.is_valid())


@override_settings(
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    CELERY_ALWAYS_EAGER=True,
    BROKER_BACKEND='memory',
    ENCRYPTION_TESTMODE=True)
class StartReportGenerationViewTest(TestCase):
    fixtures = ["super_user_and_customer.json"]

    def setUp(self):
        self.customer = Customer.objects.get()
        Provider.objects.create()

        self.energy_use_report = EnergyUseReport.objects.create(
            customer=self.customer,
            title_plain='Test energy use report',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.energy_use_area = EnergyUseArea.objects.create(
            report=self.energy_use_report,
            name_plain='coffee production')

        self.client.post(
            '/login/',
            {
                'username': 'super',
                'password': '123'})

    def test_validation_failure(self):
        """
        Responds with a C{JsonResponseBadRequest} if invalid form is submitted.
        """
        response = self.client.post(
            '/energy_use_reports/start_report/',
            data={
                'energy_use_report': self.energy_use_report.id,
                'from_date': '2013-02-01',
                'to_date': '2013-01-01'})
        self.assertNotContains(response, 'XYZXYZXYZ', status_code=400)

    def test_validation_success(self):
        with patch('celery.task.control.inspect.scheduled',
                   new=mock_scheduled):
            response = self.client.post(
                '/energy_use_reports/start_report/',
                data={
                    'energy_use_report': self.energy_use_report.id,
                    'from_date': '2013-01-01',
                    'to_date': '2013-02-01',
                    'previous_period_from_date': '2012-12-01',
                    'previous_period_to_date': '2012-12-31'})
            self.assertNotContains(response, 'XYZXYZXYZ')


@override_settings(
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    CELERY_ALWAYS_EAGER=True,
    BROKER_BACKEND='memory',
    ENCRYPTION_TESTMODE=True)
class CollectEnergyUseReportDataTaskTest(TestCase):

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(timezone=pytz.utc)
        self.customer.save()
        trackuser._set_customer(self.customer)
        self.user = User.objects.create_user(
            'username', 'password', user_type=User.CUSTOMER_USER,
            customer=self.customer)

        self.energy_use_report = EnergyUseReport.objects.create(
            customer=self.customer,
            title_plain='Test energy use report',
            currency_unit='currency_dkk',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.energy_use_area = EnergyUseArea.objects.create(
            report=self.energy_use_report,
            name_plain='coffee production')

    def tearDown(self):
        trackuser._set_customer(None)

    def test_empty_report(self):
        with replace_customer(self.customer), replace_user(self.user):
            task_status = EnergyUseReportTask.delay(
                {
                    'energy_use_report_id': self.energy_use_report.id,
                    'from_date': date(2013, 1, 1),
                    'to_date': date(2013, 1, 2),
                    'previous_period_from_date': date(2012, 12, 31),
                    'previous_period_to_date': date(2012, 12, 31),
                    'include_cost': True,
                    'include_co2': True})

        self.assertTrue(task_status.successful())

        self.assertEqual(
            task_status.result['data'][self.energy_use_area.id]['cost'], 0)
        self.assertEqual(
            task_status.result['data'][self.energy_use_area.id]['consumption'],
            0)

        self.assertTrue(task_status.result['include_cost'])
        self.assertTrue(task_status.result['include_co2'])

    @unittest.skip(
        'Condensing/caching currently does not provide the "incomplete" error')
    def test_non_empty_report(self):
        mp1 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain='MP1',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp1.consumption = TestDataSeries(
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp1.save()
        mp2 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain='MP2',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp2.consumption = TestDataSeries(
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp2.save()

        # 0.42 DKK/kWh
        tariff = TestDataSeries.objects.create(
            role=DataRoleField.ELECTRICITY_TARIFF,
            unit='millicurrency_dkk*kilowatt^-1*hour^-1',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        tariff.stored_data.create(
            timestamp=datetime(2013, 1, 1, tzinfo=self.customer.timezone),
            value=420)

        mp2.save()

        cost_graph = mp2.graph_set.create(
            role=DataRoleField.COST)
        cost = CostCalculation(
            graph=cost_graph,
            role=DataRoleField.COST,
            consumption=mp2.consumption,
            index=tariff,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        cost.full_clean(exclude=['unit'])
        cost.save()

        # 2 kWh extrapolated.
        mp2.consumption.stored_data.create(
            timestamp=datetime(2013, 1, 1, 1, tzinfo=self.customer.timezone),
            value=0)
        mp2.consumption.stored_data.create(
            timestamp=datetime(2013, 1, 2, tzinfo=self.customer.timezone),
            value=2000000)

        mp3 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain='MP3',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp3.consumption = TestDataSeries(
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp3.save()

        self.energy_use_area.measurement_points.add(mp1)
        self.energy_use_area.measurement_points.add(mp2)

        energy_use_area2 = EnergyUseArea.objects.create(
            report=self.energy_use_report,
            name_plain='coke production')
        energy_use_area2.measurement_points.add(mp3)

        with replace_customer(self.customer), replace_user(self.user):
            task_status = EnergyUseReportTask.delay(
                {
                    'energy_use_report_id': self.energy_use_report.id,
                    'from_date': date(2013, 1, 1),
                    'to_date': date(2013, 1, 2),
                    'include_cost': True,
                    'include_co2': True})

        self.assertTrue(task_status.successful())

        # should be 2 kWh
        self.assertEqual(
            task_status.result['data'][self.energy_use_area.id]['consumption'],
            2)

        # should cost 0.84 DKK = 0.42 DKK/kWh * 2 kWh
        self.assertEqual(
            task_status.result['data'][self.energy_use_area.id]['cost'],
            Fraction(84, 100))

        self.assertEqual(
            task_status.result['data'][energy_use_area2.id]['cost'], 0)
        self.assertEqual(
            task_status.result['data'][energy_use_area2.id]['consumption'], 0)

        unicode_errors = map(unicode, task_status.result['errors'])

        expected_errors = []
        error_collector = AreaErrorCollector(
            expected_errors, mp1, self.energy_use_area)
        error_collector.extrapolated_consumption_current_period()
        error_collector.extrapolated_consumption_previous_period()
        error_collector.no_tariff()

        error_collector = AreaErrorCollector(
            expected_errors, mp2, self.energy_use_area)
        error_collector.extrapolated_consumption_current_period()
        error_collector.extrapolated_consumption_previous_period()
        error_collector.extrapolated_cost_current_period()
        error_collector.extrapolated_cost_previous_period()

        for expected_error in map(unicode, expected_errors):
            self.assertIn(expected_error, unicode_errors)

    @unittest.skip(
        'Condensing/caching currently does not provide the "incomplete" error')
    def test_non_empty_report_with_main_measurement_points(self):
        mp1 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain='MP1',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp1.consumption = TestDataSeries(
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp1.save()

        mp2 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain='MP2',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp2.consumption = TestDataSeries(
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp2.save()

        # 0.42 DKK/kWh
        tariff = TestDataSeries.objects.create(
            role=DataRoleField.ELECTRICITY_TARIFF,
            unit='millicurrency_dkk*kilowatt^-1*hour^-1',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        tariff.stored_data.create(
            timestamp=datetime(2013, 1, 1, tzinfo=self.customer.timezone),
            value=420)

        cost_graph = mp2.graph_set.create(role=DataRoleField.COST)
        cost = CostCalculation(
            graph=cost_graph,
            consumption=mp2.consumption,
            index=tariff,
            utility_type=mp2.utility_type,
            role=DataRoleField.COST)
        cost.full_clean(exclude=['unit'])
        cost.save()

        # 2 kWh extrapolated.
        mp2.consumption.stored_data.create(
            timestamp=datetime(2013, 1, 1, 1, tzinfo=self.customer.timezone),
            value=0)
        mp2.consumption.stored_data.create(

            timestamp=datetime(2013, 1, 2, tzinfo=self.customer.timezone),
            value=2000000)

        mp3 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain='MP3',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp3.consumption = TestDataSeries(
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        mp3.save()

        # 4 kWh extrapolated
        mp3.consumption.stored_data.create(
            timestamp=datetime(2013, 1, 1, 1, tzinfo=self.customer.timezone),
            value=0)
        mp3.consumption.stored_data.create(
            timestamp=datetime(2013, 1, 2, tzinfo=self.customer.timezone),
            value=4000000)

        cost_graph = mp3.graph_set.create(role=DataRoleField.COST)
        cost = CostCalculation(
            graph=cost_graph,
            consumption=mp3.consumption,
            index=tariff,
            utility_type=mp3.utility_type,
            role=DataRoleField.COST)
        cost.full_clean(exclude=['unit'])
        cost.save()

        self.energy_use_area.measurement_points.add(mp1)
        self.energy_use_area.measurement_points.add(mp2)

        self.energy_use_report.main_measurement_points.add(mp3)

        with replace_customer(self.customer), replace_user(self.user):
            task_status = EnergyUseReportTask.delay(
                {
                    'energy_use_report_id': self.energy_use_report.id,
                    'from_date': date(2013, 1, 1),
                    'to_date': date(2013, 1, 2),
                    'include_cost': True,
                    'include_co2': True})

        self.assertTrue(task_status.successful())

        # should be 2 kWh
        self.assertEqual(
            task_status.result['data'][self.energy_use_area.id]['consumption'],
            2)

        # should be 4 kWh
        self.assertEqual(
            task_status.result['total_consumption'], 4)

        self.assertEqual(
            task_status.result['total_previous_consumption'], 0)

        # should cost 0.84 DKK = 0.42 DKK/kWh * 2 kWh
        self.assertEqual(
            task_status.result['data'][self.energy_use_area.id]['cost'],
            Fraction(84, 100))

        # should cost 1.68 DKK = 0.42 DKK/kWh * 4 kWh
        self.assertEqual(
            task_status.result['total_cost'], Fraction(168, 100))

        self.assertEqual(
            task_status.result['total_previous_cost'], 0)

        unicode_errors = map(unicode, task_status.result['errors'])

        expected_errors = []
        error_collector = AreaErrorCollector(
            expected_errors, mp1, self.energy_use_area)
        error_collector.extrapolated_consumption_current_period()
        error_collector.extrapolated_consumption_previous_period()
        error_collector.no_tariff()

        error_collector = AreaErrorCollector(
            expected_errors, mp2, self.energy_use_area)
        error_collector.extrapolated_consumption_current_period()
        error_collector.extrapolated_consumption_previous_period()
        error_collector.extrapolated_cost_current_period()
        error_collector.extrapolated_cost_previous_period()

        for expected_error in map(unicode, expected_errors):
            self.assertIn(expected_error, unicode_errors)


@override_settings(ENCRYPTION_TESTMODE=True)
class FinalizeEnergyUseReportViewTest(TestCase):

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(timezone=pytz.utc)
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.energy_use_report = EnergyUseReport.objects.create(
            customer=self.customer,
            title_plain='Test energy use report',
            currency_unit='currency_dkk',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.energy_use_area1 = EnergyUseArea.objects.create(
            report=self.energy_use_report,
            name_plain='coffee production')

        self.energy_use_area2 = EnergyUseArea.objects.create(
            report=self.energy_use_report,
            name_plain='coke production')

    def tearDown(self):
        trackuser._set_customer(None)

    def test_generate_report(self):
        view = FinalizeEnergyUseReportView()
        view.generate_report(
            {
                'energy_use_report': self.energy_use_report.id,
                'data': {
                    self.energy_use_area1.id: {
                        'consumption': Fraction(2, 3),
                        'cost': Fraction(1, 3),
                        'co2': Fraction(1, 4),
                        'previous_consumption': Fraction(22, 30),
                        'previous_cost': Fraction(11, 3),
                        'previous_co2': Fraction(11, 4),
                    },
                    self.energy_use_area2.id: {
                        'consumption': Fraction(4, 7),
                        'cost': Fraction(7, 11),
                        'co2': Fraction(5, 4),
                        'previous_consumption': Fraction(2, 7),
                        'previous_cost': Fraction(65, 110),
                        'previous_co2': Fraction(3, 4),
                    },
                },
                'errors': [
                    'There is less coffeine in coke than in coffee',
                    'There is too little coke in coke',
                    'And here comes a long error message, which describe in'
                    'great detail why coffee is broke, and in particular the'
                    'cost of coffee is undefined.  '
                    'It appears that coffee tends'
                    'to just evaporate before our eyes, and as such our coffee'
                    'demands cannot be met by any amount of coffee supply.  '
                    'Come '
                    'to think of it --- coffee should really be a utility type'
                    'of its own.'],
                'from_date': date(2013, 8, 1),
                'to_date': date(2013, 8, 30),
                'previous_from_date': date(2013, 7, 1),
                'previous_to_date': date(2013, 7, 31),
                'graph_data': {
                    'options': {
                        'colors': ['#BEEEFF'],
                        'yaxis': {
                            'title': 'kWh',
                        },
                        'xaxis': {
                            'title': 'Total 46 kWh',
                            'ticks': [(0.33, '1/3')],
                            'min': 0,
                            'max': 47,
                        },
                    },
                    'data': [
                        {
                            'bars': {'show': True},
                            'data': [(0, 1), (2, 5)],
                        },
                    ],
                },
                'include_cost': False,
                'include_co2': False,
            },
            datetime.now(pytz.utc))

    def test_generate_report_with_cost(self):
        view = FinalizeEnergyUseReportView()
        view.generate_report(
            {
                'energy_use_report': self.energy_use_report.id,
                'data': {
                    self.energy_use_area1.id: {
                        'consumption': Fraction(2, 3),
                        'cost': Fraction(1, 3),
                        'co2': Fraction(1, 4),
                        'previous_consumption': Fraction(22, 30),
                        'previous_cost': Fraction(11, 3),
                        'previous_co2': Fraction(11, 4),
                    },
                    self.energy_use_area2.id: {
                        'consumption': Fraction(4, 7),
                        'cost': Fraction(7, 11),
                        'co2': Fraction(5, 4),
                        'previous_consumption': Fraction(2, 7),
                        'previous_cost': Fraction(65, 110),
                        'previous_co2': Fraction(3, 4),
                    },
                },
                'errors': [
                    'There is less coffeine in coke than in coffee',
                    'There is too little coke in coke',
                    'And here comes a long error message, which describe in'
                    'great detail why coffee is broke, and in particular the'
                    'cost of coffee is undefined.  '
                    'It appears that coffee tends'
                    'to just evaporate before our eyes, and as such our coffee'
                    'demands cannot be met by any amount of coffee supply.  '
                    'Come '
                    'to think of it --- coffee should really be a utility type'
                    'of its own.'],
                'from_date': date(2013, 8, 1),
                'to_date': date(2013, 8, 30),
                'previous_from_date': date(2013, 7, 1),
                'previous_to_date': date(2013, 7, 31),
                'graph_data': {
                    'options': {
                        'colors': ['#BEEEFF'],
                        'yaxis': {
                            'title': 'kWh',
                        },
                        'xaxis': {
                            'title': 'Total 46 kWh',
                            'ticks': [(0.33, '1/3')],
                            'min': 0,
                            'max': 47,
                        },
                    },
                    'data': [
                        {
                            'bars': {'show': True},
                            'data': [(0, 1), (2, 5)],
                        },
                    ],
                },
                'include_cost': True,
                'include_co2': False,
            },
            datetime.now(pytz.utc))

    def test_generate_report_with_co2(self):
        view = FinalizeEnergyUseReportView()
        view.generate_report(
            {
                'energy_use_report': self.energy_use_report.id,
                'data': {
                    self.energy_use_area1.id: {
                        'consumption': Fraction(2, 3),
                        'cost': Fraction(1, 3),
                        'co2': Fraction(1, 4),
                        'previous_consumption': Fraction(22, 30),
                        'previous_cost': Fraction(11, 3),
                        'previous_co2': Fraction(11, 4),
                    },
                    self.energy_use_area2.id: {
                        'consumption': Fraction(4, 7),
                        'cost': Fraction(7, 11),
                        'co2': Fraction(5, 4),
                        'previous_consumption': Fraction(2, 7),
                        'previous_cost': Fraction(65, 110),
                        'previous_co2': Fraction(3, 4),
                    },
                },
                'errors': [
                    'There is less coffeine in coke than in coffee',
                    'There is too little coke in coke',
                    'And here comes a long error message, which describe in'
                    'great detail why coffee is broke, and in particular the'
                    'cost of coffee is undefined.  '
                    'It appears that coffee tends'
                    'to just evaporate before our eyes, and as such our coffee'
                    'demands cannot be met by any amount of coffee supply.  '
                    'Come '
                    'to think of it --- coffee should really be a utility type'
                    'of its own.'],
                'from_date': date(2013, 8, 1),
                'to_date': date(2013, 8, 30),
                'previous_from_date': date(2013, 7, 1),
                'previous_to_date': date(2013, 7, 31),
                'graph_data': {
                    'options': {
                        'colors': ['#BEEEFF'],
                        'yaxis': {
                            'title': 'kWh',
                        },
                        'xaxis': {
                            'title': 'Total 46 kWh',
                            'ticks': [(0.33, '1/3')],
                            'min': 0,
                            'max': 47,
                        },
                    },
                    'data': [
                        {
                            'bars': {'show': True},
                            'data': [(0, 1), (2, 5)],
                        },
                    ],
                },
                'co2_graph_data': {
                    'options': {
                        'colors': ['#BEEEFF'],
                        'yaxis': {
                            'title': 'kg',
                        },
                        'xaxis': {
                            'title': 'Total 46 kg',
                            'ticks': [(0.33, '1/3')],
                            'min': 0,
                            'max': 47,
                        },
                    },
                    'data': [
                        {
                            'bars': {'show': True},
                            'data': [(0, 1), (2, 5)],
                        },
                    ],
                },
                'include_cost': False,
                'include_co2': True,
            },
            datetime.now(pytz.utc))
