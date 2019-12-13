# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.utils.iter_ext import pairwise
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import first_last
from gridplatform.utils import condense


def quotient_sequence(nominator_sequence, denominator_sequence):
    nominator_sequence = iter(nominator_sequence)
    denominator_sequence = iter(denominator_sequence)
    while True:
        # Will stop on either input raising StopIteration...
        nominator = next(nominator_sequence)
        denominator = next(denominator_sequence)
        if nominator.from_timestamp != denominator.from_timestamp:
            # Missing entries in either; skip in the other.
            # On missing data, we cannot provide any sensible output.
            while nominator.from_timestamp < denominator.from_timestamp:
                nominator = next(nominator_sequence)
            while denominator.from_timestamp < nominator.from_timestamp:
                denominator = next(denominator_sequence)
        assert nominator.from_timestamp == denominator.from_timestamp
        assert nominator.to_timestamp == denominator.to_timestamp
        if denominator.physical_quantity:
            val = nominator.physical_quantity / denominator.physical_quantity
            yield nominator._replace(physical_quantity=val)
        else:
            # No production but have consumption --- assume that consumption
            # should be taken to contribute to consumption in next period with
            # consumption...  (This is a subtly different scenario with missing
            # data --- on seeing zero production, we assume that energy
            # consumption contributes to later production --- but on missing
            # data, the production is *unknown*, without strong reasons to
            # expect it to actually contribute to production registered
            # later...)
            while not denominator.physical_quantity:
                denominator = next(denominator_sequence)
            lst = [nominator]
            while nominator.from_timestamp < denominator.from_timestamp:
                nominator = next(nominator_sequence)
                if nominator.from_timestamp <= denominator.from_timestamp:
                    lst.append(nominator)
            assert nominator.from_timestamp >= denominator.from_timestamp
            assert nominator.from_timestamp > denominator.from_timestamp or \
                nominator in lst
            total_acc = sum(
                (acc.physical_quantity for acc in lst),
                nominator.physical_quantity * 0)
            val = total_acc / denominator.physical_quantity
            for x in lst:
                yield x._replace(physical_quantity=val)


class VariablyBoundAccumulationMixin(object):
    def calculate_development(self, from_timestamp, to_timestamp):
        """
        Specialisation of ``calculate_development()`` for for variably bound
        accumulation --- where the "default" implementation of getting "raw"
        samples at ``to_timestamp`` and ``from_timestamp`` and subtracting
        fails.
        """
        try:
            first, last = first_last(self.get_samples(
                from_timestamp, to_timestamp))
            return self.create_range_sample(
                from_timestamp, to_timestamp,
                last.physical_quantity - first.physical_quantity,
                uncachable=(
                    first.uncachable or
                    last.uncachable or
                    from_timestamp != first.timestamp or
                    to_timestamp != last.timestamp),
                extrapolated=(
                    first.extrapolated or
                    last.extrapolated or
                    from_timestamp != first.timestamp or
                    to_timestamp != last.timestamp))
        except ValueError:
            # @bug: Bug cammuflaging error handling.
            return self.create_range_sample(
                from_timestamp, to_timestamp,
                PhysicalQuantity(0, self.unit),
                uncachable=True, extrapolated=True)


class CacheOptimizedCalculateDevelopmentMixin(object):
    """
    Implement L{calculate_development()} via multiple calls to
    L{get_condensed_samples()} for clever choises of arguments in order to
    optimize cache utilization.  For ranges where this does not work, we fall
    back to the super class implementation of L{calculate_development} (this
    can be customized in L{_calculate_development_fallback()}.
    """
    @classmethod
    def _period_to_caching_periods(cls, from_timestamp, to_timestamp):
        """
        Translate a time period into a combination of time periods aligned with
        cache resolutions and whatever is left over.
        """
        # (sample_resolution, from_timestamp, to_timestamp) list
        cache_periods = []
        periods_left = [(from_timestamp, to_timestamp)]
        timezone = from_timestamp.tzinfo

        for delta in condense.RESOLUTIONS:
            # nothing, "before", "after", or both (or initial)
            assert len(periods_left) < 3
            new_periods_left = []
            for period_from, period_to in periods_left:
                aligned_from = condense.floor(period_from, delta, timezone)
                if aligned_from < period_from:
                    aligned_from += delta
                aligned_to = condense.floor(period_to, delta, timezone)
                if aligned_from < aligned_to:
                    if period_from < aligned_from:
                        new_periods_left.append((period_from, aligned_from))
                    if aligned_to < period_to:
                        new_periods_left.append((aligned_to, period_to))
                    cache_periods.append((delta, aligned_from, aligned_to))
                else:
                    new_periods_left.append((period_from, period_to))
            periods_left = new_periods_left
        return (cache_periods, periods_left)

    def _calculate_development_fallback(self, from_timestamp, to_timestamp):
        return super(
            CacheOptimizedCalculateDevelopmentMixin,
            self).calculate_development(from_timestamp, to_timestamp)

    def calculate_development(self, from_timestamp, to_timestamp):
        """
        Specialisation of ``calculate_development()``; using cached data for
        computation when possible.
        """
        cache_periods, periods_left = self._period_to_caching_periods(
            from_timestamp, to_timestamp)

        samples = []

        for sample_resolution, period_from, period_to in cache_periods:
            samples.extend(self.get_condensed_samples(
                period_from, sample_resolution, period_to))

        for period_from, period_to in periods_left:
            val = self._calculate_development_fallback(period_from, period_to)
            if val is None:
                return None
            samples.append(val)

        uncachable = False
        extrapolated = False
        val = PhysicalQuantity(0, self.unit)
        for sample in samples:
            uncachable = uncachable or sample.uncachable
            extrapolated = extrapolated or sample.extrapolated
            val += sample.physical_quantity
        return self.create_range_sample(
            from_timestamp, to_timestamp, val, uncachable,
            extrapolated)


