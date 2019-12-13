# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.test import TestCase
from django.test import SimpleTestCase

import pytz

from gridplatform.utils import condense
from gridplatform.utils.samples import RangedSample
from gridplatform.utils.unitconversion import PhysicalQuantity

from .utils import _pad_ranged_sample_sequence
from .utils import add_ranged_sample_sequences
from .utils import aggregate_sum_ranged_sample_sequence
from .utils import subtract_ranged_sample_sequences


class AggregateSumRangedSampleSequenceTest(SimpleTestCase):
    def test_noop(self):
        """
        Sanity check; grouping hours to hours should not alter data.
        """
        start = datetime.datetime(2014, 4, 14, 12, 0, tzinfo=pytz.utc)
        data = [
            RangedSample(
                start,
                start + datetime.timedelta(hours=1),
                PhysicalQuantity(1, 'liter')),
            RangedSample(
                start + datetime.timedelta(hours=1),
                start + datetime.timedelta(hours=2),
                PhysicalQuantity(2, 'liter')),
            RangedSample(
                start + datetime.timedelta(hours=2),
                start + datetime.timedelta(hours=3),
                PhysicalQuantity(5, 'liter')),
        ]
        resolution = condense.HOURS
        timezone = pytz.utc
        self.assertEqual(
            list(
                aggregate_sum_ranged_sample_sequence(
                    data, resolution, timezone)),
            data)

    def test_timezone(self):
        """
        Grouping by days should match days in specified timezone rather than
        input data timezone.
        """
        start = datetime.datetime(2014, 1, 14, 21, 0, tzinfo=pytz.utc)
        data = [
            RangedSample(
                start,
                start + datetime.timedelta(hours=1),
                PhysicalQuantity(1, 'liter')),
            RangedSample(
                start + datetime.timedelta(hours=1),
                start + datetime.timedelta(hours=2),
                PhysicalQuantity(2, 'liter')),
            RangedSample(
                start + datetime.timedelta(hours=2),
                start + datetime.timedelta(hours=3),
                PhysicalQuantity(5, 'liter')),
        ]
        resolution = condense.DAYS
        timezone = pytz.timezone('Europe/Copenhagen')
        expected = [
            RangedSample(
                datetime.datetime(2014, 1, 14, tzinfo=timezone),
                datetime.datetime(2014, 1, 15, tzinfo=timezone),
                PhysicalQuantity(3, 'liter')),
            RangedSample(
                datetime.datetime(2014, 1, 15, tzinfo=timezone),
                datetime.datetime(2014, 1, 16, tzinfo=timezone),
                PhysicalQuantity(5, 'liter')),
        ]
        self.assertEqual(
            list(
                aggregate_sum_ranged_sample_sequence(
                    data, resolution, timezone)),
            expected)


class PadSampleSequenceTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.sequence = [
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1, h)),
                self.timezone.localize(datetime.datetime(2014, 1, 1, h + 1)),
                PhysicalQuantity(1, 'joule')) for h in range(3)]
        self.from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))
        self.to_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1, 3))

    def test_none_missing(self):
        self.assertEqual(
            self.sequence,
            list(_pad_ranged_sample_sequence(
                self.sequence, self.from_timestamp, self.to_timestamp,
                condense.HOURS)))

    def test_start_missing(self):
        self.sequence[0] = None
        self.assertEqual(
            self.sequence,
            list(_pad_ranged_sample_sequence(
                (sample for sample in self.sequence if sample is not None),
                self.from_timestamp, self.to_timestamp, condense.HOURS)))

    def test_middle_missing(self):
        self.sequence[1] = None
        self.assertEqual(
            self.sequence,
            list(_pad_ranged_sample_sequence(
                (sample for sample in self.sequence if sample is not None),
                self.from_timestamp, self.to_timestamp, condense.HOURS)))

    def test_end_missing(self):
        self.sequence[-1] = None
        self.assertEqual(
            self.sequence,
            list(_pad_ranged_sample_sequence(
                (sample for sample in self.sequence if sample is not None),
                self.from_timestamp, self.to_timestamp, condense.HOURS)))


class AddRangedSampleSequencesTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')

    def test_empty(self):
        self.assertEqual(
            [],
            list(
                add_ranged_sample_sequences(
                    [],
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2)),
                    condense.DAYS)))

    def test_one_empty_datasequence(self):
        self.assertEqual(
            [],
            list(
                add_ranged_sample_sequences(
                    [[]],
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2)),
                    condense.DAYS)))

    def test_more_datasequences(self):
        sequence = iter(
            add_ranged_sample_sequences(
                [
                    [
                        RangedSample(
                            self.timezone.localize(
                                datetime.datetime(2014, 1, 1)),
                            self.timezone.localize(
                                datetime.datetime(2014, 1, 2)),
                            PhysicalQuantity(7, 'joule'))],
                    [
                        RangedSample(
                            self.timezone.localize(
                                datetime.datetime(2014, 1, 1)),
                            self.timezone.localize(
                                datetime.datetime(2014, 1, 2)),
                            PhysicalQuantity(42, 'joule'))]],
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)),
                condense.DAYS))

        self.assertEqual(
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)),
                PhysicalQuantity(49, 'joule')),
            next(sequence))

        with self.assertRaises(StopIteration):
            next(sequence)


class SubtractRangedSampleSequencesTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')

    def test_empty(self):
        sequence = iter(subtract_ranged_sample_sequences([], []))
        with self.assertRaises(StopIteration):
            next(sequence)

    def test_matching_samples(self):
        sequence = iter(subtract_ranged_sample_sequences(
            [
                RangedSample(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2)),
                    PhysicalQuantity(19, 'joule')),
            ], [
                RangedSample(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2)),
                    PhysicalQuantity(13, 'joule')),
            ]))

        self.assertEqual(
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)),
                PhysicalQuantity(6, 'joule')),
            next(sequence))

        with self.assertRaises(StopIteration):
            next(sequence)

    def test_a_before_b(self):
        sequence = iter(subtract_ranged_sample_sequences(
            [
                RangedSample(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2)),
                    PhysicalQuantity(19, 'joule')),
            ], [
                RangedSample(
                    self.timezone.localize(datetime.datetime(2014, 1, 2)),
                    self.timezone.localize(datetime.datetime(2014, 1, 3)),
                    PhysicalQuantity(13, 'joule')),
            ]))

        self.assertEqual(
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)),
                PhysicalQuantity(19, 'joule')),
            next(sequence))

        self.assertEqual(
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 2)),
                self.timezone.localize(datetime.datetime(2014, 1, 3)),
                -PhysicalQuantity(13, 'joule')),
            next(sequence))

        with self.assertRaises(StopIteration):
            next(sequence)

    def test_b_before_a(self):
        sequence = iter(subtract_ranged_sample_sequences(
            [
                RangedSample(
                    self.timezone.localize(datetime.datetime(2014, 1, 2)),
                    self.timezone.localize(datetime.datetime(2014, 1, 3)),
                    PhysicalQuantity(19, 'joule')),
            ], [
                RangedSample(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2)),
                    PhysicalQuantity(13, 'joule')),
            ]))

        self.assertEqual(
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)),
                -PhysicalQuantity(13, 'joule')),
            next(sequence))

        self.assertEqual(
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 2)),
                self.timezone.localize(datetime.datetime(2014, 1, 3)),
                PhysicalQuantity(19, 'joule')),
            next(sequence))

        with self.assertRaises(StopIteration):
            next(sequence)
