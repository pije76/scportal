# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.test import TestCase
from django.test import SimpleTestCase
from django.test.utils import override_settings

import pytz

from gridplatform.utils.samples import Sample
from gridplatform.utils.unitconversion import PhysicalQuantity

from gridplatform.customer_datasources.models import DataSource
from gridplatform.datasources.models import RawData
from gridplatform.datasources.models import interpolate

from .models import adjust_from_to
from .models import generate_cache
from .models import generate_period_data
from .models import missing_periods
from .models import period_aligned
from .models import raw_data_for_cache


@override_settings(
    ENCRYPTION_TESTMODE=True)
class CleanupCacheForRawdataDeleteTest(TestCase):
    def setUp(self):
        self.datasource = DataSource.objects.create(unit='milliwatt*hour')

    def test_delete(self):
        # NOTE: Cleanup is slightly conservative --- removes periods touching
        # endpoints of tainted period (which might not be strictly
        # necessary...)
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 13, 0, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 13, 2, tzinfo=pytz.utc), 8),
            (datetime.datetime(2014, 4, 14, 14, 0, tzinfo=pytz.utc), 17),
            (datetime.datetime(2014, 4, 14, 15, 0, tzinfo=pytz.utc), 29),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        generate_cache(self.datasource, from_timestamp, to_timestamp)
        obj = RawData.objects.get(
            timestamp=datetime.datetime(2014, 4, 14, 13, 2, tzinfo=pytz.utc))
        obj.delete()
        expected_hours = []
        self.assertEqual(
            list(self.datasource.houraccumulateddata_set.order_by(
                'timestamp').values_list('timestamp', 'value')),
            expected_hours)
        expected_minutes = [
            (datetime.datetime(2014, 4, 14, 14, 5, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 10, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 15, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 20, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 25, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 30, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 35, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 40, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 45, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 50, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 55, tzinfo=pytz.utc), 1),
        ]
        self.assertEqual(
            list(self.datasource.fiveminuteaccumulateddata_set.order_by(
                'timestamp').values_list('timestamp', 'value')),
            expected_minutes)


@override_settings(
    ENCRYPTION_TESTMODE=True)
class GetAccumulatedTest(TestCase):
    def setUp(self):
        self.datasource = DataSource.objects.create(unit='milliwatt*hour')

    def test_all_cached(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 11, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 77),
            (datetime.datetime(2014, 4, 14, 22, tzinfo=pytz.utc), 77),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        generate_cache(self.datasource, from_timestamp, to_timestamp)
        expected_hours = [
            Sample(
                datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc),
                PhysicalQuantity(12, 'milliwatt*hour'), False, False),
            Sample(
                datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc),
                PhysicalQuantity(12, 'milliwatt*hour'), False, False),
        ]
        self.assertEqual(
            self.datasource.hourly_accumulated(from_timestamp, to_timestamp),
            expected_hours)
        expected_minutes = [
            Sample(
                datetime.datetime(2014, 4, 14, 13, 0, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 13, 5, tzinfo=pytz.utc),
                PhysicalQuantity(1, 'milliwatt*hour'), False, False),
            Sample(
                datetime.datetime(2014, 4, 14, 13, 5, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 13, 10, tzinfo=pytz.utc),
                PhysicalQuantity(1, 'milliwatt*hour'), False, False),
            Sample(
                datetime.datetime(2014, 4, 14, 13, 10, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 13, 15, tzinfo=pytz.utc),
                PhysicalQuantity(1, 'milliwatt*hour'), False, False),
        ]
        self.assertEqual(
            self.datasource.five_minute_accumulated(
                from_timestamp,
                from_timestamp + datetime.timedelta(minutes=15)),
            expected_minutes)

    def test_partial_data(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 11, 0, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 14, 30, tzinfo=pytz.utc), 47),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        generate_cache(self.datasource, from_timestamp, to_timestamp)
        expected_hours = [
            Sample(
                datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc),
                PhysicalQuantity(12, 'milliwatt*hour'), False, False),
        ]
        self.assertEqual(
            self.datasource.hourly_accumulated(from_timestamp, to_timestamp),
            expected_hours)

    def test_partial_cache(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        cache_from_timestamp = datetime.datetime(
            2014, 4, 14, 13, tzinfo=pytz.utc)
        cache_to_timestamp = datetime.datetime(
            2014, 4, 14, 14, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 11, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 77),
            (datetime.datetime(2014, 4, 14, 22, tzinfo=pytz.utc), 77),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        generate_cache(
            self.datasource, cache_from_timestamp, cache_to_timestamp)
        expected_hours = [
            Sample(
                datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc),
                PhysicalQuantity(12, 'milliwatt*hour'), False, False),
            Sample(
                datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc),
                PhysicalQuantity(12, 'milliwatt*hour'), False, False),
        ]
        self.assertEqual(
            self.datasource.hourly_accumulated(from_timestamp, to_timestamp),
            expected_hours)

    def test_pulse(self):
        self.datasource.unit = 'impulse'
        self.datasource.save()
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        cache_from_timestamp = datetime.datetime(
            2014, 4, 14, 13, tzinfo=pytz.utc)
        cache_to_timestamp = datetime.datetime(
            2014, 4, 14, 14, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 11, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 77),
            (datetime.datetime(2014, 4, 14, 22, tzinfo=pytz.utc), 77),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        generate_cache(
            self.datasource, cache_from_timestamp, cache_to_timestamp)
        expected_hours = [
            Sample(
                datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc),
                PhysicalQuantity(72, 'impulse'), False, False),
            Sample(
                datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc),
                PhysicalQuantity(0, 'impulse'), False, False),
        ]
        self.assertEqual(
            self.datasource.hourly_accumulated(from_timestamp, to_timestamp),
            expected_hours)


