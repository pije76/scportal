# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from datetime import datetime, timedelta
from fractions import Fraction
import functools
import itertools
import operator
import unittest

from mock import Mock
from mock import patch
import pytz

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django import forms
from django.db.models import ProtectedError

from gridplatform import trackuser
from gridplatform.customers.models import Customer
from gridplatform.encryption.testutils import encryption_context
from gridplatform.encryption.testutils import no_encryption
from gridplatform.providers.models import Provider
from gridplatform.trackuser import replace_customer
from gridplatform.trackuser import replace_user
from gridplatform.users.models import User
from gridplatform.utils import condense
from gridplatform.utils import utilitytypes
from gridplatform.utils.iter_ext import count_extended
from gridplatform.utils.iter_ext import pairwise
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.unitconversion import PhysicalQuantity
from legacy.devices.models import Agent
from legacy.devices.models import Meter
from legacy.devices.models import PhysicalInput
from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.models import CollectionConstraint
from .fields import DataRoleField
from .interpolationcloud import InterpolationCloud
from .models import AbstractGraph
from .models import Chain
from .models import Co2Calculation
from .models import CostCalculation
from .models import DataSeries
from .models import DegreeDayCorrection
from .models import HeatingDegreeDays
from .models import IndexCalculation
from .models import Location
from .models import Multiplication
from .models import PiecewiseConstantIntegral
from .models import RateConversion
from .models import SimpleLinearRegression
from .models import Summation
from .models import Utilization
from .models.dataseries import UndefinedSamples
from .models.mixins import CacheOptimizedCalculateDevelopmentMixin
from .models.mixins import VariablyBoundAccumulationMixin
from .proxies import ConsumptionMeasurementPoint
from .proxies import ConsumptionMeasurementPointSummation
from .proxies import ImportedMeasurementPoint
from .tasks import get_condensed_samples_task
from .tasks import get_samples_task


class TestDataSeries(DataSeries):
    """
    Simplest concrete implementation of the abstract L{DataSeries} class.
    """

    def get_recursive_condense_resolution(self, resolution):
        """
        Unless recursive condension is the particular subject to test, it is
        disabled during unit-testsing.
        """
        return None

    def calculate_development(self, from_timestamp, to_timestamp):
        assert self.is_accumulation()

        try:
            from_sample = next(iter(
                self.get_samples(from_timestamp, from_timestamp)))
            to_sample = next(iter(
                self.get_samples(to_timestamp, to_timestamp)))

            return self.create_range_sample(
                from_timestamp, to_timestamp,
                to_sample.physical_quantity - from_sample.physical_quantity,
                uncachable=(
                    from_sample.uncachable or
                    to_sample.uncachable),
                extrapolated=(
                    from_sample.extrapolated or
                    to_sample.extrapolated))
        except StopIteration:
            return None


class DataSeriesMock(TestDataSeries):
    def depends_on(self):
        if hasattr(self, 'depends_on_list'):
            return self.depends_on_list
        else:
            return []

    def _get_samples(self, from_timestamp, to_timestamp):
        if not hasattr(self, 'raw_data_samples'):
            self.raw_data_samples = []
        for s in self.raw_data_samples:
            if from_timestamp <= s.from_timestamp <= s.to_timestamp <= \
                    to_timestamp:
                yield s


class DataSeriesTestSpecification(object):
    """
    A C{DataSeriesTestSpecification} is a mixin for C{TestCase}s that test
    C{DataSeries}.  It defines abstract test methods which should be
    implemented for all L{DataSeries} specializations.
    """

    def test_depends_on(self):
        raise NotImplementedError()

    def test_get_samples(self):
        raise NotImplementedError()

    def test_get_underlying_function(self):
        raise NotImplementedError()

    def test_calculate_development(self):
        raise NotImplementedError()


class ENPIMixinTestSpecification(DataSeriesTestSpecification):
    """
    A C{ENPIMixinTestSpecification} is a L{DataSeriesTestSpecification} for
    L{DataSeries} that are mixed with the L{ENPIMixin}.
    """

    def test_calculate_enpi(self):
        raise NotImplementedError()


@override_settings(ENCRYPTION_TESTMODE=True)
class ChainTest(TestCase):
    """
    Test the L{Chain} data series.
    """

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)
        assert self.customer is trackuser.get_customer()

        self.customer.electricity_consumption = "kilowatt*hour"
        self.customer.timezone = pytz.utc

        self.tariff = Chain.objects.create(
            role=DataRoleField.ELECTRICITY_TARIFF,
            unit='millicurrency_dkk*kilowatt^-1*hour^-1',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.subtariff1 = TestDataSeries.objects.create(
            role=DataRoleField.ELECTRICITY_TARIFF,
            unit='millicurrency_dkk*kilowatt^-1*hour^-1',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.subtariff2 = TestDataSeries.objects.create(
            role=DataRoleField.ELECTRICITY_TARIFF,
            unit='millicurrency_dkk*gigajoule^-1',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.start_time = datetime(2013, 1, 1, tzinfo=pytz.utc)

        self.period1 = self.tariff.links.create(
            valid_from=self.start_time + timedelta(hours=12),
            data_series=self.subtariff1)

        self.period2 = self.tariff.links.create(
            valid_from=self.start_time + timedelta(hours=24),
            data_series=self.subtariff2)

        self.subtariff1.stored_data.create(
            timestamp=self.start_time,
            value=1)
        self.subtariff1.stored_data.create(
            timestamp=self.start_time + timedelta(hours=8),
            value=2)
        self.subtariff1.stored_data.create(
            timestamp=self.start_time + timedelta(hours=16),
            value=3)
        self.subtariff2.stored_data.create(
            timestamp=self.start_time + timedelta(hours=8),
            value=4)
        self.subtariff2.stored_data.create(
            timestamp=self.start_time + timedelta(hours=20),
            value=5)

        self.consumption = TestDataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.consumption.stored_data.create(
            value=0, timestamp=self.start_time)
        self.consumption.stored_data.create(
            value=100, timestamp=self.start_time + timedelta(hours=48))

        self.cost = CostCalculation.objects.create(
            customer=self.customer,
            role=DataRoleField.COST,
            unit='currency_dkk',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            consumption=self.consumption,
            tariff=self.tariff)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_get_samples(self):
        """
        Test L{DerivedDataSeries.get_samples()} with formula
        DerivedDataSeries.SIMPLE_JOIN.

        @see: L{setUp()}
        """
        samples_iterator = iter(
            self.tariff.get_samples(
                self.start_time,
                to_timestamp=self.start_time + timedelta(hours=48)))

        self.assertEqual(
            next(samples_iterator),
            self.tariff.create_range_sample(
                self.start_time + timedelta(hours=12),
                self.start_time + timedelta(hours=16),
                PhysicalQuantity(2, self.subtariff1.unit)))

        self.assertEqual(
            next(samples_iterator),
            self.tariff.create_range_sample(
                self.start_time + timedelta(hours=16),
                self.start_time + timedelta(hours=24),
                PhysicalQuantity(3, self.subtariff1.unit)))

        self.assertEqual(
            next(samples_iterator),
            self.tariff.create_range_sample(
                self.start_time + timedelta(hours=24),
                self.start_time + timedelta(hours=48),
                PhysicalQuantity(5, self.subtariff2.unit)))


class DataRoleFieldTest(TestCase):
    """
    Tests for L{DataRoleField}.
    """

    def test_choices(self):
        """
        Test that noone mistakenly assigned the same number to two different
        roles.
        """
        self.assertEqual(
            len(DataRoleField.CHOICES),
            len(dict(DataRoleField.CHOICES)))


class CostCalculationTest(TestCase):
    """
    Test of L{CostCalculation} delegate class.
    """

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.unit = CostCalculation(
            customer=self.customer,
            role=DataRoleField.COST,
            unit='millicurrency_dkk',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            consumption=TestDataSeries.objects.create(
                customer=self.customer,
                role=DataRoleField.CONSUMPTION,
                unit='milliwatt*hour',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity),
            tariff=TestDataSeries.objects.create(
                customer=self.customer,
                role=DataRoleField.ELECTRICITY_TARIFF,
                unit='millicurrency_dkk*watt^-1*hour^-1',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity))
        self.unit.save()

        self.start_time = datetime(2013, 1, 1, tzinfo=pytz.utc)

    def test_index_extrapolation(self):
        self.unit._get_accumulation_samples = Mock(
            return_value=[
                self.unit.consumption.create_point_sample(
                    self.start_time,
                    PhysicalQuantity(0, self.unit.consumption.unit)),
                self.unit.consumption.create_point_sample(
                    self.start_time + timedelta(hours=1),
                    PhysicalQuantity(10, self.unit.consumption.unit)),
                self.unit.consumption.create_point_sample(
                    self.start_time + timedelta(hours=2),
                    PhysicalQuantity(0, self.unit.consumption.unit)),
            ])

        self.unit._get_rate_samples = Mock(
            return_value=[
                self.unit.tariff.create_range_sample(
                    self.start_time, self.start_time + timedelta(hours=1),
                    PhysicalQuantity(1, self.unit.tariff.unit))])

        result = list(
            self.unit.get_samples(
                self.start_time, self.start_time + timedelta(hours=2)))
        self.assertEqual(
            result,
            [
                self.unit.create_point_sample(
                    self.start_time,
                    PhysicalQuantity(0, self.unit.unit)),
                self.unit.create_point_sample(
                    self.start_time + timedelta(hours=1),
                    (
                        PhysicalQuantity(10, self.unit.consumption.unit) *
                        PhysicalQuantity(1, self.unit.tariff.unit))),
                self.unit.create_point_sample(
                    self.start_time + timedelta(hours=2),
                    (
                        PhysicalQuantity(10, self.unit.consumption.unit) *
                        PhysicalQuantity(1, self.unit.tariff.unit)),
                    uncachable=True, extrapolated=True)])

    def test_calculate_development(self):
        for i in range(11):
            self.unit.consumption.stored_data.create(
                timestamp=self.start_time + timedelta(hours=i),
                value=i)

        self.unit.tariff.stored_data.create(
            timestamp=self.start_time,
            value=7919)

        result = self.unit.calculate_development(
            self.start_time, self.start_time + timedelta(hours=10))

        expected_result = self.unit.create_range_sample(
            self.start_time,
            self.start_time + timedelta(hours=10),
            PhysicalQuantity(1, 'milliwatt*hour') * 10 *
            PhysicalQuantity(7919, 'millicurrency_dkk*watt^-1*hour^-1'),
            uncachable=True, extrapolated=False)

        self.assertEqual(result, expected_result)

    @unittest.skip('Condensed values are currently not extrapolated')
    def test_extrapolated_condensed(self):
        """
        Test cost calculation across an interval without consumption values at
        the end-point, and single tariff value covering same interval.
        """
        self.unit.consumption.stored_data.create(
            timestamp=self.start_time,
            value=2)

        self.unit.consumption.stored_data.create(
            timestamp=self.start_time + timedelta(hours=1),
            value=3)

        self.unit.tariff.stored_data.create(
            timestamp=self.start_time,
            value=7919)

        condensed_cost_samples = iter(
            self.unit.get_condensed_samples(
                self.start_time,
                RelativeTimeDelta(hours=1),
                to_timestamp=self.start_time + timedelta(hours=2)))

        sample = next(condensed_cost_samples)
        self.assertTrue(sample.is_range)
        self.assertEqual(sample.from_timestamp, self.start_time)
        self.assertEqual(
            sample.to_timestamp, self.start_time + timedelta(hours=1))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity('7.919', 'millicurrency_dkk'))

        sample = next(condensed_cost_samples)
        self.assertTrue(sample.is_range)
        self.assertEqual(sample.from_timestamp,
                         self.start_time + timedelta(hours=1))
        self.assertEqual(sample.to_timestamp,
                         self.start_time + timedelta(hours=2))
        self.assertEqual(
            sample.physical_quantity, PhysicalQuantity(0, 'millicurrency_dkk'))

        with self.assertRaises(StopIteration):
            next(condensed_cost_samples)

    def test_alternation_condensed(self):
        """
        Test condensation where raw samples alternate between the timestamps of
        both tariff and consumption.
        """
        self.unit.consumption.stored_data.create(
            timestamp=self.start_time,
            value=2)

        self.unit.consumption.stored_data.create(
            timestamp=self.start_time + timedelta(minutes=30),
            value=3)

        self.unit.consumption.stored_data.create(
            timestamp=self.start_time + timedelta(hours=1, minutes=2),
            value=5)

        self.unit.tariff.stored_data.create(
            timestamp=self.start_time - timedelta(hours=1),
            value=7919)

        self.unit.tariff.stored_data.create(
            timestamp=self.start_time + timedelta(hours=1),
            value=3019)

        condensed_cost_samples = iter(
            self.unit.get_condensed_samples(
                self.start_time,
                RelativeTimeDelta(hours=1),
                to_timestamp=self.start_time + timedelta(hours=2)))

        sample = next(condensed_cost_samples)
        self.assertTrue(sample.is_range)
        self.assertEqual(sample.from_timestamp, self.start_time)
        self.assertEqual(
            sample.to_timestamp, self.start_time + timedelta(hours=1))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity('7.919', 'millicurrency_dkk') *
            (1 + Fraction(2 * 30, 32)))

        sample = next(condensed_cost_samples)
        self.assertTrue(sample.is_range)
        self.assertEqual(
            sample.from_timestamp, self.start_time + timedelta(hours=1))
        self.assertEqual(
            sample.to_timestamp, self.start_time + timedelta(hours=2))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity('3.019', 'millicurrency_dkk') *
            2 * Fraction(2, 32))

        with self.assertRaises(StopIteration):
            next(condensed_cost_samples)

    def test_alternation_raw(self):
        """
        Test raw samples alternating between the timestamps of both tariff and
        consumption.
        """
        self.unit.consumption.stored_data.create(
            timestamp=self.start_time,
            value=2)

        self.unit.consumption.stored_data.create(
            timestamp=self.start_time + timedelta(minutes=30),
            value=3)

        self.unit.consumption.stored_data.create(
            timestamp=self.start_time + timedelta(hours=1),
            value=5)

        self.unit.tariff.stored_data.create(
            timestamp=self.start_time - timedelta(minutes=42),
            value=7919)

        self.unit.tariff.stored_data.create(
            timestamp=self.start_time + timedelta(minutes=45),
            value=3019)

        raw_cost_samples = iter(
            self.unit.get_samples(
                self.start_time,
                self.start_time + timedelta(hours=1)))

        sample = next(raw_cost_samples)
        self.assertTrue(sample.is_point)
        self.assertEqual(sample.timestamp, self.start_time)
        self.assertEqual(
            sample.physical_quantity, PhysicalQuantity(0, 'currency_dkk'))

        sample = next(raw_cost_samples)
        self.assertTrue(sample.is_point)
        self.assertEqual(sample.timestamp,
                         self.start_time + timedelta(minutes=45))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity('7.919', 'millicurrency_dkk') * 2)

        sample = next(raw_cost_samples)
        self.assertTrue(sample.is_point)
        self.assertEqual(sample.timestamp,
                         self.start_time + timedelta(hours=1))
        self.assertAlmostEqual(
            sample.physical_quantity,
            PhysicalQuantity('7.919', 'millicurrency_dkk') * 2 +
            PhysicalQuantity('3.019', 'millicurrency_dkk'))

        with self.assertRaises(StopIteration):
            next(raw_cost_samples)


