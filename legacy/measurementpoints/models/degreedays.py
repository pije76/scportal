# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import itertools
import logging

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from gridplatform.utils.iter_ext import count_extended
from gridplatform.utils.iter_ext import flatten
from gridplatform.utils.iter_ext import pairwise
from gridplatform.utils.iter_ext import pairwise_extended
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import condense

from .dataseries import DataSeries
from .dataseries import UndefinedSamples
from .mixins import VariablyBoundAccumulationMixin
from ..fields import DataRoleField


logger = logging.getLogger(__name__)


celsius_base = PhysicalQuantity('273.15', 'kelvin')
degree_day_base = celsius_base + PhysicalQuantity(17, 'kelvin')


def _inject_interpolated(ds, from_timestamp, to_timestamp, timestamp_sequence):
    # Assuming that ds.get_samples(from_timestamp, to_timestamp) includes
    # interpolated or extrapolated samples at the endpoints, and that
    # from_timestamp and to_timestamp are elements in timestamp_sequence, this
    # returns a sequence of samples where samples at the time points specified
    # in timestamp_sequence (until to_timestamp) are guaranteed to be included;
    # either from the "raw" sequence or through interpolation of elements from
    # the "raw" sequence.

    # NTS: generalise/make into DS method raw_with_interpolated()?
    def interpolate(t, before, after):
        return ds._interpolate_extrapolate_sample(
            t, data_before=before, data_after=after)

    temperatures = ds.get_samples(from_timestamp, to_timestamp)
    temperature_pairs = pairwise_extended(temperatures)

    timestamp = next(timestamp_sequence)
    for t0, t1 in temperature_pairs:
        # requested period may start before available data...
        while timestamp < t0.timestamp:
            timestamp = next(timestamp_sequence)
        yield t0
        if t1 is None:
            return
        if t1.timestamp > timestamp:
            # may need to inject one or more interpolated values...
            if t0.timestamp == timestamp:
                # timestamp is represented; has been yielded
                timestamp = next(timestamp_sequence)
            assert t0.timestamp < timestamp
            while timestamp < t1.timestamp:
                assert from_timestamp <= timestamp <= to_timestamp
                yield interpolate(timestamp, t0, t1)
                timestamp = next(timestamp_sequence)


def _temperature_pair_value(t0, t1):
    # NOTE: module-level rather than inner function in get_samples()
    # to make explicit that it does not use variables from that context...
    assert t0 is not None
    assert t1 is not None
    seconds = (t1.timestamp - t0.timestamp).total_seconds()
    val0 = degree_day_base - t0.physical_quantity
    val1 = degree_day_base - t1.physical_quantity
    return ((val0 + val1) / 2) * PhysicalQuantity(seconds, 'second')