@override_settings(
    ENCRYPTION_TESTMODE=True)
class GenerateCacheTest(TestCase):
    def setUp(self):
        self.datasource = DataSource.objects.create(unit='milliwatt*hour')

    def test_complete(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 11, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 77),
            (datetime.datetime(2014, 4, 14, 22, tzinfo=pytz.utc), 77),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        generate_cache(self.datasource, from_timestamp, to_timestamp)
        expected_hours = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 12),
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 12),
        ]
        self.assertEqual(
            list(self.datasource.houraccumulateddata_set.order_by(
                'timestamp').values_list('timestamp', 'value')),
            expected_hours)
        expected_minutes = [
            (datetime.datetime(2014, 4, 14, 13, 0, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 5, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 10, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 15, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 20, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 25, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 30, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 35, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 40, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 45, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 50, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 55, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 0, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 5, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 10, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 15, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 20, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 25, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 30, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 35, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 40, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 45, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 50, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 55, tzinfo=pytz.utc), 1),
        ]
        self.assertEqual(
            list(self.datasource.fiveminuteaccumulateddata_set.order_by(
                'timestamp').values_list('timestamp', 'value')),
            expected_minutes)

    def test_partial(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 11, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc), 29),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        generate_cache(self.datasource, from_timestamp, to_timestamp)
        expected_hours = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 12),
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 12),
        ]
        self.assertEqual(
            list(self.datasource.houraccumulateddata_set.order_by(
                'timestamp').values_list('timestamp', 'value')),
            expected_hours)
        expected_minutes = [
            (datetime.datetime(2014, 4, 14, 13, 0, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 5, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 10, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 15, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 20, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 25, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 30, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 35, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 40, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 45, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 50, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 13, 55, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 0, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 5, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 10, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 15, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 20, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 25, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 30, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 35, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 40, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 45, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 50, tzinfo=pytz.utc), 1),
            (datetime.datetime(2014, 4, 14, 14, 55, tzinfo=pytz.utc), 1),
        ]
        self.assertEqual(
            list(self.datasource.fiveminuteaccumulateddata_set.order_by(
                'timestamp').values_list('timestamp', 'value')),
            expected_minutes)


class MissingPeriodsTest(SimpleTestCase):
    def test_missing_periods(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        present = [
            datetime.datetime(2014, 4, 14, 12, tzinfo=pytz.utc),
            datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc),
            datetime.datetime(2014, 4, 14, 16, tzinfo=pytz.utc),
        ]
        expected_missing = [
            (
                datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 16, tzinfo=pytz.utc),
            ),
            (
                datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc),
                datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc),
            ),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            list(missing_periods(
                from_timestamp, to_timestamp, present, period_length)),
            expected_missing)


class GeneratePeriodDataTest(SimpleTestCase):
    def test_empty(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = []
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            list(generate_period_data(
                data, from_timestamp, to_timestamp,
                period_length, interpolate)),
            [])

    def test_matching(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc), 20),
            (datetime.datetime(2014, 4, 14, 16, tzinfo=pytz.utc), 35),
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 45),
            (datetime.datetime(2014, 4, 14, 18, tzinfo=pytz.utc), 50),
            (datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc), 50),
        ]
        period_length = datetime.timedelta(hours=1)
        expected = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc), 15),
            (datetime.datetime(2014, 4, 14, 16, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 18, tzinfo=pytz.utc), 0),
        ]
        self.assertEqual(
            list(generate_period_data(
                data, from_timestamp, to_timestamp,
                period_length, interpolate)),
            expected)

    def test_interpolate(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 12, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 16, tzinfo=pytz.utc), 45),
        ]
        period_length = datetime.timedelta(hours=1)
        expected = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 10),
        ]
        self.assertEqual(
            list(generate_period_data(
                data, from_timestamp, to_timestamp,
                period_length, interpolate)),
            expected)

    def test_partial(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 25),
            (datetime.datetime(2014, 4, 14, 16, tzinfo=pytz.utc), 45),
        ]
        period_length = datetime.timedelta(hours=1)
        expected = [
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 10),
        ]
        self.assertEqual(
            list(generate_period_data(
                data, from_timestamp, to_timestamp,
                period_length, interpolate)),
            expected)


@override_settings(
    ENCRYPTION_TESTMODE=True)
