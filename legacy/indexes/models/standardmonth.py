# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils import first_last
from gridplatform.utils import condense
from legacy.measurementpoints.models import DataSeries

from .index import Index


class StandardMonthIndex(Index):
    """
    C{StandardMonthIndex} is a L{DataSeries} whose underlying function is an
    unbound accumulation of standard values explicitly defined for each month.
    """

    class Meta(Index.Meta):
        verbose_name = _('standard month index')
        verbose_name_plural = _('standard month index')
        app_label = 'indexes'

    january = models.DecimalField(decimal_places=3, max_digits=10)
    february = models.DecimalField(decimal_places=3, max_digits=10)
    march = models.DecimalField(decimal_places=3, max_digits=10)
    april = models.DecimalField(decimal_places=3, max_digits=10)
    may = models.DecimalField(decimal_places=3, max_digits=10)
    june = models.DecimalField(decimal_places=3, max_digits=10)
    july = models.DecimalField(decimal_places=3, max_digits=10)
    august = models.DecimalField(decimal_places=3, max_digits=10)
    september = models.DecimalField(decimal_places=3, max_digits=10)
    october = models.DecimalField(decimal_places=3, max_digits=10)
    november = models.DecimalField(decimal_places=3, max_digits=10)
    december = models.DecimalField(decimal_places=3, max_digits=10)

    def get_month_quantity(self, timestamp):
        """
        Get L{PhysicalQuantity} associated to the month of the given
        C{timestamp}.
        """
        assert timestamp == self.timezone.normalize(
            timestamp.astimezone(self.timezone))
        MONTH_ATTRS = ['january', 'february', 'march', 'april',
                       'may', 'june', 'july', 'august',
                       'september', 'october', 'november', 'december']
        # timestamp.month is in [1, 12], not [0, 11]
        return PhysicalQuantity(
            getattr(self, MONTH_ATTRS[timestamp.month - 1]), self.unit)

    def _get_samples(self, from_timestamp, to_timestamp):
        """
        C{StandardMonthIndex} implementation of
        L{DataSeries.get_raw_data_samples()}.
        """
        assert from_timestamp <= to_timestamp

        # convert end-points to our timezone to ensure L{get_month_value()}
        # works correctly.
        from_timestamp = self.timezone.normalize(
            from_timestamp.astimezone(self.timezone))
        to_timestamp = self.timezone.normalize(
            to_timestamp.astimezone(self.timezone))

        month_delta = RelativeTimeDelta(months=1)

        accumulated_value = PhysicalQuantity(0, self.unit)

        current_month_start = condense.floor(
            from_timestamp, month_delta, self.timezone)
        current_month_end = current_month_start + month_delta

        yield self.create_point_sample(
            from_timestamp, accumulated_value)

        while current_month_start < to_timestamp:
            current_range_start = max(current_month_start, from_timestamp)
            current_range_end = min(current_month_end, to_timestamp)

            accumulated_value += (
                self.get_month_quantity(current_range_start) *
                PhysicalQuantity(
                    (current_range_end -
                     current_range_start).total_seconds(),
                    'second') /
                PhysicalQuantity(
                    (current_month_end -
                     current_month_start).total_seconds(),
                    'second'))
            yield self.create_point_sample(
                current_range_end, accumulated_value)

            current_month_start = current_month_end
            current_month_end += month_delta

    def calculate_development(self, from_timestamp, to_timestamp):
        """
        C{StandardMonth} implementation of
        L{DataSeries.calculate_development()}

        @note: Could share implementation with CostCalculation, but since
        current implementation requires no queries at all, that will not be
        beneficial, once L{CostCalculation.calculate_development()} is
        optimized using cache.
        """
        first, last = first_last(
            self.get_samples(from_timestamp, to_timestamp))
        return self.create_range_sample(
            from_timestamp, to_timestamp,
            last.physical_quantity - first.physical_quantity,
            uncachable=(first.uncachable or last.uncachable))

    def _condense_data_samples_recursive(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        The Index class hierachy is a bit messy. A StandardMonthIndex needs to
        work much like an Index, but its data should be handled more like
        normal DataSeries.
        """
        return DataSeries._condense_data_samples_recursive(
            self, from_timestamp, sample_resolution, to_timestamp)

    def get_recursive_condense_resolution(self, resolution):
        """
        Only one sample pr month in raw data, and these data are part of the
        model itself. No need at all to build cache recursively.
        """
        return None