class HeatingDegreeDays(VariablyBoundAccumulationMixin, DataSeries):
    """
    Data series computing "degree days" based on some temperature data series.

    For each day with an average temperature under 17 °C, the number of "degree
    days" is the difference between 17 °C and the average temperature for that
    day.  For days with average temperature at or above 17 °C, the number of
    "degree days" is 0.  For a period of several days, the number of degree
    days is the sum of the degree days for each day contained therein.  The
    concept of degree days is not defined for timespans shorter than a day.

    C{HeatingDegreeDays} are only defined for whole days, and L{get_samples}
    and L{get_condensed_samples} will raise L{UndefinedSamples} if called with
    odd or too short periods (C{from_timestamp}, C{to_timestamp}) or too small
    sample_resolution.
    """
    derived_from = models.ForeignKey(
        DataSeries, on_delete=models.CASCADE,
        related_name='heatingdegreedays_derivative_set')

    class Meta(DataSeries.Meta):
        app_label = 'measurementpoints'

    def clean(self):
        if self.role is None:
            self.role = DataRoleField.HEATING_DEGREE_DAYS
        if not self.unit:
            self.unit = 'kelvin*day'
        if self.derived_from is not None:
            if self.derived_from.role != DataRoleField.ABSOLUTE_TEMPERATURE:
                raise ValidationError(
                    _('Heating degree days can only be defined in '
                      'terms of absolute temperatures.'))
            if not PhysicalQuantity.compatible_units(
                    self.derived_from.unit, 'kelvin'):
                raise ValidationError('Unit %s on temperature data series not '
                                      'usable for HeatingDegreeDays')
        super(HeatingDegreeDays, self).clean()

    def _get_samples(self, from_timestamp, to_timestamp):
        """
        Return a sequence of computed daily accumulated degree days since
        from_timestamp.

        @raise UndefinedSamples: If C{from_timestamp} or C{to_timestamp} are
        not midnights.
        """
        # For each day, compute average temperature, subtract 17 degrees
        # Celsius, round negative numbers to 0, and return as kelvin*day ...

        # Unit should be "kelvin*day" --- but need not be represented by that
        # exact string...
        sample_resolution = RelativeTimeDelta(days=1)
        timezone = from_timestamp.tzinfo
        assert timezone is not None
        assert PhysicalQuantity.same_unit(self.unit, 'kelvin*day')
        if condense.floor(
                from_timestamp, sample_resolution, timezone) != from_timestamp or \
                condense.floor(
                    to_timestamp, sample_resolution, timezone) != to_timestamp:
            raise UndefinedSamples(
                _('Warning: Heating degree days are only defined for '
                  'days or larger resolutions.'))

        # temperature sample pairs, extended with (interpolated) values for
        # each "midnight"
        temperature_pairs = pairwise_extended(_inject_interpolated(
            self.derived_from, from_timestamp, to_timestamp,
            count_extended(from_timestamp, sample_resolution)))

        try:
            t0, t1 = next(temperature_pairs)
        except StopIteration:
            # no data at all...
            # NOTE: Just letting the StopIteration exception pass through
            # should work, but this makes handling of that edge case --- that
            # nothing should be returned if there is no "raw" data to base the
            # computation on --- clearer/more explicit.
            return

        accumulated = PhysicalQuantity(0, self.unit)
        # We yield accumulated values since from_timestamp --- the accumulated
        # value at from_timestamp should be 0.
        #
        # NOTE: *After* reading from temperature_pairs --- if there is no data
        # at all, we already returned without yielding anything at all.
        if t0.timestamp > from_timestamp:
            # Extrapolate to 0 degree-days before first actual measurement.
            for t in count_extended(from_timestamp, RelativeTimeDelta(days=1)):
                if t < t0.from_timestamp:
                    yield self.create_point_sample(
                        t, accumulated, uncachable=True, extrapolated=True)
                else:
                    break

            from_timestamp = t
            # "Real" data starts at this new from_timestamp ...
            while t1 is not None and t1.timestamp <= from_timestamp:
                # Skip ahead in temperature input until the start of the first
                # "whole" day.  When t1.timestamp == from_timestamp, next will
                # have t0.timestamp == from_timestamp ...
                t0, t1 = next(temperature_pairs)
        yield self.create_point_sample(
            from_timestamp, accumulated,
            uncachable=t0.uncachable, extrapolated=t0.extrapolated)
        if t1 is None and from_timestamp != to_timestamp:
            assert from_timestamp != to_timestamp
            yield self.create_point_sample(
                to_timestamp, accumulated,
                uncachable=True, extrapolated=t0.extrapolated)
            return

        time_periods = itertools.takewhile(
            lambda (t0, t1): t0 < to_timestamp,
            pairwise(
                count_extended(from_timestamp, RelativeTimeDelta(days=1))))

        zero_kelvin_days = PhysicalQuantity(0, 'kelvin*day')

        for day_begin, day_end in time_periods:
            day_accumulated = PhysicalQuantity(0, self.unit)
            uncachable = False
            extrapolated = False
            assert t1 is None or t0.timestamp == day_begin
            while t1 is not None and t1.timestamp <= day_end:
                uncachable = uncachable or t0.uncachable or t1.uncachable
                extrapolated = extrapolated or \
                    t0.extrapolated or t1.extrapolated
                day_accumulated += _temperature_pair_value(t0, t1)
                t0, t1 = next(temperature_pairs)
            if t0.timestamp == day_end:
                # Increment total accumulated normally for day
                assert t1 is None or t1.timestamp > day_end
                day_accumulated = max(day_accumulated, zero_kelvin_days)
                accumulated += day_accumulated
            else:
                # No more data; total accumulated stays constant; data is
                # extrapolation
                assert t1 is None
                uncachable = True
                extrapolated = True
            # Yield real or extrapolated data...
            assert from_timestamp <= day_end <= to_timestamp
            yield self.create_point_sample(
                day_end, accumulated,
                uncachable=uncachable, extrapolated=extrapolated)

    def depends_on(self):
        return [self.derived_from] + self.derived_from.depends_on()

    def get_recursive_condense_resolution(self, resolution):
        if condense.is_coarser_resolution(resolution, condense.DAYS):
            return condense.next_resolution(resolution)
        else:
            return None


