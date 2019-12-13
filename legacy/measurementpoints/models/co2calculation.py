# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import operator

from django.utils.translation import ugettext_lazy as _

from gridplatform.utils.samples import Sample
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.datasequences.utils import aggregate_sum_ranged_sample_sequence  # noqa
from gridplatform.utils.samples import wrap_ranged_sample_sequence
from gridplatform.datasequences.utils import multiply_ranged_sample_sequences
from gridplatform.utils import condense

from .indexcalculation import IndexCalculation
from .costcalculation import _break_into_fiveminutes_samples


class Co2Calculation(IndexCalculation):
    """
    A C{Co2Calculation} is a L{DataSeries} derived from a consumption
    L{DataSeries} and a index L{DataSeries}.

    @ivar index: The index L{DataSeries} used in the CO2 calculation.

    @ivar consumption: The consumption L{DataSeries} used in the consumption
    calculation.
    """

    class Meta:
        proxy = True
        verbose_name = _('CO₂ calculation')
        verbose_name_plural = _('CO₂ calculations')
        app_label = 'measurementpoints'

    RATE_RESOLUTION = RelativeTimeDelta(minutes=5)

    def _five_minute_accumulated(self, from_timestamp, to_timestamp):
        assert self.RATE_RESOLUTION == RelativeTimeDelta(minutes=5)

        co2conversion_samples = _break_into_fiveminutes_samples(
            self._get_rate().get_samples(
                from_timestamp, to_timestamp), from_timestamp, to_timestamp)
        consumption_samples = self._get_accumulation().get_condensed_samples(
            from_timestamp, condense.FIVE_MINUTES, to_timestamp)

        return multiply_ranged_sample_sequences(
            consumption_samples, co2conversion_samples)

    def _get_condensed_samples(
            self, from_timestamp, sample_resolution, to_timestamp):
        # NOTE: API from DataSeries
        data = self._five_minute_accumulated(from_timestamp, to_timestamp)
        if sample_resolution == RelativeTimeDelta(minutes=5):
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
        samples = self._five_minute_accumulated(from_timestamp, to_timestamp)
        value = reduce(
            operator.add,
            (s.physical_quantity for s in samples),
            PhysicalQuantity(0, self.unit))
        return Sample(from_timestamp, to_timestamp, value, False, False)