class DevelopmentRateComputation(VariablyBoundAccumulationMixin):
    """
    A C{DevelopmentRateComputation} is a mixin class that helps implement
    L{DataSeries.get_samples()} using a formula like M{F(t) =
    S{integral}f(a'(t), r(t)) dt}, where M{F} is the resulting continuous
    accumulation function, M{a'} is the first derivative of a continuous
    accumulation M{a}, M{r} is a piece wise constant rate, M{t} is time and
    M{f} is customized by the child class in the method L{_compute_sample()}.
    """

    def _compute_sample(self, development, rate):
        """
        Abstract method for implementing the M{f} in M{F(t) =
        S{integral}f(a'(t), r(t)) dt}.

        @param development: A PhysicalQuantity equal to M{a(t+S{Delta}) - a(t)}
        for some time M{t}.

        @param rate: A PhysicalQuantity equal to M{r(t')} for all
        M{t'S{isin}[t; t + S{Delta}]}, for the same time M{t}.

        @return: A PhysicalQuantity equal to M{S{integral}f(a'(t'), r(t')) dt'}
        where M{t'} runs from M{t} to M{t+S{Delta}}.
        """
        raise NotImplementedError()

    def _get_accumulation(self):
        """
        Abstract method returning the L{DataSeries} defining M{a} in M{F(t) =
        S{integral}f(a'(t), r(t)) dt}.
        """
        raise NotImplementedError()

    def _get_rate(self):
        """
        Abstract method returning the L{DataSeries} defining M{r} in M{F(t) =
        S{integral}f(a'(t), r(t)) dt}.
        """
        raise NotImplementedError()

    def _get_samples(self, from_timestamp, to_timestamp):
        """
        C{DevelopmentRateComputation} implementation of
        L{DataSeries.get_raw_data_samples()}.

        @precondition: The abstract methods L{_compute_sample()},
        L{_get_accumulation()}, L{_get_rate()} must all be implemented.

        @bug: First sample appears to be skipped when entering domain.
        """
        assert from_timestamp <= to_timestamp
        assert self._get_accumulation().is_accumulation()
        assert self.is_accumulation()

        raw_accumulation = pairwise(
            self._get_accumulation_samples(from_timestamp, to_timestamp))
        raw_rate = self._get_rate_samples(from_timestamp, to_timestamp)

        # Algorithm:
        #
        # The loop variable r spans a window of the rate.
        #
        # The loop variable pair (c0, c1) defines a window of the accumulation,
        # inside which we may interpolate the accumulation, conviniently bound
        # to the name c.
        #
        # The algorithm alternates between moving one of these two windows
        # forwards, such that there is an overlap at all times.  The algorithm
        # does not assume one window needs to move more often than the other.
        #
        # c and old_c are chosen s.t. they are both included in the rate window
        # as well as the accumulation window.
        INITIAL_ACCUMULATED_RESULT = PhysicalQuantity(
            0, self.unit)

        accumulated_result = INITIAL_ACCUMULATED_RESULT

        # To make it possible to yield the initial sample, we track if any
        # samples has been yielded.
        sample_yielded = False

        try:
            c0, c1 = next(raw_accumulation)

            for r in raw_rate:
                while c1.timestamp < r.from_timestamp:
                    c0, c1 = next(raw_accumulation)

                assert r.from_timestamp <= c1.timestamp
                accumulation_start = self._get_accumulation().\
                    _interpolate_extrapolate_sample(
                        max(r.from_timestamp, c0.timestamp),
                        data_before=c0, data_after=c1)
                assert accumulation_start.timestamp == max(
                    r.from_timestamp, c0.timestamp)

                while c1.timestamp < r.to_timestamp:
                    c0, c1 = next(raw_accumulation)

                assert c0.timestamp <= r.to_timestamp <= c1.timestamp
                accumulation_end = self._get_accumulation().\
                    _interpolate_extrapolate_sample(
                        r.to_timestamp, data_before=c0, data_after=c1)
                assert accumulation_end.timestamp == r.to_timestamp

                accumulated_result += self._compute_sample(
                    accumulation_end.physical_quantity -
                    accumulation_start.physical_quantity,
                    r.physical_quantity)

                sample = self.create_point_sample(
                    r.to_timestamp,
                    accumulated_result,
                    uncachable=(
                        r.uncachable or
                        accumulation_start.uncachable or
                        accumulation_end.uncachable),
                    extrapolated=(
                        r.extrapolated or
                        accumulation_start.extrapolated or
                        accumulation_end.extrapolated))

                if not sample_yielded and sample.timestamp != from_timestamp:
                    # yield a sample at from_timestamp, possibly extrapolated.
                    yield self.create_point_sample(
                        from_timestamp,
                        INITIAL_ACCUMULATED_RESULT,
                        uncachable=sample.uncachable or (
                            max(r.from_timestamp,
                                accumulation_start.timestamp) !=
                            from_timestamp),
                        extrapolated=sample.extrapolated or (
                            max(r.from_timestamp,
                                accumulation_start.timestamp) !=
                            from_timestamp))

                    if max(r.from_timestamp, accumulation_start.timestamp) != \
                            from_timestamp:
                        # if the from_timestamp sample was extrapolated, the
                        # first unextrapolated sample also needs to be
                        # yielded.
                        yield self.create_point_sample(
                            max(r.from_timestamp,
                                accumulation_start.timestamp),
                            INITIAL_ACCUMULATED_RESULT,
                            uncachable=(
                                sample.uncachable or
                                accumulation_start.uncachable),
                            extrapolated=(
                                sample.extrapolated or
                                accumulation_start.extrapolated))

                sample_yielded = True
                yield sample

            # Ensure post-condition
            if sample_yielded and sample.timestamp != to_timestamp:
                yield self.create_point_sample(
                    to_timestamp,
                    sample.physical_quantity,
                    uncachable=True, extrapolated=True)

        finally:
            if not sample_yielded:
                yield self.create_point_sample(
                    from_timestamp,
                    INITIAL_ACCUMULATED_RESULT,
                    uncachable=True, extrapolated=True)
                yield self.create_point_sample(
                    to_timestamp,
                    self._compute_sample(
                        PhysicalQuantity(0, self._get_accumulation().unit),
                        PhysicalQuantity(
                            0, self._get_rate().unit)),
                    uncachable=True, extrapolated=True)

    def get_underlying_function(self):
        """
        C{DevelopmentRateComputation} override of
        L{DataSeries.get_underlying_function()}.
        """
        return self.CONTINUOUS_ACCUMULATION

    def _get_accumulation_samples(self, from_timestamp, to_timestamp):
        """
        Get accumulation samples for the given M{[C{from_timestamp},
        {to_timestamp}]} interval.
        """
        return self._get_accumulation().subclass_instance.get_samples(
            from_timestamp, to_timestamp)

    def _get_rate_samples(self, from_timestamp, to_timestamp):
        """
        Get rate samples for the given M{[C{from_timestamp}, {to_timestamp}]}
        interval.
        """
        return self._get_rate().subclass_instance.get_samples(
            from_timestamp, to_timestamp)

    # subclasses must define this constant on their own.
    RATE_RESOLUTION = None

    def get_recursive_condense_resolution(self, resolution):
        """
        Must recurse through as many resolutions as required to reach
        C{RATE_RESOLUTION}. resolutions below C{RATE_RESOLUTION} will not be
        reached through recursion, unless requested directly.
        """
        return condense.next_resolution(resolution)

    def _condense_data_samples_recursive(
            self, from_timestamp, resolution, to_timestamp):
        assert self.RATE_RESOLUTION is not None
        if resolution == self.RATE_RESOLUTION:
            ZERO = PhysicalQuantity(0, self.unit)
            developments = self._get_accumulation().get_condensed_samples(
                from_timestamp, resolution, to_timestamp)
            rates = iter(
                self._get_rate().get_samples(
                    from_timestamp, to_timestamp))
            rate = next(rates, None)
            for development in developments:
                while rate is not None and \
                        rate.to_timestamp <= development.from_timestamp:
                    rate = next(rates, None)
                if rate is not None and \
                        rate.from_timestamp <= development.from_timestamp and \
                        rate.to_timestamp >= development.to_timestamp:

                    yield self.create_range_sample(
                        development.from_timestamp,
                        development.to_timestamp,
                        self._compute_sample(
                            development.physical_quantity,
                            rate.physical_quantity),
                        uncachable=not (
                            rate.cachable and development.cachable),
                        extrapolated=(
                            rate.extrapolated or development.extrapolated))

                    # rates may be longer than development, and therefore
                    # should only be next()'ed when the last valid subinterval
                    # has been processed with the corresponding development.
                    if rate.to_timestamp == development.to_timestamp:
                        rate = next(rates, None)
                        assert rate is None or rate.from_timestamp + resolution <= \
                            rate.to_timestamp
                else:
                    yield self.create_range_sample(
                        development.from_timestamp,
                        development.to_timestamp,
                        ZERO,
                        uncachable=True,
                        extrapolated=True)
        else:
            condensations = super(DevelopmentRateComputation, self).\
                _condense_data_samples_recursive(from_timestamp,
                                                 resolution, to_timestamp)
            for sample in condensations:
                yield sample