class RawDataForCacheTest(TestCase):
    def setUp(self):
        self.datasource = DataSource.objects.create(unit='milliwatt*hour')

    def test_no_data(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        self.assertEqual(
            raw_data_for_cache(self.datasource, from_timestamp, to_timestamp),
            [])

    def test_edges(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (from_timestamp, 50),
            (to_timestamp, 100),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        self.assertEqual(
            raw_data_for_cache(self.datasource, from_timestamp, to_timestamp),
            data)

    def test_close_outside(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 12, 59, 15, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 7),
            (datetime.datetime(2014, 4, 14, 19, 1, 45, tzinfo=pytz.utc), 8),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        self.assertEqual(
            raw_data_for_cache(self.datasource, from_timestamp, to_timestamp),
            data)

    def test_outside(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 11, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 7),
            (datetime.datetime(2014, 4, 14, 22, tzinfo=pytz.utc), 8),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        self.assertEqual(
            raw_data_for_cache(self.datasource, from_timestamp, to_timestamp),
            data)

    def test_missing_end(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 11, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 7),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        self.assertEqual(
            raw_data_for_cache(self.datasource, from_timestamp, to_timestamp),
            data)

    def test_missing_start(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 7),
            (datetime.datetime(2014, 4, 14, 22, tzinfo=pytz.utc), 8),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        self.assertEqual(
            raw_data_for_cache(self.datasource, from_timestamp, to_timestamp),
            data)

    def test_filtering(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 12, 58, 15, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 12, 59, 15, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc), 7),
            (datetime.datetime(2014, 4, 14, 19, 1, 45, tzinfo=pytz.utc), 8),
            (datetime.datetime(2014, 4, 14, 19, 2, 45, tzinfo=pytz.utc), 8),
        ]
        RawData.objects.bulk_create([
            RawData(
                datasource=self.datasource, value=value, timestamp=timestamp)
            for timestamp, value in data])
        self.assertEqual(
            raw_data_for_cache(self.datasource, from_timestamp, to_timestamp),
            data[1:-1])


class AdjustFromToTest(SimpleTestCase):
    def test_noop_covered(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 12, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 20, tzinfo=pytz.utc), 20),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (from_timestamp, to_timestamp))

    def test_noop_edges(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (from_timestamp, 5),
            (to_timestamp, 10),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (from_timestamp, to_timestamp))

    def test_adjust_from(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 14, 5, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 20, tzinfo=pytz.utc), 20),
        ]
        period_length = datetime.timedelta(hours=1)
        expected_from = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (expected_from, to_timestamp))

    def test_adjust_to(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 12, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 17, 35, tzinfo=pytz.utc), 20),
        ]
        period_length = datetime.timedelta(hours=1)
        # NTS: Data is measured at timestamp; *not* representing periods
        # period_length periods here.
        expected_to = datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (from_timestamp, expected_to))

    def test_adjust_both(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 14, 20, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 17, 35, tzinfo=pytz.utc), 20),
        ]
        period_length = datetime.timedelta(hours=1)
        expected_from = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        expected_to = datetime.datetime(2014, 4, 14, 17, tzinfo=pytz.utc)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (expected_from, expected_to))

    def test_only_before(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 11, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 12, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 12, 35, tzinfo=pytz.utc), 20),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (None, None))

    def test_only_after(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 19, 20, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 20, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 22, tzinfo=pytz.utc), 20),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (None, None))

    def test_partial_inside(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 15, 20, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 15, 55, tzinfo=pytz.utc), 10),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (None, None))

    def test_aligned_inside(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (data_timestamp, 5),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (data_timestamp, data_timestamp))

    def test_empty(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 19, tzinfo=pytz.utc)
        data = []
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            adjust_from_to(data, from_timestamp, to_timestamp, period_length),
            (None, None))


class PeriodAlignedTest(SimpleTestCase):
    def test_matching(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc), 15),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            list(period_aligned(
                data, from_timestamp, to_timestamp,
                period_length, interpolate)),
            data)

    def test_interpolate_middle(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc), 15),
        ]
        expected = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc), 15),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            list(period_aligned(
                data, from_timestamp, to_timestamp,
                period_length, interpolate)),
            expected)

    def test_interpolate(self):
        from_timestamp = datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc)
        to_timestamp = datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc)
        data = [
            (datetime.datetime(2014, 4, 14, 12, 30, tzinfo=pytz.utc), 5),
            (datetime.datetime(2014, 4, 14, 13, 30, tzinfo=pytz.utc), 7),
            (datetime.datetime(2014, 4, 14, 14, 30, tzinfo=pytz.utc), 13),
            (datetime.datetime(2014, 4, 14, 15, 30, tzinfo=pytz.utc), 15),
        ]
        expected = [
            (datetime.datetime(2014, 4, 14, 13, tzinfo=pytz.utc), 6),
            (datetime.datetime(2014, 4, 14, 14, tzinfo=pytz.utc), 10),
            (datetime.datetime(2014, 4, 14, 15, tzinfo=pytz.utc), 14),
        ]
        period_length = datetime.timedelta(hours=1)
        self.assertEqual(
            list(period_aligned(
                data, from_timestamp, to_timestamp,
                period_length, interpolate)),
            expected)
