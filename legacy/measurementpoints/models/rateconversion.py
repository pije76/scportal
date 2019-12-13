# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from fractions import Fraction

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.utils.iter_ext import pairwise
from gridplatform.utils.unitconversion import PhysicalQuantity

from .dataseries import DataSeries


class RateConversion(DataSeries):
    """
    A C{RateConversion} converts a consumption data series to a rate data
    series.

    @ivar consumption: The consumption data series that this C{RateConversion}
    is defined in terms of.
    """
    consumption = models.ForeignKey(
        DataSeries, on_delete=models.CASCADE,
        related_name='rate_conversion_derivative_set')

    class Meta(DataSeries.Meta):
        verbose_name = _('rate conversion')
        verbose_name_plural = _('rate conversions')
        app_label = 'measurementpoints'

    def get_recursive_condense_resolution(self, resolution):
        # Whatever is efficient for the consumption, ought to be efficient for
        # the derived rate.
        return self.consumption.subclass_instance.\
            get_recursive_condense_resolution(resolution)

    def _get_samples(self, from_timestamp, to_timestamp):
        """
        C{RateConversion} implementation of
        L{DataSeries.get_raw_data_samples()}.
        """
        if from_timestamp == to_timestamp:
            # Usually will not happen. But possible for a user to provoke this
            # by having one stage much smaller than another in benchmark
            # projects.  Also note that the precondition inherited from
            # DataSeries.get_samples() is only that from_timestamp <=
            # to_timestamp, and we are not allowed to strengthen preconditions.
            return []

        # if from_timestamp == to_timestamp the remainder of this function may
        # raise ZeroDivisionError, because timespan is zero.
        assert from_timestamp < to_timestamp
        assert self.consumption.is_accumulation()

        result = []
        raw_consumption = self.consumption.subclass_instance.\
            get_samples(from_timestamp, to_timestamp)

        for first_sample, next_sample in pairwise(raw_consumption):
            if not first_sample.extrapolated and not next_sample.extrapolated:
                timespan = PhysicalQuantity(
                    Fraction(
                        (
                            next_sample.timestamp -
                            first_sample.timestamp).
                        total_seconds()),
                    'second')
                physical_quantity = (
                    (
                        next_sample.physical_quantity -
                        first_sample.physical_quantity) /
                    timespan)

                result.append(
                    self.create_point_sample(
                        next_sample.timestamp, physical_quantity,
                        uncachable=(
                            next_sample.uncachable or
                            first_sample.uncachable)))

                # Check post-condition
                assert result[-1].from_timestamp >= from_timestamp
                assert result[-1].to_timestamp <= to_timestamp

        if result == []:
            # insufficient samples to convert to rate.
            return []

        assert result[0].timestamp != from_timestamp
        result.insert(0, self.create_point_sample(
            from_timestamp,
            result[0].physical_quantity,
            uncachable=True))

        # follows from post condition of consumption.get_samples
        assert len(result) >= 2, \
            'consumption.get_samples() violates its post condition ' \
            '(consumption is an instance of %s)' % \
            self.consumption.__class__.__name__

        return result
