# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
import pytz
from mock import patch
from mock import MagicMock

from .models import PeriodBase
from .models import SingleValueAccumulationPeriodMixin
from .models import AccumulationPeriodBase


@override_settings(ENCRYPTION_TESTMODE=True)
class PeriodBaseTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')

    def test_clean_happy(self):
        period = PeriodBase(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)))
        period.clean()

    def test_clean_to_timestamp_not_after_from_timestamp(self):
        period = PeriodBase(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)))

        with self.assertRaises(ValidationError):
            period.clean()

    def test_clean_from_timestamp_not_clock_hour(self):
        period = PeriodBase(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1, 1, 42)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))

        with self.assertRaises(ValidationError):
            period.clean()

    def test_clean_to_timestamp_not_clock_hour(self):
        period = PeriodBase(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2, 1, 42)))

        with self.assertRaises(ValidationError):
            period.clean()

    def test_clean_overlapping_periods_happy(self):
        period_1 = PeriodBase(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))
        period_2 = PeriodBase(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))

        PeriodBase.clean_overlapping_periods([period_2, period_1])

    def test_clean_overlapping_periods_unhappy(self):
        period_1 = PeriodBase(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))
        period_2 = PeriodBase(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1, 12)))

        with self.assertRaises(ValidationError):
            PeriodBase.clean_overlapping_periods([period_1, period_2])

    def test_clean_delegates_to_overlapping_periods(self):
        period = PeriodBase(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))

        period.datasequence = MagicMock()
        period.datasequence.period_set = MagicMock()
        period.datasequence.period_set.all = lambda: []

        # autospec doesn't work well for descriptors, so we use side_effect
        # instead (for delegation checks this doesn't matter).
        patched_clean_overlapping_periods = patch.object(
            PeriodBase, 'clean_overlapping_periods',
            side_effect=PeriodBase.clean_overlapping_periods)

        with patched_clean_overlapping_periods as mock:
            period.clean()

        mock.assert_called_with([period])


class TestSingleValueAccumulationPeriod(
        SingleValueAccumulationPeriodMixin, AccumulationPeriodBase):
    datasequence = None


class SingleValueAccumulationPeriodMixinTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')

    def test_clean_empty_period(self):
        # recreates a bug
        period = TestSingleValueAccumulationPeriod(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            value=1234,
            unit='kilowatt*hour')

        with self.assertRaises(ValidationError):
            period.clean()