class InterpolationCloudTest(TestCase):
    """
    Test the L{InterpolationCloud} class.
    """

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()

        self.from_timestamp = datetime(2013, 1, 1, tzinfo=pytz.utc)
        self.to_timestamp = datetime(2013, 1, 2, tzinfo=pytz.utc)

        self.data_series1 = TestDataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.data_series2 = TestDataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='joule',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

    def test_no_samples(self):
        """
        Test that an interpolation cloud spanning no samples, yields two empty
        sample vectors.
        """
        interpolation_cloud = InterpolationCloud(
            [self.data_series1, self.data_series2],
            self.from_timestamp,
            self.to_timestamp)

        self.assertEqual(list(interpolation_cloud), [[None, None],
                                                     [None, None]])

    def test_plenty_of_samples(self):
        """
        Test that an interpolation cloud spanning plenty of sample, yields the
        correct interpolated samples.
        """
        self.data_series1.stored_data.create(
            value=7,
            timestamp=self.from_timestamp - timedelta(hours=1))
        self.data_series1.stored_data.create(
            value=11,
            timestamp=self.from_timestamp + timedelta(hours=4))
        self.data_series1.stored_data.create(
            value=13,
            timestamp=self.from_timestamp + timedelta(hours=30))

        self.data_series2.stored_data.create(
            value=17,
            timestamp=self.from_timestamp - timedelta(hours=2))
        self.data_series2.stored_data.create(
            value=19,
            timestamp=self.from_timestamp + timedelta(hours=9))
        self.data_series2.stored_data.create(
            value=23,
            timestamp=self.from_timestamp + timedelta(hours=20))
        self.data_series2.stored_data.create(
            value=29,
            timestamp=self.from_timestamp + timedelta(hours=24))

        interpolation_cloud = InterpolationCloud(
            [self.data_series1, self.data_series2],
            self.from_timestamp,
            self.to_timestamp)

        self.assertEqual(
            list(interpolation_cloud),

            [
                [
                    self.data_series1.create_point_sample(
                        self.from_timestamp,
                        PhysicalQuantity(
                            Fraction(7 * 5 + 4, 5), 'milliwatt*hour')),
                    self.data_series2.create_point_sample(
                        self.from_timestamp,
                        PhysicalQuantity(Fraction(17 * 11 + 4, 11), 'joule'))],

                [
                    self.data_series1.create_point_sample(
                        self.from_timestamp + timedelta(hours=4),
                        PhysicalQuantity(11, 'milliwatt*hour')),
                    self.data_series2.create_point_sample(
                        self.from_timestamp + timedelta(hours=4),
                        PhysicalQuantity(
                            Fraction(17 * 11 + 12, 11), 'joule'))],

                [
                    self.data_series1.create_point_sample(
                        self.from_timestamp + timedelta(hours=9),
                        PhysicalQuantity(
                            Fraction(11 * 13 + 5, 13), 'milliwatt*hour')),
                    self.data_series2.create_point_sample(
                        self.from_timestamp + timedelta(hours=9),
                        PhysicalQuantity(19, 'joule'))],

                [
                    self.data_series1.create_point_sample(
                        self.from_timestamp + timedelta(hours=20),
                        PhysicalQuantity(
                            Fraction(11 * 13 + 16, 13), 'milliwatt*hour')),
                    self.data_series2.create_point_sample(
                        self.from_timestamp + timedelta(hours=20),
                        PhysicalQuantity(23, 'joule'))],

                [
                    self.data_series1.create_point_sample(
                        self.to_timestamp,
                        PhysicalQuantity(
                            Fraction(11 * 13 + 20, 13), 'milliwatt*hour')),
                    self.data_series2.create_point_sample(
                        self.to_timestamp,
                        PhysicalQuantity(29, 'joule'))]])

    def test_plenty_of_samples_and_no_samples(self):
        """
        Test that an interpolation cloud spanning plenty of samples of one data
        series and no samples of another, yields the correct interpolated
        samples.
        """
        self.data_series1.stored_data.create(
            value=7,
            timestamp=self.from_timestamp - timedelta(hours=1))
        self.data_series1.stored_data.create(
            value=11,
            timestamp=self.from_timestamp + timedelta(hours=4))
        self.data_series1.stored_data.create(
            value=13,
            timestamp=self.from_timestamp + timedelta(hours=30))

        interpolation_cloud = InterpolationCloud(
            [self.data_series1, self.data_series2],
            self.from_timestamp,
            self.to_timestamp)

        self.assertEqual(
            list(interpolation_cloud),

            [
                [
                    self.data_series1.create_point_sample(
                        self.from_timestamp,
                        PhysicalQuantity(
                            Fraction(7 * 5 + 4, 5), 'milliwatt*hour')),
                    None],

                [
                    self.data_series1.create_point_sample(
                        self.from_timestamp + timedelta(hours=4),
                        PhysicalQuantity(11, 'milliwatt*hour')),
                    None],

                [
                    self.data_series1.create_point_sample(
                        self.to_timestamp,
                        PhysicalQuantity(
                            Fraction(11 * 13 + 20, 13),
                            'milliwatt*hour')),
                    None]])

    def test_plenty_of_samples_and_extrapolated_samples(self):
        """
        Test that an interpolation cloud spanning plenty of samples for one
        data series and only extrapolated samples of another, yields the
        correct interpolated samples.
        """
        self.data_series1.stored_data.create(
            value=7,
            timestamp=self.from_timestamp - timedelta(hours=1))
        self.data_series1.stored_data.create(
            value=11,
            timestamp=self.from_timestamp + timedelta(hours=4))
        self.data_series1.stored_data.create(
            value=13,
            timestamp=self.from_timestamp + timedelta(hours=30))
        self.data_series2.stored_data.create(
            value=17,
            timestamp=self.from_timestamp - timedelta(hours=2))

        interpolation_cloud = InterpolationCloud(
            [self.data_series1, self.data_series2],
            self.from_timestamp,
            self.to_timestamp)

        result = list(interpolation_cloud)

        expected_result = [
            [
                self.data_series1.create_point_sample(
                    self.from_timestamp,
                    PhysicalQuantity(
                        Fraction(7 * 5 + 4, 5), 'milliwatt*hour')),
                self.data_series2.create_point_sample(
                    self.from_timestamp,
                    PhysicalQuantity(17, 'joule'),
                    uncachable=True,
                    extrapolated=True)],

            [
                self.data_series1.create_point_sample(
                    self.from_timestamp + timedelta(hours=4),
                    PhysicalQuantity(11, 'milliwatt*hour')),
                self.data_series2.create_point_sample(
                    self.from_timestamp + timedelta(hours=4),
                    PhysicalQuantity(17, 'joule'),
                    uncachable=True,
                    extrapolated=True)],

            [
                self.data_series1.create_point_sample(
                    self.to_timestamp,
                    PhysicalQuantity(
                        Fraction(11 * 13 + 20, 13), 'milliwatt*hour')),
                self.data_series2.create_point_sample(
                    self.to_timestamp,
                    PhysicalQuantity(17, 'joule'),
                    uncachable=True,
                    extrapolated=True)]]

        self.assertEqual(result, expected_result)