class DegreeDayCorrection(DataSeries):
    """
    Data series computing "degree day corrected consumption", based on actual
    consumption, actual degree days, and "standard degree days" to normalise
    against.

    For any requested period, the total consumption is normalised against the
    total number of actual and standard degree days.  In particular, this means
    that partitioning a period and computing corrected consumption for each
    part is unlikely to give results that sum up to the same as the corrected
    consumption for the entire period...

    @note: This is a generalisation of the specification of "monthly corrected
    consumption" and "yearly corrected consumption" --- both defined in terms
    of total consumption and total number of degree days in the periods.

    get_samples() will raise NotImplementedError, as it cannot be
    correctly implemented.
    """
    consumption = models.ForeignKey(
        DataSeries, on_delete=models.PROTECT,
        related_name='degreedayscorrectionconsumption_derivative_set')

    standarddegreedays = models.ForeignKey(
        DataSeries, on_delete=models.PROTECT,
        related_name='degreedayscorrectionstandardegreedays_derivative_set')

    degreedays = models.ForeignKey(
        DataSeries, on_delete=models.PROTECT,
        related_name='degreedayscorrectiondegreedaysn_derivative_set')

    class Meta(DataSeries.Meta):
        app_label = 'measurementpoints'

    def clean(self):
        if self.role is None:
            self.role = DataRoleField.CONSUMPTION
        if self.consumption and \
                self.consumption.role != DataRoleField.CONSUMPTION:
            raise ValidationError('DegreeDayCorrection must apply to a '
                                  'CONSUMPTION data series')
        # will probably need to check for HEATING_XXX or COOLING_XXX, when
        # cooling degree days are introduced (if ever).
        if self.standarddegreedays and \
                self.standarddegreedays.role != \
                DataRoleField.STANDARD_HEATING_DEGREE_DAYS:
            raise ValidationError(
                'standarddegreedays for DegreeDayCorrection '
                'does not have role STANDARD_HEATING_DEGREE_DAYS')
        if self.degreedays and \
                self.degreedays.role != DataRoleField.HEATING_DEGREE_DAYS:
            raise ValidationError(
                'degreedays for DegreeDayCorrection does not '
                'have role HEATING_DEGREE_DAYS')
        return super(DegreeDayCorrection, self).clean()

    def save(self, *args, **kwargs):
        self.clean()
        super(DegreeDayCorrection, self).save(*args, **kwargs)

    def _get_samples(self, from_timestamp, to_timestamp):
        raise NotImplementedError('raw data samples is not well-defined for '
                                  'DegreeDayCorrection')

    @staticmethod
    def _corrected_sample(consumption, standarddegreedays, degreedays):
        """
        "Correct" a single consumption sample wrt. the ratio between the
        specified standarddegreedays and degreedays samples.  If the numeric
        value for standarddegreedays or degreedays is 0, the value in the
        "corrected" sample is the same as in the original.
        """
        samples = [consumption, standarddegreedays, degreedays]
        cachable = any([s.cachable for s in samples])
        extrapolated = any([s.extrapolated for s in samples])

        if not standarddegreedays.physical_quantity or \
                not degreedays.physical_quantity:
            # no "correction" --- but still mark as cachable/not depending on
            # whether the degree days values leading to this are cachable...
            return consumption._replace(
                cachable=cachable,
                extrapolated=extrapolated)

        val = consumption.physical_quantity * \
            standarddegreedays.physical_quantity / degreedays.physical_quantity
        return consumption._replace(
            physical_quantity=val,
            cachable=cachable,
            extrapolated=extrapolated)

    def calculate_development(self, from_timestamp, to_timestamp):
        """
        Calculate corrected development over a period, i.e. "normalise" total
        consumption in period wrt. total degree days in period.
        """
        assert PhysicalQuantity.same_unit(self.unit, self.consumption.unit)
        consumption = self.consumption.subclass_instance.calculate_development(
            from_timestamp, to_timestamp)
        standarddegreedays = \
            self.standarddegreedays.subclass_instance.calculate_development(
                from_timestamp, to_timestamp)
        degreedays = self.degreedays.subclass_instance.calculate_development(
            from_timestamp, to_timestamp)
        if any([s is None
                for s in consumption, standarddegreedays, degreedays]):
            return None

        return self._corrected_sample(
            consumption, standarddegreedays, degreedays)

    def _condense_data_samples_recursive(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        Compute/construct condensed data samples in the specified resoulution,
        based on condensed data from the consumption, standarddegreedays and
        degreedays data series with the same resolution.

        Overrides DataSeries._condense_data_samples_recursive(); used by
        get_condensed_samples().
        """
        assert PhysicalQuantity.same_unit(self.unit, self.consumption.unit)
        consumption = self.consumption.subclass_instance
        consumption_condensed = consumption.get_condensed_samples(
            from_timestamp, sample_resolution, to_timestamp)
        standarddegreedays = self.standarddegreedays.subclass_instance
        standarddegreedays_condensed = \
            standarddegreedays.get_condensed_samples(
                from_timestamp, sample_resolution, to_timestamp)
        degreedays = self.degreedays.subclass_instance
        degreedays_condensed = degreedays.get_condensed_samples(
            from_timestamp, sample_resolution, to_timestamp)

        for consumption, standarddegreedays, degreedays in itertools.izip(
                consumption_condensed, standarddegreedays_condensed,
                degreedays_condensed):
            assert consumption.from_timestamp == \
                standarddegreedays.from_timestamp
            assert standarddegreedays.from_timestamp == \
                degreedays.from_timestamp

            yield self._corrected_sample(
                consumption, standarddegreedays, degreedays)

    def depends_on(self):
        """
        @see L{DataSeries.depends_on()}
        """
        others = [self.consumption.subclass_instance,
                  self.standarddegreedays.subclass_instance,
                  self.degreedays.subclass_instance]
        return others + list(flatten([o.depends_on() for o in others]))