class ENPIMixin(object):
    """
    An ENPI (Energy Performance Indicator) is the energy consumption (or other
    kind of consumption) per unit of energy driver.

    A typical example is the energy consumption of some production facility
    with the count of products produced as the energy driver.

    What makes an ENPI a performance indicator is that ENPI values across
    different intervals can be compared.  For example 3.2 kWh/pcs last month is
    comparable with 3.1 kWh/pcs yesterday.

    For the ENPI to be statistically significant, it should be calculated
    across intervals with a statistically significant energy driver
    developments.  It is up to the user to assess statistical significance.
    """

    def _condense_energy_drivers(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        Condense energy drivers between C{from_timestamp} and C{to_timestamp}
        with C{sample_resolution}.

        This method is abstract and required by
        L{ENPIMixin._condense_data_samples_recursive()}

        This method implements the same interface as
        L{DataSeries.get_condensed_samples()}.

        @return: Returns an iterable of ranged samples.
        """
        raise NotImplementedError(
            '%r did not implement this method' % self.__class__)

    def _condense_energy_consumption(self, from_timestamp, sample_resolution,
                                     to_timestamp):
        """
        Condense energy consumption between C{from_timestamp} and
        C{to_timestamp} with C{sample_resolution}.

        This method is abstract and required by
        L{ENPIMixin._condense_data_samples_recursive()}

        This method implements the same interface as
        L{DataSeries.get_condensed_samples()}.

        @return: Returns an iterable of ranged samples.
        """
        raise NotImplementedError(
            '%r did not implement this method' % self.__class__)

    def _condense_data_samples_recursive(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        C{ENPIMixin} override of
        L{DataSeries._condense_data_samples_recursive}.

        Yields ranged samples of ENPI across the interval represented by the
        range, or, if necessary across a containing interval.

        By definition all energy consumption is a contribution to the ENPI
        yielded by the next energy driver development.  For periods without
        energy driver development, the energy consumption is therefore saved up
        and added to the energy consumption of the following period.  This will
        by definition only happen when condensing for periods that are
        statistically insignificant.

        @precondition: C{self._condense_energy_drivers()} and
        C{self._condense_energy_consumption()} must both be implemented.
        """
        return quotient_sequence(
            self._condense_energy_consumption(
                from_timestamp, sample_resolution, to_timestamp),
            self._condense_energy_drivers(
                from_timestamp, sample_resolution, to_timestamp))

    def _calculate_energy_development(self, from_timestamp, to_timestamp):
        """
        Calculate energy development between C{from_timestamp} and
        C{to_timestamp}.

        This method is abstract and required by L{calculate_enpi()}.

        @return: Returns a ranged sample.
        """
        raise NotImplementedError(
            '%r did not implement this method' % self.__class__)

    def _calculate_energy_driver_development(
            self, from_timestamp, to_timestamp):
        """
        Calculate energy driver development between C{from_timestamp} and
        C{to_timestamp}.

        This method is abstract and required by L{calculate_enpi()}.

        @return: Returns a ranged sample.
        """
        raise NotImplementedError(
            '%r did not implement this method' % self.__class__)

    def calculate_enpi(self, from_timestamp, to_timestamp):
        """
        Calculate the ENPI between C{from_timestamp} and C{to_timestamp}.

        @return: Returns a ranged sample holding the ENPI between
        C{from_timestamp} and C{to_timestamp}, or None if the ENPI for the
        given range is not well-defined.

        @precondition: C{self._calculate_energy_development()} and
        C{self._calculate_energy_driver_development()} are both implemented.
        """
        energy_sample = self._calculate_energy_development(
            from_timestamp, to_timestamp)

        energy_driver_sample = self._calculate_energy_driver_development(
            from_timestamp, to_timestamp)

        if energy_sample is not None and energy_driver_sample:
            return self.create_range_sample(
                from_timestamp,
                to_timestamp,
                physical_quantity=(
                    energy_sample.physical_quantity /
                    energy_driver_sample.physical_quantity),
                uncachable=True,
                extrapolated=True)
        else:
            return None