class SummationTest(TestCase):
    """
    Test the L{Summation} model.
    """

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()

        self.from_timestamp = datetime(2013, 1, 1, tzinfo=pytz.utc)
        self.to_timestamp = datetime(2013, 1, 2, tzinfo=pytz.utc)

        self.data_series1 = TestDataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.data_series2 = TestDataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='joule',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.summation = Summation.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='newton*foot',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            plus_data_series=[self.data_series1],
            minus_data_series=[self.data_series2])

    def test_empty_summation_get_samples(self):
        summation = Summation.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='newton*foot',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        result = list(
            summation.get_samples(
                self.from_timestamp, self.to_timestamp))

        expected_result = []

        self.assertEqual(result, expected_result)

    def test_reload(self):
        """
        Test reloading, i.e. that a Summation define the same sum before and
        after it was stored.
        """
        reloaded_summation = Summation.objects.get(id=self.summation.id)
        self.assertEqual(
            self.summation.plus_data_series,
            reloaded_summation.plus_data_series)

        self.assertEqual(
            self.summation.minus_data_series,
            reloaded_summation.minus_data_series)

    def test_no_samples(self):
        """
        Test summation across two data series without any samples at all.
        """
        result = list(
            self.summation.get_samples(
                self.from_timestamp, self.to_timestamp))

        expected_result = []

        self.assertEqual(result, expected_result)

        self.assertFalse(
            self.summation.calculate_development(
                self.from_timestamp, self.to_timestamp))

        self.assertEqual(
            list(
                self.summation.get_condensed_samples(
                    self.from_timestamp,
                    RelativeTimeDelta(hours=1),
                    to_timestamp=self.to_timestamp)),
            [])

    def test_plenty_of_samples(self):
        """
        Test summation across two data series with plenty of samples
        """
        self.data_series1.stored_data.create(
            value=7,
            timestamp=self.from_timestamp - timedelta(hours=1))
        self.data_series1.stored_data.create(
            value=11,
            timestamp=self.from_timestamp + timedelta(hours=4))
        self.data_series1.stored_data.create(
            value=13,
            timestamp=self.from_timestamp + timedelta(hours=30))

        self.data_series2.stored_data.create(
            value=17,
            timestamp=self.from_timestamp - timedelta(hours=2))
        self.data_series2.stored_data.create(
            value=19,
            timestamp=self.from_timestamp + timedelta(hours=9))
        self.data_series2.stored_data.create(
            value=23,
            timestamp=self.from_timestamp + timedelta(hours=20))
        self.data_series2.stored_data.create(
            value=29,
            timestamp=self.from_timestamp + timedelta(hours=24))

        result = list(
            self.summation.get_samples(
                self.from_timestamp, self.to_timestamp))

        expected_result = [
            self.summation.create_point_sample(
                self.from_timestamp,
                (PhysicalQuantity(7 + Fraction(11 - 7, 5), 'milliwatt*hour') -
                 PhysicalQuantity(17 + Fraction((19 - 17) * 2, 11), 'joule'))),
            self.summation.create_point_sample(
                self.from_timestamp + timedelta(hours=4),
                (PhysicalQuantity(Fraction(11), 'milliwatt*hour') -
                 PhysicalQuantity(17 + Fraction((19 - 17) * 6, 11), 'joule'))),
            self.summation.create_point_sample(
                self.from_timestamp + timedelta(hours=9),
                (PhysicalQuantity(11 + Fraction((13 - 11) * 5, 26),
                                  'milliwatt*hour') -
                 PhysicalQuantity(Fraction(19), 'joule'))),
            self.summation.create_point_sample(
                self.from_timestamp + timedelta(hours=20),
                (PhysicalQuantity(11 + Fraction((13 - 11) * 16, 26),
                                  'milliwatt*hour') -
                 PhysicalQuantity(Fraction(23), 'joule'))),
            self.summation.create_point_sample(
                self.to_timestamp,
                (PhysicalQuantity(11 + Fraction((13 - 11) * 20, 26),
                                  'milliwatt*hour') -
                 PhysicalQuantity(Fraction(29), 'joule')))]

        self.assertEqual(result, expected_result)

        self.assertEqual(
            self.summation.calculate_development(
                self.from_timestamp, self.to_timestamp),
            self.summation.create_range_sample(
                self.from_timestamp, self.to_timestamp,
                (expected_result[-1].physical_quantity -
                 expected_result[0].physical_quantity)))

        self.assertEqual(
            list(
                self.summation.get_condensed_samples(
                    self.from_timestamp,
                    RelativeTimeDelta(hours=1),
                    to_timestamp=self.to_timestamp)),
            [
                self.summation.create_range_sample(
                    self.from_timestamp + timedelta(hours=i),
                    self.from_timestamp + timedelta(hours=i + 1),
                    PhysicalQuantity(
                        Fraction(37100, 4191), self.summation.unit))
                for i in range(0, 4)
            ] +
            [
                self.summation.create_range_sample(
                    self.from_timestamp + timedelta(hours=i),
                    self.from_timestamp + timedelta(hours=i + 1),
                    PhysicalQuantity(
                        Fraction(17000, 54483), self.summation.unit))
                for i in range(4, 9)
            ] +
            [
                self.summation.create_range_sample(
                    self.from_timestamp + timedelta(hours=i),
                    self.from_timestamp + timedelta(hours=i + 1),
                    PhysicalQuantity(
                        Fraction(-15500, 54483), self.summation.unit))
                for i in range(9, 20)
            ] +
            [
                self.summation.create_range_sample(
                    self.from_timestamp + timedelta(hours=i),
                    self.from_timestamp + timedelta(hours=i + 1),
                    PhysicalQuantity(
                        Fraction(-6625, 1651), self.summation.unit))
                for i in range(20, 24)
            ])

    @unittest.skip(
        '... mismatch on cachable/extrapolated; '
        'we do not really track those anymore')
    def test_plenty_of_samples_and_no_samples(self):
        """
        Test summation across two data series; one with plenty of samples, one
        without any samples
        """
        self.data_series1.stored_data.create(
            value=7,
            timestamp=self.from_timestamp - timedelta(hours=1))
        self.data_series1.stored_data.create(
            value=11,
            timestamp=self.from_timestamp + timedelta(hours=4))
        self.data_series1.stored_data.create(
            value=13,
            timestamp=self.from_timestamp + timedelta(hours=30))

        result = list(
            self.summation.get_samples(
                self.from_timestamp, self.to_timestamp))

        expected_result = [
            self.summation.create_point_sample(
                self.from_timestamp,
                PhysicalQuantity(
                    7 + Fraction(11 - 7, 5), 'milliwatt*hour'),
                uncachable=True, extrapolated=True),
            self.summation.create_point_sample(
                self.from_timestamp + timedelta(hours=4),
                PhysicalQuantity(
                    Fraction(11), 'milliwatt*hour'),
                uncachable=True, extrapolated=True),
            self.summation.create_point_sample(
                self.to_timestamp,
                PhysicalQuantity(
                    11 + Fraction((13 - 11) * 20, 26), 'milliwatt*hour'),
                uncachable=True, extrapolated=True)]

        self.assertEqual(result, expected_result)

        self.assertEqual(
            self.summation.calculate_development(
                self.from_timestamp, self.to_timestamp),
            self.summation.create_range_sample(
                self.from_timestamp, self.to_timestamp,
                (expected_result[-1].physical_quantity -
                 expected_result[0].physical_quantity),
                uncachable=True, extrapolated=True))

        self.assertEqual(
            list(
                self.summation.get_condensed_samples(
                    self.from_timestamp,
                    RelativeTimeDelta(hours=1),
                    to_timestamp=self.to_timestamp)),
            [
                self.summation.create_range_sample(
                    self.from_timestamp + timedelta(hours=i),
                    self.from_timestamp + timedelta(hours=i + 1),
                    PhysicalQuantity(Fraction(1200, 127), self.summation.unit),
                    uncachable=True, extrapolated=True) for i in range(0, 4)] +
            [
                self.summation.create_range_sample(
                    self.from_timestamp + timedelta(hours=i),
                    self.from_timestamp + timedelta(hours=i + 1),
                    PhysicalQuantity(
                        Fraction(1500, 1651), self.summation.unit),
                    uncachable=True, extrapolated=True) for i in range(4, 24)])

    def test_plenty_of_samples_and_extrapolation(self):
        """
        Test summation across two data series; one with plenty of samples, and
        one only with samples outside the given range.
        """
        self.data_series1.stored_data.create(
            value=7,
            timestamp=self.from_timestamp - timedelta(hours=1))
        self.data_series1.stored_data.create(
            value=11,
            timestamp=self.from_timestamp + timedelta(hours=4))
        self.data_series1.stored_data.create(
            value=13,
            timestamp=self.from_timestamp + timedelta(hours=30))

        self.data_series2.stored_data.create(
            value=17,
            timestamp=self.from_timestamp - timedelta(hours=2))

        result = list(self.summation.get_samples(
                      self.from_timestamp, self.to_timestamp))

        expected_result = [
            self.summation.create_point_sample(
                self.from_timestamp,
                (PhysicalQuantity(
                    7 + Fraction(11 - 7, 5), 'milliwatt*hour') -
                 PhysicalQuantity(17, 'joule')),
                uncachable=True, extrapolated=True),
            self.summation.create_point_sample(
                self.from_timestamp + timedelta(hours=4),
                (PhysicalQuantity(
                    Fraction(11), 'milliwatt*hour') -
                 PhysicalQuantity(17, 'joule')),
                uncachable=True, extrapolated=True),
            self.summation.create_point_sample(
                self.to_timestamp,
                (PhysicalQuantity(
                    11 + Fraction((13 - 11) * 20, 26), 'milliwatt*hour') -
                 PhysicalQuantity(
                     Fraction(17), 'joule')),
                uncachable=True, extrapolated=True)]

        self.assertEqual(result, expected_result)

        self.assertEqual(
            self.summation.calculate_development(
                self.from_timestamp, self.to_timestamp),
            self.summation.create_range_sample(
                self.from_timestamp, self.to_timestamp,
                (expected_result[-1].physical_quantity -
                 expected_result[0].physical_quantity),
                uncachable=True, extrapolated=True))

        self.assertEqual(
            list(
                self.summation.get_condensed_samples(
                    self.from_timestamp,
                    RelativeTimeDelta(hours=1),
                    to_timestamp=self.to_timestamp)),
            [
                self.summation.create_range_sample(
                    self.from_timestamp + timedelta(hours=i),
                    self.from_timestamp + timedelta(hours=i + 1),
                    PhysicalQuantity(Fraction(1200, 127), self.summation.unit),
                    uncachable=True, extrapolated=True) for i in range(0, 4)] +
            [
                self.summation.create_range_sample(
                    self.from_timestamp + timedelta(hours=i),
                    self.from_timestamp + timedelta(hours=i + 1),
                    PhysicalQuantity(
                        Fraction(1500, 1651), self.summation.unit),
                    uncachable=True, extrapolated=True) for i in range(4, 24)])

    def test_data_series_dependencies(self):
        """
        Test that summation depends on data_series1 and data_series2
        """
        self.assertEqual(self.summation.depends_on(),
                         [self.data_series1, self.data_series2])


