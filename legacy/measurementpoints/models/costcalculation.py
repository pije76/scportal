# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.utils.translation import ugettext_lazy as _

from gridplatform.utils.samples import Sample
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.datasequences.utils import aggregate_sum_ranged_sample_sequence  # noqa
from gridplatform.datasequences.utils import multiply_ranged_sample_sequences
from gridplatform.utils.samples import wrap_ranged_sample_sequence
from gridplatform.datasequences.models.base import is_five_minute_multiplum
from gridplatform.utils import condense
from gridplatform.datasequences.models.energyconversion import _break_into_hourly_samples  # noqa
from .indexcalculation import IndexCalculation


def _break_into_fiveminutes_samples(
        ranged_samples, from_timestamp, to_timestamp):
    """
    Yield five-minutes subsamples of each sample in ranged_samples.
    """
    assert is_five_minute_multiplum(from_timestamp), \
        '%r is not a 5 minute multiplum' % from_timestamp
    assert is_five_minute_multiplum(to_timestamp), \
        '%r is not a 5 minute multiplum' % to_timestamp
    timestamp = from_timestamp
    for sample in ranged_samples:
        while timestamp < sample.from_timestamp:
            timestamp += condense.FIVE_MINUTES
        while timestamp < sample.to_timestamp:
            subsample = sample._replace(
                from_timestamp=timestamp,
                to_timestamp=timestamp + condense.FIVE_MINUTES)
            assert subsample.from_timestamp >= sample.from_timestamp
            assert subsample.to_timestamp <= sample.to_timestamp
            yield subsample
            timestamp += condense.FIVE_MINUTES


class CostCalculation(IndexCalculation):
    """
    A C{Costcalculation} is a L{DataSeries} derived from a consumption
    L{DataSeries} and a tariff L{DataSeries}.

    @ivar tariff: The tariff L{DataSeries} used in the cost calculation.

    @ivar consumption: The consumption L{DataSeries} used in the consumption
    calculation.
    """
    class Meta:
        proxy = True
        verbose_name = _('cost calculation')
        verbose_name_plural = _('cost calculations')
        app_label = 'measurementpoints'

    def _get_tariff(self):
        return self.index

    def _set_tariff(self, value):
        self.index = value

    tariff = property(_get_tariff, _set_tariff)

    def _get_tariff_id(self):
        return self.index

    def _set_tariff_id(self, value):
        self.index = value

    tariff_id = property(_get_tariff_id, _set_tariff_id)

    RATE_RESOLUTION = RelativeTimeDelta(hours=1)

    def _hourly_accumulated(self, from_timestamp, to_timestamp):
        assert self.RATE_RESOLUTION == RelativeTimeDelta(hours=1)

        tariff_samples = _break_into_hourly_samples(
            self._get_rate().get_samples(
                from_timestamp, to_timestamp), from_timestamp, to_timestamp)
        consumption_samples = self._get_accumulation().get_condensed_samples(
            from_timestamp, condense.HOURS, to_timestamp)

        return multiply_ranged_sample_sequences(
            consumption_samples, tariff_samples)

    def _five_minute_accumulated(self, from_timestamp, to_timestamp):
        consumption_seq = iter(self._get_accumulation().get_condensed_samples(
            from_timestamp, RelativeTimeDelta(minutes=5), to_timestamp))
        price_seq = _break_into_fiveminutes_samples(
            iter(self._get_rate().get_samples(from_timestamp, to_timestamp)),
            from_timestamp,
            to_timestamp)
        price = next(price_seq)
        while True:
            consumption = next(consumption_seq)
            while price.to_timestamp < consumption.to_timestamp:
                price = next(price_seq)
            assert consumption.from_timestamp >= price.from_timestamp
            assert consumption.to_timestamp <= price.to_timestamp
            yield consumption._replace(
                physical_quantity=consumption.physical_quantity *
                price.physical_quantity)

    def _get_condensed_samples(
            self, from_timestamp, sample_resolution, to_timestamp):
        # NOTE: API from DataSeries
        data = self._hourly_accumulated(from_timestamp, to_timestamp)
        if sample_resolution == RelativeTimeDelta(hours=1):
            return data
        else:
            return wrap_ranged_sample_sequence(
                aggregate_sum_ranged_sample_sequence(
                    data, sample_resolution, self.customer.timezone))

    def calculate_development(self, from_timestamp, to_timestamp):
        from gridplatform.datasequences.models.base import is_five_minute_multiplum  # noqa
        assert is_five_minute_multiplum(from_timestamp), \
            '%r is not a 5 minute multiplum' % from_timestamp
        assert is_five_minute_multiplum(to_timestamp), \
            '%r is not a 5 minute multiplum' % to_timestamp
        assert from_timestamp <= to_timestamp

        if from_timestamp.minute != 0:
            period_end_timestamp = min(
                to_timestamp,
                from_timestamp + datetime.timedelta(
                    minutes=60 - from_timestamp.minute))
            leading_five_minute_period = (from_timestamp, period_end_timestamp)
        else:
            leading_five_minute_period = None

        if to_timestamp.minute != 0 and (
                leading_five_minute_period is None or
                leading_five_minute_period[1] != to_timestamp):
            period_begin_timestamp = \
                to_timestamp - RelativeTimeDelta(minutes=to_timestamp.minute)
            following_five_minute_period = (
                period_begin_timestamp, to_timestamp)
        else:
            following_five_minute_period = None

        if leading_five_minute_period is None:
            hour_from_time = from_timestamp
        else:
            hour_from_time = leading_five_minute_period[1]
        if following_five_minute_period is None:
            hour_to_time = to_timestamp
        else:
            hour_to_time = following_five_minute_period[0]

        value = PhysicalQuantity(0, self.unit)
        if leading_five_minute_period is not None:
            samples = self._five_minute_accumulated(
                leading_five_minute_period[0],
                leading_five_minute_period[1])
            value = sum((s.physical_quantity for s in samples), value)

        if following_five_minute_period is not None:
            samples = self._five_minute_accumulated(
                following_five_minute_period[0],
                following_five_minute_period[1])
            value = sum((s.physical_quantity for s in samples), value)

        if hour_from_time < hour_to_time:
            samples = self._hourly_accumulated(
                hour_from_time,
                hour_to_time)
            value = sum((s.physical_quantity for s in samples), value)
        return Sample(from_timestamp, to_timestamp, value, False, False)