class MultiplicationTest(TestCase):
    """
    Test the L{Multiplication} model.
    """

    def setUp(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        self.unit = Multiplication.objects.create(
            customer=customer,
            role=DataRoleField.CONSUMPTION,
            unit='meter^3',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water,
            multiplier='123.456',
            source_data_series=TestDataSeries.objects.create(
                customer=customer,
                role=DataRoleField.CONSUMPTION,
                unit='liter',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water))
        self.from_timestamp = datetime(2013, 1, 1, tzinfo=pytz.utc)
        self.to_timestamp = self.from_timestamp + timedelta(days=1)

        self.unit.source_data_series.stored_data.create(
            value=5,
            timestamp=self.from_timestamp - timedelta(minutes=10))
        self.unit.source_data_series.stored_data.create(
            value=7,
            timestamp=self.from_timestamp + timedelta(minutes=20))

    def test_get_raw_data_series(self):
        """
        Test L{Multiplication.get_raw_data_series()}
        """
        self.assertEqual(
            list(
                self.unit.get_samples(self.from_timestamp, self.to_timestamp)),
            [
                self.unit.create_point_sample(
                    self.from_timestamp,
                    PhysicalQuantity(
                        (5 + Fraction(2, 3)) * Fraction('123.456') *
                        Fraction(1, 1000),
                        'meter^3')),
                self.unit.create_point_sample(
                    self.from_timestamp + timedelta(minutes=20),
                    PhysicalQuantity(
                        7 * Fraction('123.456') *
                        Fraction(1, 1000),
                        'meter^3')),
                self.unit.create_point_sample(
                    self.to_timestamp,
                    PhysicalQuantity(
                        7 * Fraction('123.456') *
                        Fraction(1, 1000),
                        'meter^3'),
                    uncachable=True,
                    extrapolated=True)])

    def test_depends_on(self):
        """
        Test L{Multiplication.depends_on()}
        """
        self.assertEqual(
            self.unit.depends_on(),
            [self.unit.source_data_series])


@override_settings(ENCRYPTION_TESTMODE=True)
class HeatingDegreeDaysTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.temperature = TestDataSeries.objects.create(
            role=DataRoleField.ABSOLUTE_TEMPERATURE,
            unit='millikelvin',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating)

        self.from_timestamp = datetime(2013, 1, 1, tzinfo=pytz.utc)
        self.to_timestamp = self.from_timestamp + timedelta(days=7)

        self.celsius_base = PhysicalQuantity('273.15', 'kelvin')

        for n in range(5):
            self.temperature.stored_data.create(
                value=(
                    (
                        self.celsius_base +
                        PhysicalQuantity(15, 'kelvin'))
                    .convert(self.temperature.unit)),
                timestamp=self.from_timestamp + timedelta(days=n) -
                timedelta(hours=1))
            self.temperature.stored_data.create(
                value=(
                    (
                        self.celsius_base +
                        PhysicalQuantity(15, 'kelvin')).
                    convert(self.temperature.unit)),
                timestamp=self.from_timestamp + timedelta(days=n) +
                timedelta(hours=1))
        self.temperature.stored_data.create(
            value=(self.celsius_base + PhysicalQuantity(15, 'kelvin')).convert(
                self.temperature.unit),
            timestamp=self.from_timestamp + timedelta(days=5))
        for n in range(6, 8):
            self.temperature.stored_data.create(
                value=(
                    (
                        self.celsius_base +
                        PhysicalQuantity(17, 'kelvin')).
                    convert(self.temperature.unit)),
                timestamp=self.from_timestamp + timedelta(days=n))

        self.heatingdegreedays = HeatingDegreeDays.objects.create(
            derived_from=self.temperature,
            role=DataRoleField.HEATING_DEGREE_DAYS,
            unit='kelvin*day',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_get_samples(self):
        val = list(
            self.heatingdegreedays.get_samples(
                self.from_timestamp - timedelta(days=1),
                self.to_timestamp + timedelta(days=1)))
        physical_quantities = map(
            operator.attrgetter('physical_quantity'), val)

        degree_day_unit = functools.partial(
            PhysicalQuantity, unit='kelvin*day')
        expected = map(degree_day_unit, [0, 0, 2, 4, 6, 8, 10, 11, 11, 11])

        self.assertListEqual(
            expected,
            physical_quantities)

    def test_calculate_development(self):
        actual = self.heatingdegreedays.calculate_development(
            self.from_timestamp, self.to_timestamp)
        expected = self.heatingdegreedays.create_range_sample(
            self.from_timestamp, self.to_timestamp,
            PhysicalQuantity(11, 'kelvin*day'))

        self.assertEqual(expected, actual)


@override_settings(ENCRYPTION_TESTMODE=True)
class DegreeDayCorrectionTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.consumption = TestDataSeries.objects.create(
            role=DataRoleField.CONSUMPTION,
            unit='watt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.degreedays = TestDataSeries.objects.create(
            role=DataRoleField.HEATING_DEGREE_DAYS,
            unit='kelvin*day',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating)

        self.standarddegreedays = TestDataSeries.objects.create(
            role=DataRoleField.STANDARD_HEATING_DEGREE_DAYS,
            unit='kelvin*day',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating)

        self.degreedaycorrection = DegreeDayCorrection.objects.create(
            consumption=self.consumption,
            degreedays=self.degreedays,
            standarddegreedays=self.standarddegreedays,
            role=DataRoleField.CONSUMPTION,
            unit='watt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.from_timestamp = datetime(2013, 1, 1, tzinfo=pytz.utc)
        self.to_timestamp = datetime(2013, 2, 1, tzinfo=pytz.utc)

        self.days = list(itertools.takewhile(
            lambda t: t <= self.to_timestamp,
            count_extended(self.from_timestamp, timedelta(days=1))))

        for n, day in itertools.izip(itertools.count(), self.days):
            self.consumption.stored_data.create(
                value=1000 * n,
                timestamp=day)
            self.standarddegreedays.stored_data.create(
                value=1 * n,
                timestamp=day)
            self.degreedays.stored_data.create(
                value=2 * n,
                timestamp=day)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_get_samples(self):
        with self.assertRaises(NotImplementedError):
            list(
                self.degreedaycorrection.get_samples(
                    self.from_timestamp, self.to_timestamp))

    def test_calculate_development(self):
        actual = self.degreedaycorrection.calculate_development(
            self.from_timestamp, self.to_timestamp)
        expected = self.degreedaycorrection.create_range_sample(
            self.from_timestamp, self.to_timestamp,
            PhysicalQuantity(31000 / 2, 'watt*hour'))
        self.assertEqual(actual, expected)

    def test_get_condensed(self):
        actual = list(self.degreedaycorrection.get_condensed_samples(
            from_timestamp=self.from_timestamp, to_timestamp=self.to_timestamp,
            sample_resolution=RelativeTimeDelta(days=1)))
        expected = [
            self.degreedaycorrection.create_range_sample(
                start, end, PhysicalQuantity(1000 / 2, 'watt*hour'))
            for start, end in pairwise(self.days)]
        self.assertListEqual(actual, expected)


class UtilizationTest(TestCase, ENPIMixinTestSpecification):
    """
    Test the L{Utilization} data series model.
    """
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.consumption = DataSeriesMock.objects.create(
            role=DataRoleField.CONSUMPTION,
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating,
            unit='milliwatt*hour')
        self.needs = DataSeriesMock.objects.create(
            role=DataRoleField.EMPLOYEES,
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            unit='person')
        self.utilization = Utilization.objects.create(
            role=DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
            consumption=self.consumption,
            needs=self.needs,
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating,
            unit='milliwatt*hour*person^-1*hour^-1')

        self.consumption.domain = (
            datetime(2013, 1, 1, tzinfo=pytz.utc),
            datetime(2013, 1, 3, tzinfo=pytz.utc))

        self.consumption.raw_data_samples = [
            self.consumption.create_point_sample(
                datetime(2013, 1, 1, tzinfo=pytz.utc),
                PhysicalQuantity(5, self.consumption.unit)),
            self.consumption.create_point_sample(
                datetime(2013, 1, 2, tzinfo=pytz.utc),
                PhysicalQuantity(7, self.consumption.unit)),
            self.consumption.create_point_sample(
                datetime(2013, 1, 3, tzinfo=pytz.utc),
                PhysicalQuantity(11, self.consumption.unit)),
            self.consumption.create_point_sample(
                datetime(2013, 1, 4, tzinfo=pytz.utc),
                PhysicalQuantity(11, self.consumption.unit),
                uncachable=True,
                extrapolated=True)]

        self.needs.domain = (
            datetime(2013, 1, 2, tzinfo=pytz.utc),
            datetime(2013, 1, 4, tzinfo=pytz.utc))

        self.needs.raw_data_samples = [
            self.needs.create_range_sample(
                datetime(2013, 1, 2, tzinfo=pytz.utc),
                datetime(2013, 1, 3, tzinfo=pytz.utc),
                PhysicalQuantity(5, self.needs.unit)),
            self.needs.create_range_sample(
                datetime(2013, 1, 3, tzinfo=pytz.utc),
                datetime(2013, 1, 4, tzinfo=pytz.utc),
                PhysicalQuantity(5, self.needs.unit)),
        ]

    def test_depends_on(self):
        consumption = TestDataSeries.objects.create(
            unit='kilowatt*hour',
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            role=DataRoleField.CONSUMPTION)
        needs = TestDataSeries.objects.create(
            unit='person',
            customer=self.customer,
            role=DataRoleField.EMPLOYEES,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        utilization = Utilization.objects.create(
            consumption=consumption,
            needs=needs,
            unit='kilowatt*person^-1',
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            role=DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES)
        self.assertIn(consumption, utilization.depends_on())
        self.assertIn(needs, utilization.depends_on())
        self.assertIn(self.consumption, self.utilization.depends_on())
        self.assertIn(self.needs, self.utilization.depends_on())

    def test_get_samples(self):
        with self.assertRaises(UndefinedSamples):
            list(
                self.utilization.get_samples(
                    datetime(2013, 1, 1, tzinfo=pytz.utc),
                    datetime(2013, 1, 4, tzinfo=pytz.utc)))

    def test_get_condensed_samples(self):
        self.assertEqual(
            list(
                self.utilization.get_condensed_samples(
                    datetime(2013, 1, 1, tzinfo=pytz.utc),
                    condense.DAYS,
                    datetime(2013, 1, 4, tzinfo=pytz.utc))),
            [
                self.utilization.create_range_sample(
                    datetime(2013, 1, 1, tzinfo=pytz.utc),
                    datetime(2013, 1, 2, tzinfo=pytz.utc),
                    PhysicalQuantity(6, self.consumption.unit) / (
                        PhysicalQuantity(5, self.needs.unit) *
                        PhysicalQuantity(1, 'day')),
                    uncachable=False,
                    extrapolated=False),
                self.utilization.create_range_sample(
                    datetime(2013, 1, 2, tzinfo=pytz.utc),
                    datetime(2013, 1, 3, tzinfo=pytz.utc),
                    PhysicalQuantity(6, self.consumption.unit) / (
                        PhysicalQuantity(5, self.needs.unit) *
                        PhysicalQuantity(1, 'day')),
                    uncachable=False,
                    extrapolated=False),
                self.utilization.create_range_sample(
                    datetime(2013, 1, 3, tzinfo=pytz.utc),
                    datetime(2013, 1, 4, tzinfo=pytz.utc),
                    PhysicalQuantity(0, self.consumption.unit) / (
                        PhysicalQuantity(5, self.needs.unit) *
                        PhysicalQuantity(1, 'day')),
                    uncachable=True,
                    extrapolated=True),
            ]
        )

    def test_get_underlying_function(self):
        self.assertEqual(
            self.utilization.get_underlying_function(),
            DataSeries.INTERVAL_FUNCTION)

    def test_calculate_development(self):
        with self.assertRaises(AssertionError):
            self.utilization.calculate_development(
                datetime(2013, 1, 1, tzinfo=pytz.utc),
                datetime(2013, 1, 2, tzinfo=pytz.utc))

    def test_delete(self):
        self.consumption.delete()

    def test_calculate_enpi(self):
        self.assertEqual(
            self.utilization.calculate_enpi(
                datetime(2013, 1, 1, tzinfo=pytz.utc),
                datetime(2013, 1, 4, tzinfo=pytz.utc)),
            self.utilization.create_range_sample(
                datetime(2013, 1, 1, tzinfo=pytz.utc),
                datetime(2013, 1, 4, tzinfo=pytz.utc),
                physical_quantity=(
                    PhysicalQuantity(6, self.consumption.unit) / (
                        PhysicalQuantity(5, self.needs.unit) *
                        PhysicalQuantity(2, 'day'))),
                uncachable=True,
                extrapolated=True))


class VariablyBoundAccumulation(VariablyBoundAccumulationMixin,
                                TestDataSeries):
    pass


class VariablyBoundAccumulationMixinTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()

        self.unit = VariablyBoundAccumulation(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='watt',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
        )
        self.unit.save()
        self.start_time = datetime(2013, 1, 1, 2, 3, 4, tzinfo=pytz.utc)

    def test_calculate_development(self):
        for i in range(121):
            self.unit.stored_data.create(
                timestamp=self.start_time + timedelta(minutes=i),
                value=i)
        result = self.unit.calculate_development(
            self.start_time,
            self.start_time + timedelta(minutes=120))
        result_x = self.unit.calculate_development(
            self.start_time,
            self.start_time + timedelta(minutes=120))

        expected = self.unit.create_range_sample(
            self.start_time,
            self.start_time + timedelta(minutes=120),
            PhysicalQuantity(120, 'watt'))
        self.assertEqual(expected, result)
        self.assertEqual(result, result_x)


class CacheOptimizedCalculateDevelopment(
        CacheOptimizedCalculateDevelopmentMixin, TestDataSeries):
    pass


class CacheOptimizedCalculateDevelopmentMixinTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()

        self.unit = CacheOptimizedCalculateDevelopment(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='watt',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
        )
        self.unit.save()
        self.start_time = datetime(2013, 1, 1, 2, 3, 4, tzinfo=pytz.utc)

    def test_calculate_development(self):
        for i in range(121):
            self.unit.stored_data.create(
                timestamp=self.start_time + timedelta(minutes=i),
                value=i)
        result = self.unit.calculate_development(
            self.start_time,
            self.start_time + timedelta(minutes=120))
        result_x = self.unit.calculate_development(
            self.start_time,
            self.start_time + timedelta(minutes=120))

        expected = self.unit.create_range_sample(
            self.start_time,
            self.start_time + timedelta(minutes=120),
            PhysicalQuantity(120, 'watt'))
        self.assertEqual(expected, result)
        self.assertEqual(result, result_x)


class RateConversionTest(TestCase):
    """
    Test the L{RateConversion} model.
    """
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)
        assert self.customer is trackuser.get_customer()

    def tearDown(self):
        trackuser._set_customer(None)

    def test_aggregated_samples_one_measurement_no_crash(self):
        """
        When creating a new measurement point with a gauge widget, chances were
        that we would have an assertion error in
        L{DataSeries.aggregated_samples}, once only a single measurement would
        be available.

        The details involve the domain of a rate conversion being inherited
        directly from its consumption data series.  This is not entirely
        true. No rate can be defined at points that are not accumulation points
        in the consumption domain.
        """
        derived_rate = RateConversion.objects.create(
            role=DataRoleField.POWER,
            unit="milliwatt",
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            consumption=TestDataSeries.objects.create(
                role=DataRoleField.CONSUMPTION,
                unit="milliwatt*hour",
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity))

        derived_rate.consumption.stored_data.create(
            value=0, timestamp=datetime(2013, 1, 1, 0, 3, tzinfo=pytz.utc))

        list(derived_rate.aggregated_samples(
            datetime(2013, 1, 1, 0, 0, tzinfo=pytz.utc),
            datetime(2013, 1, 1, 0, 15, tzinfo=pytz.utc)))


class AbstractGraphTest(TestCase):
    """
    Unit tests for the L{AbstractGraph} class.
    """
    def test_get_graph_data(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        data_series = TestDataSeries.objects.create(
            customer=customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        graph = AbstractGraph()

        with patch.object(AbstractGraph,
                          '_get_data_series',
                          return_value=[data_series]):
            graph.get_graph_data(
                12, datetime(2013, 1, 1, tzinfo=pytz.utc),
                num_samples=12,
                sample_resolution=RelativeTimeDelta(months=1),
                to_timestamp=datetime(2014, 1, 1, tzinfo=pytz.utc))


class SimpleLinearRegressionTest(DataSeriesTestSpecification, TestCase):
    def setUp(self):
        super(SimpleLinearRegressionTest, self).setUp()
        Provider.objects.create()
        self.customer = Customer(timezone=pytz.utc)
        self.customer.save()
        self.start_time = self.customer.timezone.localize(datetime(2013, 1, 1))
        self.end_time = self.customer.timezone.localize(datetime(2013, 1, 2))
        self.consumption = TestDataSeries.objects.create(
            role=DataRoleField.CONSUMPTION,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            unit='milliwatt*hour',
            customer=self.customer)

        # create stored data s.t. all hours have a consumption of 1 kWh
        self.consumption.stored_data.create(
            timestamp=self.start_time, value=0)
        self.consumption.stored_data.create(
            timestamp=self.end_time, value=24000000)

        self.simple_linear_regression = SimpleLinearRegression(
            data=self.consumption)
        self.simple_linear_regression.full_clean()
        self.simple_linear_regression.save()

    def test_calculate_development(self):
        with self.assertRaises(AssertionError):
            self.simple_linear_regression.calculate_development(
                self.start_time,
                self.end_time)

    def test_depends_on(self):
        with patch.object(self.consumption, 'depends_on',
                          return_value=[]) as mock:
            self.assertIn(
                self.consumption, self.simple_linear_regression.depends_on())

        mock.assertCalledWith()

    def test_get_samples(self):
        with self.assertRaises(UndefinedSamples):
            list(
                self.simple_linear_regression.get_samples(
                    self.start_time,
                    self.end_time))

    def test_get_underlying_function(self):
        self.assertEqual(
            self.simple_linear_regression.get_underlying_function(),
            DataSeries.CONTINUOUS_RATE)

    def test_get_condensed_samples(self):
        samples = list(
            self.simple_linear_regression.get_condensed_samples(
                self.start_time,
                condense.HOURS,
                self.end_time))

        self.assertEqual(
            samples[0],
            self.simple_linear_regression.create_point_sample(
                self.start_time,
                PhysicalQuantity(1, 'kilowatt*hour'),
                uncachable=True))

        self.assertEqual(
            samples[-1],
            self.simple_linear_regression.create_point_sample(
                self.end_time,
                PhysicalQuantity(1, 'kilowatt*hour'),
                uncachable=True))


class PiecewiseConstantIntegralTest(DataSeriesTestSpecification, TestCase):
    def setUp(self):
        super(PiecewiseConstantIntegralTest, self).setUp()
        Provider.objects.create()
        self.customer = Customer(timezone=pytz.utc)
        self.customer.save()
        self.start_time = self.customer.timezone.localize(datetime(2013, 1, 1))
        self.end_time = self.customer.timezone.localize(datetime(2013, 1, 2))

        self.piecewise_constant_rate = TestDataSeries.objects.create(
            role=DataRoleField.EMPLOYEES,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            unit='person',
            customer=self.customer)

        # 1 at work in the timespan 0:00 - 12:00
        self.piecewise_constant_rate.stored_data.create(
            timestamp=self.start_time, value=1)

        # 2 at work in the timespan 12:00 -
        self.piecewise_constant_rate.stored_data.create(
            timestamp=self.start_time + timedelta(hours=12), value=2)

        self.integral = PiecewiseConstantIntegral.objects.create(
            role=DataRoleField.ENERGY_DRIVER,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            unit='person*hour',
            customer=self.customer,
            data=self.piecewise_constant_rate)

    def test_calculate_development(self):
        self.assertEqual(
            self.integral.create_range_sample(
                self.start_time, self.end_time,
                physical_quantity=PhysicalQuantity(
                    12 * 1 + 12 * 2, 'person*hour')),
            self.integral.calculate_development(
                self.start_time, self.end_time))

    def test_calculate_development_fallback(self):
        self.assertEqual(
            self.integral.create_range_sample(
                self.start_time, self.end_time,
                physical_quantity=PhysicalQuantity(
                    12 * 1 + 12 * 2, 'person*hour')),
            self.integral._calculate_development_fallback(
                self.start_time, self.end_time))

    def test_depends_on(self):
        with patch.object(self.piecewise_constant_rate, 'depends_on',
                          return_value=[]) as mock:
            self.assertIn(
                self.piecewise_constant_rate,
                self.integral.depends_on())

        mock.assertCalledWith()

    def test_get_samples(self):
        with self.assertRaises(UndefinedSamples):
            list(self.integral.get_samples(self.start_time, self.end_time))

    def test_get_condensed_samples(self):
        condensed_samples = iter(
            self.integral.get_condensed_samples(
                self.start_time - timedelta(hours=1),
                condense.HOURS, self.end_time))

        self.assertEqual(
            self.integral.create_range_sample(
                self.start_time - timedelta(hours=1),
                self.start_time,
                physical_quantity=PhysicalQuantity(0, 'person*hour'),
                uncachable=True,
                extrapolated=True),
            next(condensed_samples))

        for i in range(0, 12):
            self.assertEqual(
                self.integral.create_range_sample(
                    self.start_time + timedelta(hours=i),
                    self.start_time + timedelta(hours=i + 1),
                    physical_quantity=PhysicalQuantity(1, 'person*hour')),
                next(condensed_samples))

        for i in range(12, 24):
            self.assertEqual(
                self.integral.create_range_sample(
                    self.start_time + timedelta(hours=i),
                    self.start_time + timedelta(hours=i + 1),
                    physical_quantity=PhysicalQuantity(2, 'person*hour')),
                next(condensed_samples))

        with self.assertRaises(StopIteration):
            next(condensed_samples)

    def test_get_underlying_function(self):
        self.assertEqual(
            self.integral.get_underlying_function(),
            DataSeries.CONTINUOUS_ACCUMULATION)


@override_settings(
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    CELERY_ALWAYS_EAGER=True,
    BROKER_BACKEND='memory',
    ENCRYPTION_TESTMODE=True)
class GetCondensedSamplesTaskTest(TestCase):
    def test_get_condensed_samples_task(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        user = User.objects.create_user(
            'username', 'password', user_type=User.CUSTOMER_USER,
            customer=customer)
        data_series = TestDataSeries.objects.create(
            customer=customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        START_TIME = datetime(2014, 1, 1, tzinfo=pytz.utc)
        END_TIME = datetime(2014, 1, 1, 2, tzinfo=pytz.utc)

        data_series.stored_data.create(value=0, timestamp=START_TIME)

        data_series.stored_data.create(value=2, timestamp=END_TIME)

        with replace_customer(customer), replace_user(user):
            task_status = get_condensed_samples_task.delay(
                data_series.id, START_TIME, END_TIME, condense.HOURS)
        self.assertTrue(task_status.successful())

        self.assertEqual(
            task_status.result[0],
            data_series.create_range_sample(
                START_TIME, START_TIME + condense.HOURS,
                PhysicalQuantity(1, 'milliwatt*hour')))

        self.assertEqual(
            task_status.result[1],
            data_series.create_range_sample(
                START_TIME + condense.HOURS, END_TIME,
                PhysicalQuantity(1, 'milliwatt*hour')))

        self.assertEqual(len(task_status.result), 2)


@override_settings(
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    CELERY_ALWAYS_EAGER=True,
    BROKER_BACKEND='memory',
    ENCRYPTION_TESTMODE=True)
class GetSamplesTaskTest(TestCase):
    def test_get_samples_task(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        user = User.objects.create_user(
            'username', 'password', user_type=User.CUSTOMER_USER,
            customer=customer)
        data_series = TestDataSeries.objects.create(
            customer=customer,
            role=DataRoleField.POWER,
            unit='milliwatt',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        START_TIME = datetime(2014, 1, 1, tzinfo=pytz.utc)
        END_TIME = datetime(2014, 1, 1, 2, tzinfo=pytz.utc)

        data_series.stored_data.create(value=0, timestamp=START_TIME)

        data_series.stored_data.create(value=2, timestamp=END_TIME)

        with replace_customer(customer), replace_user(user):
            task_status = get_samples_task.delay(
                data_series.id, START_TIME, END_TIME)
        self.assertTrue(task_status.successful())

        self.assertEqual(
            task_status.result[0],
            data_series.create_point_sample(
                START_TIME, PhysicalQuantity(0, 'milliwatt')))

        self.assertEqual(
            task_status.result[1],
            data_series.create_point_sample(
                END_TIME,
                PhysicalQuantity(2, 'milliwatt')))

        self.assertEqual(len(task_status.result), 2)


class IndexCalculationAutoUnitForm(forms.ModelForm):
    class Meta:
        model = IndexCalculation
        fields = ['role', 'utility_type', 'consumption', 'customer', 'index']


class IndexCalculationForm(forms.ModelForm):
    class Meta:
        model = IndexCalculation
        fields = ['role', 'utility_type', 'consumption', 'customer', 'index',
                  'unit']


@override_settings(ENCRYPTION_TESTMODE=True)
class IndexCalculationTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()

        self.tariff = DataSeries.objects.create(
            role=DataRoleField.ELECTRICITY_TARIFF,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            customer=self.customer)
        self.consumption = DataSeries.objects.create(
            role=DataRoleField.CONSUMPTION,
            unit='kilowatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            customer=self.customer)

    def test_no_auto_unit(self):
        form = IndexCalculationForm(
            data={
                'role': DataRoleField.COST,
                'utility_type': utilitytypes.METER_CHOICES.electricity,
                'index': self.tariff.id,
                'consumption': self.consumption.id,
                'customer': self.customer.id,
            })

        self.assertTrue(form.is_valid())

        index_calculation = form.save(commit=False)

        self.assertFalse(index_calculation.unit)

    def test_auto_unit(self):
        form = IndexCalculationAutoUnitForm(
            data={
                'role': DataRoleField.COST,
                'utility_type': utilitytypes.METER_CHOICES.electricity,
                'index': self.tariff.id,
                'consumption': self.consumption.id,
                'customer': self.customer.id,
            })

        self.assertTrue(form.is_valid())

        index_calculation = form.save(commit=False)

        self.assertTrue(
            PhysicalQuantity.compatible_units(
                index_calculation.unit,
                'currency_dkk'),
            '"%s" incompatible with "%s"' % (
                index_calculation.unit, 'currency_dkk'))


class Co2CalculationTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.unit = Co2Calculation(
            customer=self.customer,
            role=DataRoleField.CO2,
            unit='tonne',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            consumption=TestDataSeries.objects.create(
                customer=self.customer,
                role=DataRoleField.CONSUMPTION,
                unit='milliwatt*hour',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity),
            index=TestDataSeries.objects.create(
                customer=self.customer,
                role=DataRoleField.CO2_QUOTIENT,
                unit='gram*kilowatt^-1*hour^-1',
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity))
        self.unit.save()

        self.start_time = datetime(2013, 1, 1, tzinfo=pytz.utc)

    def test_calculate_development(self):
        for i in range(13):
            self.unit.consumption.stored_data.create(
                timestamp=self.start_time + timedelta(minutes=i*5),
                value=i)

        self.unit.index.stored_data.create(
            timestamp=self.start_time,
            value=7919)
        self.unit.index.stored_data.create(
            timestamp=self.start_time + timedelta(minutes=30),
            value=1292)

        result = self.unit.calculate_development(
            self.start_time, self.start_time + timedelta(hours=1))

        expected_result = self.unit.create_range_sample(
            self.start_time,
            self.start_time + timedelta(hours=1),
            PhysicalQuantity(1, 'milliwatt*hour') * 6 *
            PhysicalQuantity(7919, 'gram*kilowatt^-1*hour^-1') +
            PhysicalQuantity(1, 'milliwatt*hour') * 6 *
            PhysicalQuantity(1292, 'gram*kilowatt^-1*hour^-1'),
            uncachable=True, extrapolated=False)

        self.assertEqual(result, expected_result)


@override_settings(ENCRYPTION_TESTMODE=True)
class TestConsumptionMeasurementPointDegreeDays(TestCase):
    """
    Test the heating degree day corrected consumption aspect of the
    L{ConsumptionMeasurementPoint} proxy model.  In particular the
    C{standard_heating_degree_days} and C{heating_degree_days} properties
    behaviour upon validation, saving and loading are tested.
    """

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.agent = Agent.objects.create(
            mac="AB:CD:DE:F0:12:34",
            customer=self.customer)
        self.meter = Meter.objects.create(
            agent=self.agent,
            manufactoring_id="1234567891234",
            connection_type=Meter.GRIDPOINT,
            manual_mode=False,
            relay_on=False,
            online=True,
            name_plain="test meter",
            customer=self.customer)

        self.physicalinput = PhysicalInput.objects.create(
            unit='millikelvin',
            type=PhysicalInput.DISTRICT_HEATING,
            meter=self.meter,
            order=0,
            name_plain="Energy consumption (#0)")

        self.mp = ConsumptionMeasurementPoint(
            name_plain='test heating degree days',
            customer=self.customer,
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.mp.consumption = DataSeries.objects.create(
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.assertIsNone(self.mp.standard_heating_degree_days)
        self.assertIsNone(self.mp.heating_degree_days)
        self.assertFalse(
            self.mp.graph_set.filter(
                role=DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION).
            exists())

    def tearDown(self):
        trackuser._set_customer(None)

    def test_neither_set(self):
        self.mp.clean()
        self.mp.save()
        loaded_mp = ConsumptionMeasurementPoint.objects.get(id=self.mp.id)
        self.assertIsNone(loaded_mp.standard_heating_degree_days)
        self.assertIsNone(loaded_mp.heating_degree_days)
        self.assertFalse(
            loaded_mp.graph_set.filter(
                role=DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION).
            exists())

    def test_both_set(self):
        self.mp.standard_heating_degree_days = DataSeries.objects.create(
            role=DataRoleField.STANDARD_HEATING_DEGREE_DAYS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            unit='kelvin*day',
            customer=self.customer)
        self.mp.heating_degree_days = DataSeries.objects.create(
            role=DataRoleField.HEATING_DEGREE_DAYS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            unit='kelvin*day',
            customer=self.customer)
        self.mp.clean()
        self.mp.save()
        loaded_mp = ConsumptionMeasurementPoint.objects.get(id=self.mp.id)
        self.assertEqual(loaded_mp.standard_heating_degree_days,
                         self.mp.standard_heating_degree_days)
        self.assertEqual(loaded_mp.heating_degree_days,
                         self.mp.heating_degree_days)
        self.assertTrue(
            loaded_mp.graph_set.filter(
                role=DataRoleField.
                HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION).exists())

        # Check deletion
        loaded_mp.standard_heating_degree_days = None
        loaded_mp.heating_degree_days = None
        loaded_mp.clean()
        loaded_mp.save()
        loaded_mp.save()
        # double save when deleting corrected consumption has
        # previously not worked, and sw we test it here.
        loaded_mp = ConsumptionMeasurementPoint.objects.get(id=self.mp.id)
        self.assertIsNone(loaded_mp.standard_heating_degree_days)
        self.assertIsNone(loaded_mp.heating_degree_days)
        self.assertFalse(
            loaded_mp.graph_set.filter(
                role=DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION).
            exists())

    def test_standard_heating_degree_days_set(self):
        self.mp.standard_heating_degree_days = DataSeries.objects.create(
            role=DataRoleField.STANDARD_HEATING_DEGREE_DAYS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            unit='kelvin*day',
            customer=self.customer)
        self.assertIsNotNone(self.mp.standard_heating_degree_days)
        self.assertIsNone(self.mp.heating_degree_days)
        with self.assertRaises(ValidationError):
            self.mp.clean()

    def test_heating_degree_days_set(self):
        self.mp.heating_degree_days = DataSeries.objects.create(
            role=DataRoleField.HEATING_DEGREE_DAYS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            unit='kelvin*day',
            customer=self.customer)
        self.assertIsNone(self.mp.standard_heating_degree_days)
        self.assertIsNotNone(self.mp.heating_degree_days)
        with self.assertRaises(ValidationError):
            self.mp.clean()


@override_settings(ENCRYPTION_TESTMODE=True)
class TestConsumptionMeasurementPointSummation(TestCase):
    """
    Test the L{ConsumptionMeasurementPointSummation} proxy class.
    """

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.mp_electricity1 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain='Electricity 1',
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.mp_electricity1.consumption = DataSeries.objects.create(
            customer=self.customer,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            role=DataRoleField.CONSUMPTION)
        self.mp_electricity1.save()

        self.mp_electricity2 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain='Electricity 2',
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.mp_electricity2.consumption = DataSeries.objects.create(
            customer=self.customer,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            role=DataRoleField.CONSUMPTION)
        self.mp_electricity2.save()

        self.mp_water1 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain='Water 1',
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water)
        self.mp_water1.consumption = DataSeries.objects.create(
            customer=self.customer,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water,
            role=DataRoleField.CONSUMPTION)
        self.mp_water1.save()

        self.unit = ConsumptionMeasurementPointSummation(
            name_plain='Electricity sum',
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_instantiation(self):
        self.unit.plus_consumption_measurement_points = [self.mp_electricity1]
        self.assertIn(
            self.mp_electricity1,
            self.unit.plus_consumption_measurement_points)
        self.assertNotIn(
            self.mp_electricity1,
            self.unit.minus_consumption_measurement_points)

        self.unit.minus_consumption_measurement_points = [self.mp_electricity2]
        self.assertIn(
            self.mp_electricity2,
            self.unit.minus_consumption_measurement_points)
        self.assertNotIn(
            self.mp_electricity2,
            self.unit.plus_consumption_measurement_points)

        self.assertNotIn(
            self.mp_water1,
            self.unit.plus_consumption_measurement_points)
        self.assertNotIn(
            self.mp_water1,
            self.unit.minus_consumption_measurement_points)

    def test_reinstantiation(self):
        self.test_instantiation()
        self.unit.save()
        self.reinstantiation = ConsumptionMeasurementPointSummation.\
            objects.get(id=self.unit.id)

        self.assertIn(
            self.mp_electricity1,
            self.reinstantiation.plus_consumption_measurement_points)
        self.assertNotIn(
            self.mp_electricity1,
            self.reinstantiation.minus_consumption_measurement_points)

        self.assertIn(
            self.mp_electricity2,
            self.reinstantiation.minus_consumption_measurement_points)
        self.assertNotIn(
            self.mp_electricity2,
            self.reinstantiation.plus_consumption_measurement_points)

        self.assertNotIn(
            self.mp_water1,
            self.reinstantiation.plus_consumption_measurement_points)
        self.assertNotIn(
            self.mp_water1,
            self.reinstantiation.minus_consumption_measurement_points)

    def test_dependencies(self):
        self.unit.plus_consumption_measurement_points = [self.mp_electricity1]
        self.unit.minus_consumption_measurement_points = [self.mp_electricity2]
        self.unit.save()

        self.assertEqual(
            any([self.mp_electricity1.is_deletable(),
                 self.mp_electricity2.is_deletable()]),
            False)

    def test_dependencies_by_db_level(self):
        self.unit.plus_consumption_measurement_points = [self.mp_electricity1]
        self.unit.minus_consumption_measurement_points = [self.mp_electricity2]
        self.unit.save()

        self.assertRaises(
            ProtectedError, lambda: self.mp_electricity1.delete())
        self.assertRaises(
            ProtectedError, lambda: self.mp_electricity2.delete())


class ImportedMeasurementPointTest(TestCase):
    def test_clean_success(self):
        mp = ImportedMeasurementPoint()

        csv = 'kWh - Time;571313115400167430;571313115400167454\n'\
            ';;\n'\
            '01-08-2010 00:00 - 01-08-2010 01:00;0,475;1,825\n'\
            '01-08-2010 01:00 - 01-08-2010 02:00;0,125;1,8\n'

        mp.timezone = pytz.utc
        mp.consumption_column = 1
        mp.upload_file = SimpleUploadedFile('test.csv', str(csv))
        mp.unit = 'kilowatt*hour'

        mp.clean()

        self.assertEqual(
            mp.parsed_csv,
            [(datetime(2010, 8, 1, 0, 0, tzinfo=pytz.utc),
              datetime(2010, 8, 1, 1, 0, tzinfo=pytz.utc),
              Fraction('0.475')),
             (datetime(2010, 8, 1, 1, 0, tzinfo=pytz.utc),
              datetime(2010, 8, 1, 2, 0, tzinfo=pytz.utc),
              Fraction('0.125'))])

    def test_clean_skip_an_empty_line_success(self):
        mp = ImportedMeasurementPoint()

        csv = 'kWh - Time;571313115400167430;571313115400167454\n'\
            ';;\n'\
            '01-08-2010 00:00 - 01-08-2010 01:00;0,475;1,825\n\n'\
            '01-08-2010 01:00 - 01-08-2010 02:00;0,125;1,8\n'

        mp.timezone = pytz.utc
        mp.consumption_column = 1
        mp.upload_file = SimpleUploadedFile('test.csv', str(csv))
        mp.unit = 'kilowatt*hour'

        mp.clean()

        self.assertEqual(
            mp.parsed_csv,
            [(datetime(2010, 8, 1, 0, 0, tzinfo=pytz.utc),
              datetime(2010, 8, 1, 1, 0, tzinfo=pytz.utc),
              Fraction('0.475')),
             (datetime(2010, 8, 1, 1, 0, tzinfo=pytz.utc),
              datetime(2010, 8, 1, 2, 0, tzinfo=pytz.utc),
              Fraction('0.125'))])

    def test_clean_decoding_success(self):
        mp = ImportedMeasurementPoint()

        csv = 'kWh - Time;571313115400167430;571313115400167454; '\
            u'Åbenbar unicode-ødelæggende kommentar\n'\
            ';;\n'\
            '01-08-2010 00:00 - 01-08-2010 01:00;0,475;1,825\n\n'\
            '01-08-2010 01:00 - 01-08-2010 02:00;0,125;1,8\n'

        mp.timezone = pytz.utc
        mp.consumption_column = 1
        mp.upload_file = SimpleUploadedFile('test.csv', csv.encode('iso8859'))
        mp.unit = 'kilowatt*hour'

        mp.clean()

        self.assertEqual(
            mp.parsed_csv,
            [(datetime(2010, 8, 1, 0, 0, tzinfo=pytz.utc),
              datetime(2010, 8, 1, 1, 0, tzinfo=pytz.utc),
              Fraction('0.475')),
             (datetime(2010, 8, 1, 1, 0, tzinfo=pytz.utc),
              datetime(2010, 8, 1, 2, 0, tzinfo=pytz.utc),
              Fraction('0.125'))])

    def test_clean_consumption_column_does_not_exist(self):
        mp = ImportedMeasurementPoint()

        csv = 'kWh - Time;571313115400167430;571313115400167454\n'\
            ';;\n'\
            '01-08-2010 00:00 - 01-08-2010 01:00;0,475;1,825\n'\
            '01-08-2010 01:00 - 01-08-2010 02:00;0,125;1,8\n'
        mp.timezone = pytz.utc
        mp.consumption_column = 42
        mp.upload_file = SimpleUploadedFile('test.csv', str(csv))
        mp.unit = 'kilowatt*hour'

        with self.assertRaises(ImportedMeasurementPoint.
                               ConsumptionColumnDoesNotExist) as cm:
            mp.clean()

        self.assertEqual(cm.exception.filename, 'test.csv')
        self.assertEqual(cm.exception.lineno, 2)

    def test_clean_consumption_parse_error(self):
        mp = ImportedMeasurementPoint()

        csv = 'kWh - Time;571313115400167430;571313115400167454\n'\
            ';;\n'\
            '01-08-2010 00:00 - 01-08-2010 01:00;0,475;1,825\n'\
            '01-08-2010 01:00 - 01-08-2010 02:00;pi;1,8\n'

        mp.consumption_column = 1
        mp.upload_file = SimpleUploadedFile('test.csv', str(csv))
        mp.timezone = pytz.utc
        mp.unit = 'kilowatt*hour'
        with self.assertRaises(ImportedMeasurementPoint.
                               ConsumptionParseError) as cm:
            mp.clean()

        self.assertEqual(cm.exception.filename, 'test.csv')
        self.assertEqual(cm.exception.lineno, 3)

    def test_clean_time_sequence_first_row_error(self):
        mp = ImportedMeasurementPoint()

        csv = 'kWh - Time;571313115400167430;571313115400167454\n'\
            ';;\n'\
            '01-08-2010 01:00 - 01-08-2010 00:00;0,475;1,825\n'\
            '01-08-2010 01:00 - 01-08-2010 02:00;0,125;1,8\n'

        mp.consumption_column = 1
        mp.upload_file = SimpleUploadedFile('test.csv', str(csv))
        mp.timezone = pytz.utc
        mp.unit = 'kilowatt*hour'

        with self.assertRaises(ImportedMeasurementPoint.
                               TimeSequenceError) as cm:
            mp.clean()

        self.assertEqual(cm.exception.filename, 'test.csv')
        self.assertEqual(cm.exception.lineno, 2)

    def test_clean_time_sequence_between_rows_error(self):

        mp = ImportedMeasurementPoint()

        csv = 'kWh - Time;571313115400167430;571313115400167454\n'\
            ';;\n'\
            '01-08-2010 00:00 - 01-08-2010 01:00;0,475;1,825\n'\
            '01-08-2010 02:00 - 01-08-2010 03:00;0,125;1,8\n'

        mp.consumption_column = 1
        mp.upload_file = SimpleUploadedFile('test.csv', str(csv))
        mp.timezone = pytz.utc
        mp.unit = 'kilowatt*hour'

        with self.assertRaises(ImportedMeasurementPoint.
                               TimeSequenceError) as cm:
            mp.clean()

        self.assertEqual(cm.exception.filename, 'test.csv')
        self.assertEqual(cm.exception.lineno, 3)

    def test_clean_time_value_error(self):
        mp = ImportedMeasurementPoint()

        csv = 'kWh - Time;571313115400167430;571313115400167454\n'\
            ';;\n'\
            '2010-08-01 8.30pm - 01-08-2010 01:00;0,475;1,825\n'

        mp.consumption_column = 1
        mp.upload_file = SimpleUploadedFile('test.csv', str(csv))
        mp.timezone = pytz.utc
        mp.unit = 'kilowatt*hour'
        with self.assertRaises(ImportedMeasurementPoint.
                               TimeValueError) as cm:
            mp.clean()

        self.assertEqual(cm.exception.filename, 'test.csv')
        self.assertEqual(cm.exception.lineno, 2)

    def test_clean_empty_file_error(self):
        mp = ImportedMeasurementPoint()

        csv = 'kWh - Time;571313115400167430;571313115400167454\n'\
            ';;\n'

        mp.consumption_column = 1
        mp.upload_file = SimpleUploadedFile('test.csv', str(csv))
        mp.timezone = pytz.utc
        mp.unit = 'kilowatt*hour'
        with self.assertRaises(ImportedMeasurementPoint.
                               EmptyFileError) as cm:
            mp.clean()

        self.assertEqual(cm.exception.filename, 'test.csv')

    def test_clean_no_file_no_exception(self):
        mp = ImportedMeasurementPoint()
        mp.consumption_column = 1
        mp.clean()

    def test_save(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        with replace_customer(self.customer):
            assert self.customer is trackuser.get_customer()
            with no_encryption():
                mp = ImportedMeasurementPoint(
                    utility_type=utilitytypes.METER_CHOICES.electricity)
                mp.parsed_csv = [
                    (datetime(2010, 8, 1, 0, 0, tzinfo=pytz.utc),
                     datetime(2010, 8, 1, 1, 0, tzinfo=pytz.utc),
                     Fraction('0.475')),
                    (datetime(2010, 8, 1, 1, 0, tzinfo=pytz.utc),
                     datetime(2010, 8, 1, 2, 0, tzinfo=pytz.utc),
                     Fraction('0.125'))]
                mp.unit = 'kilowatt*hour'
                mp.timezone = pytz.utc
                mp.save()

                self.assertTrue(mp.consumption.stored_data.filter(
                    timestamp=datetime(2010, 8, 1, tzinfo=pytz.utc),
                    value=0).exists())
                self.assertTrue(mp.consumption.stored_data.filter(
                    timestamp=datetime(2010, 8, 1, 1, tzinfo=pytz.utc),
                    value=int(0.475 * 1000000)).exists())
                self.assertTrue(mp.consumption.stored_data.filter(
                    timestamp=datetime(2010, 8, 1, 2, tzinfo=pytz.utc),
                    value=int((0.125 + 0.475) * 1000000)).exists())


@override_settings(ENCRYPTION_TESTMODE=True)
class TestLocation(TestCase):
    """
    Test the L{Location} class.
    """
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()

    def test_dependencies_by_db_level(self):
        loc1 = Location.objects.create(
            name_plain='test 1', customer=self.customer)
        Location.objects.create(
            name_plain='test 2', customer=self.customer, parent=loc1)

        self.assertRaises(ProtectedError, lambda: loc1.delete())

    @unittest.skip("Implementation is missing on model, currently in view.py")
    def test_dependencies(self):
        loc1 = Location.objects.create(
            name_plain='test 1', customer=self.customer)
        Location.objects.create(
            name_plain='test 2', customer=self.customer, parent=loc1)
        self.assertEqual(loc1.is_deletable(), False)


class TestCollection(TestCase):
    """
    Test C{Collection}.
    """

    def test_get_icon_completeness(self):
        """
        Test Collection.get_icon() for completeness.
        """
        unit = Collection()
        for role, _ in Collection.ROLE_CHOICES:
            unit.role = role
            unit.get_icon()


@override_settings(ENCRYPTION_TESTMODE=True)
class CollectionManagerTest(TestCase):
    def setUp(self):
        with encryption_context():
            Provider.objects.create()
            self.customer = Customer()
            self.customer.save()
            self.user = User.objects.create_user(
                'username', 'password', user_type=User.CUSTOMER_USER,
                customer=self.customer)

    def test_no_customer_and_no_user(self):
        collection = Collection.objects.create(
            customer=self.customer,
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.assertEqual(
            collection, Collection.objects.get())

    def test_constraint_customer(self):
        collection = Collection.objects.create(
            customer=self.customer,
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        customer2 = Customer()
        customer2.save()
        Collection.objects.create(
            customer=customer2,
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        with replace_customer(self.customer), replace_user(self.user):
            self.assertEqual(
                collection, Collection.objects.get())

    def test_user_collection_constraint_root(self):
        collection = Collection.objects.create(
            customer=self.customer,
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        Collection.objects.create(
            customer=self.customer,
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        CollectionConstraint.objects.create(
            collection=collection, userprofile=self.user.userprofile)

        with replace_customer(self.customer), replace_user(self.user):
            self.assertEqual(
                collection, Collection.objects.get())

    def test_user_collection_constraint_child(self):
        group = Collection.objects.create(
            customer=self.customer,
            role=Collection.GROUP,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)

        collection = Collection.objects.create(
            parent=group,
            customer=self.customer,
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        rogue_collection = Collection.objects.create(
            customer=self.customer,
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        CollectionConstraint.objects.create(
            collection=group, userprofile=self.user.userprofile)

        with replace_customer(self.customer), replace_user(self.user):
            self.assertTrue(Collection.objects.filter(id=group.id).exists())
            self.assertTrue(Collection.objects.filter(
                id=collection.id).exists())
            self.assertFalse(Collection.objects.filter(
                id=rogue_collection.id).exists())

        self.assertTrue(Collection.objects.filter(id=group.id).exists())
        self.assertTrue(Collection.objects.filter(id=collection.id).exists())
        self.assertTrue(Collection.objects.filter(
            id=rogue_collection.id).exists())
