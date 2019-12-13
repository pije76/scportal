# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Data Series
==========

    This module defines L{DataSeries} as the base model for all data series.

    Interdependencies
    -----------------

        L{DataSeries} may be defined in terms of other L{DataSeries}, thus
        creating a dependency releation, forming a directed, acyclic dependency
        graph among L{DataSeries}.  Various operations require traversing this
        dependency graph following the dependencies in one direction or the
        other.

        To avoid infinite recursion, circular dependencies are not
        allowed, i.e. no L{DataSeries} that this particular L{DataSeries}
        depends on is allowed to depend on this particular L{DataSeries}.  See
        the L{DataSeries.depends_on()} method.
"""

from fractions import Fraction
import itertools
from operator import attrgetter

from django.db import models
from django.db.models.query_utils import Q
from django.db.models.query import DateQuerySet
from django.db.models.query import DateTimeQuerySet
from django.db.models.query import ValuesListQuerySet
from django.db.models.query import ValuesQuerySet
from django.utils.translation import ugettext_lazy as _

from gridplatform.customers.models import Customer
from gridplatform.encryption.managers import DecryptingManager
from gridplatform.encryption.managers import DecryptingQuerySet
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_provider_id
from gridplatform.trackuser import get_user
from gridplatform.trackuser.managers import FilteringQuerySetMixinBase
from gridplatform.utils import condense
from gridplatform.utils import utilitytypes
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.iter_ext import count_extended
from gridplatform.utils.iter_ext import pairwise
from gridplatform.utils.iter_ext import pairwise_extended
from gridplatform.utils.models import StoreSubclass
from gridplatform.utils.models import StoredSubclassManager
from gridplatform.utils.samples import Sample
from gridplatform.utils.unitconversion import PhysicalQuantity
from legacy.legacy_utils.preferredunits import get_preferred_unit_converter

from ..fields import DataRoleField
from .graph import Graph


class UndefinedSamples(Exception):
    """
    Exception raised when samples are supposed to be undefined, even inside the
    domain of a L{DataSeries}.

    Some DataSeries are interval aggregates of other DataSeries.  These may not
    be well-defined if the requested period is odd-ended or too short: For
    instance if the aggregate is something pr. day and the requested period
    starts and/or ends at something different than a midnight or only spans a
    few hours.

    @seealso: L{HeatingDegreeDays} and L{MeanTemperatureChange}.
    """
    pass


class DataSeriesQuerySetMixin(FilteringQuerySetMixinBase):
    """
    QuerySet limiting result set according to whether the current user is
    allowed to see the customer with specified ID.
    """

    def _apply_filtering(self):
        user = get_user()
        if user is None:
            return
        if not user.is_authenticated():
            self.query.set_empty()
            return
        customer = get_customer()
        ACCEPTABLE_CUSTOMER_IS_NULL_INDEX_ROLES = [
            DataRoleField.ELECTRICITY_TARIFF,
            DataRoleField.CO2_QUOTIENT,
        ]
        if customer is not None:
            if not customer.is_active:
                self.query.set_empty()
                return
            id_field = '{}_id'.format(self._filter_field)
            kwargs = {id_field: customer.id}
            self.query.add_q(Q(**kwargs) | Q(**{
                '{}__isnull'.format(id_field): True,
                'role__in': ACCEPTABLE_CUSTOMER_IS_NULL_INDEX_ROLES,
            }))
            return
        provider_id = get_provider_id()
        if provider_id:
            provider_id_field = '{}__provider_id'.format(self._filter_field)
            kwargs = {provider_id_field: provider_id}
            self.query.add_q(Q(**kwargs) | Q(**{
                '{}__isnull'.format(provider_id_field): True,
                'role__in': ACCEPTABLE_CUSTOMER_IS_NULL_INDEX_ROLES,
            }))
            return
        assert user.is_staff, \
            'non-staff user {} without customer or provider; ' + \
            'should not exist'.format(user.id)
        return


class DataSeriesManager(DecryptingManager, StoredSubclassManager):
    _field = 'customer'
    use_for_related_fields = True

    class _QuerySet(DataSeriesQuerySetMixin, DecryptingQuerySet):
        pass

    class _ValuesQuerySet(DataSeriesQuerySetMixin, ValuesQuerySet):
        pass

    class _ValuesListQuerySet(DataSeriesQuerySetMixin, ValuesListQuerySet):
        pass

    class _DateQuerySet(DataSeriesQuerySetMixin, DateQuerySet):
        pass

    class _DateTimeQuerySet(DataSeriesQuerySetMixin, DateTimeQuerySet):
        pass

    def get_queryset(self):
        qs = super(DataSeriesManager, self).get_queryset()
        kwargs = {
            'klass': self._QuerySet,
            '_filter_field': self._field,
            '_ValuesQuerySet': self._ValuesQuerySet,
            '_ValuesListQuerySet': self._ValuesListQuerySet,
            '_DateQuerySet': self._DateQuerySet,
            '_DateTimeQuerySet': self._DateTimeQuerySet,
        }
        return qs._clone(**kwargs)


class DataSeriesBase(models.Model):
    objects = DataSeriesManager()

    class Meta:
        abstract = True


class DataSeries(DataSeriesBase, StoreSubclass):
    """
    A C{DataSeries} samples an underlying function.  Knowing this
    underlying function is important when interpreting and visualizing
    these data.

    For instance, if the C{DataSeries} samples an accumulation, you
    will usually want to compare the destilled development of the
    sample values inside a number of similar periods.  If the data
    series, on the other hand, samples a rate, it is easy to visualize
    even large sets of undestiled sequential data; for instance with
    upper and lower bounds graphs.

    Also, there exist many techniques for interpolating U{continuous
    functions<http://mathworld.wolfram.com/ContinuousFunction.html>},
    such as U{linear
    interpolation<http://en.wikipedia.org/wiki/Linear_interpolation>}.
    For discontinuous functions, however, these techniques do not
    apply.  Specifically, we will often meet the piecewise constant
    function, where each sample represent the constant value since the
    previous sample (discrete states, mean values and so on).

    @cvar PIECEWISE_CONSTANT_ACCUMULATION: Piecewise constant
    accumulation.  For example accumulated unit production count.

    @cvar PIECEWISE_CONSTANT_RATE: Piecewise constant rate.  For
    example mean power.

    @cvar CONTINUOUS_ACCUMULATION: Continuous accumulation.  For
    example accumulated energy consumption.

    @cvar CONTINUOUS_RATE: Continuous rate. For example power,
    temperature, frequency or current.

    @cvar INTERVAL_FUNCTION: Interval function, i.e. a function that is
    computed across time intervals and not for any particular point in time;
    i.e. a function that is only well-defined when condensed.

    @ivar role: The role of this C{DataSeries} object.

    @ivar graph: The graph that this C{DataSeries} belongs to.  This
    may be NULL for C{DataSeries} such as L{Index} (it may still be
    rendered to a graph, but its main purpose is not to be drawn on
    any graph in particular).

    @ivar customer: A customer which the C{DataSeries} belongs to, if null it's
    a global C{DataSeries} (e.g. a spot tariff or similar).

    @ivar utility_type: The type of resource that this C{DataSeries} is
    related to.  For non-L{Index} C{DataSeries}, C{utility_type} is genericly
    available through C{graph__collection__resource__type}.  I.e. moving the
    field to the L{Index} class would make it impossible to query for all
    DataSeries with a given resource type (and once you figure out how to do
    that anyway, feel free to move the C{utility_type} field to the L{Index}
    class.

    You can collect data for similar aspects of different resources, for
    instance energy consumption on both ELECTRICITY and DISTRICT_HEATING, cost
    on everything and temperature in a DISTRICT_HEATING installation.  but also
    just room temperature, which is not related to any resource type in
    particular, i.e. UNKNOWN.
    """
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT,
                                 blank=True, null=True, default=get_customer)
    role = DataRoleField()

    graph = models.ForeignKey(Graph, on_delete=models.CASCADE,
                              null=True, blank=True)

    unit = BuckinghamField(blank=True)

    utility_type = models.IntegerField(
        _('utility type'), choices=utilitytypes.OPTIONAL_METER_CHOICES)

    PIECEWISE_CONSTANT_ACCUMULATION = 0
    PIECEWISE_CONSTANT_RATE = 1
    CONTINUOUS_ACCUMULATION = 2
    CONTINUOUS_RATE = 3
    INTERVAL_FUNCTION = 4

    UNDERLYING_FUNCTION_CHOICES = (
        (PIECEWISE_CONSTANT_ACCUMULATION,
         _(u"Piecewise constant accumulation")),
        (PIECEWISE_CONSTANT_RATE,
         _(u"Piecewise constant rate")),
        (CONTINUOUS_ACCUMULATION,
         _(u"Continuous accumulation")),
        (CONTINUOUS_RATE,
         _(u"Continuous rate")),
        (INTERVAL_FUNCTION,
         _(u'Interval function')),
    )

    class Meta(StoreSubclass.Meta):
        verbose_name = _('dataseries')
        verbose_name_plural = _('dataseries')
        ordering = ['role', 'id']
        app_label = 'measurementpoints'

    _exclude_field_from_validation = []

    def __unicode__(self):
        if self.subclass.model_class() != self.__class__:
            # This operator is used for ModelChoiceFields, where the queryset
            # does not return concrete instances, but only raw DataSeries
            # instances.  If so, delegate to the subclass_instance.
            return unicode(self.subclass_instance)
        elif self.graph and self.graph.collection and self.customer:
            # This is the default implementation for all subclasses.
            return u'{collection_name} -- {role} ({unit})'.format(
                collection_name=self.graph.collection.name_plain,
                role=self.get_role_display(),
                unit=self.get_preferred_unit_converter().get_display_unit())
        else:
            return self.get_role_display()

    def get_encryption_id(self):
        return (Customer, self.customer_id)

    def get_samples(self, from_timestamp, to_timestamp):
        """
        Yields (or returns a list of) raw samples covering the interval
        M{[C{from_timestamp}; C{to_timestamp}]}.

        Subclasses that don't store their data directly as StoredData, should
        reimplement the C{_get_samples()} method.

        @precondition: C{from_timestamp <= to_timestamp}

        @postcondition: For rates, both end-points are included if possible
        through interpolation.  If insufficient data is available, nothing is
        yielded/the empty list is returned.

        @postcondition: For accumulations, both end-points are included
        (possibly using interpolation or extrapolation).  If insufficient data
        is available, nothing is yielded/the empty list is returned.

        @postcondition: All yielded samples are contained within the interval.

        @postcondition: Each sample yielded represent time after the previously
        yielded sample.

        @raise UndefinedSamples: If subclass is not supposed to be defined for
        the particular combination of C{from_timestamp} and C{to_timestamp}.
        """
        assert from_timestamp <= to_timestamp

        if self.get_underlying_function() == self.INTERVAL_FUNCTION:
            raise UndefinedSamples(
                'Raw samples for interval functions are not well-defined.')

        first_sample = None
        final_sample = None
        previous_timestamp = None
        for sample in self.subclass_instance._get_samples(
                from_timestamp, to_timestamp):
            assert isinstance(sample, Sample), \
                '%r is not an instance of Sample (self.__class__ == %s)' % (
                    sample, self.__class__)
            if first_sample is None:
                first_sample = sample
            elif sample.is_point:
                assert previous_timestamp < sample.timestamp
            elif sample.is_range:
                assert previous_timestamp <= sample.from_timestamp

            final_sample = sample
            assert from_timestamp <= sample.from_timestamp, \
                '%r > %r (self.__class__ == %s)' % (
                    from_timestamp, sample.from_timestamp, self.__class__)
            assert to_timestamp >= sample.to_timestamp, \
                '%r < %r (self.__class__ == %s)' % (
                    to_timestamp, sample.to_timestamp, self.__class__)
            yield sample

            previous_timestamp = sample.to_timestamp

        if self.is_rate() and first_sample is not None and \
                final_sample is not None:
            assert not first_sample.extrapolated, str(self.__class__)
            assert not final_sample.extrapolated, str(self.__class__)

        if self.is_accumulation():
            if first_sample is not None and final_sample is not None:
                assert first_sample.from_timestamp == from_timestamp, str(
                    self.__class__)
                assert final_sample.to_timestamp == to_timestamp, str(
                    self.__class__)

    def _get_samples(self, from_timestamp, to_timestamp):
        """
        Yields (or returns a list of) raw samples covering the interval
        M{[C{from_timestamp}; C{to_timestamp}]}.

        Subclasses that don't store their data directly as StoredData, should
        reimplement this method.

        @precondition: C{from_timestamp <= to_timestamp}

        @postcondition: For rates, both end-points are included if possible
        through interpolation.  If insufficient data is available, nothing is
        yielded/the empty list is returned.

        @postcondition: For accumulations, both end-points are included
        (possibly using interpolation or extrapolation).  If insufficient data
        is available, nothing is yielded/the empty list is returned.

        @postcondition: All yielded samples are contained within the interval.

        @note: The returned samples will be in the time interval
        M{[C{from_timestamp}, C{to_timestamp}]}, where C{from_timestamp} and
        C{to_timestamp} will be linear interpolation values if enough data is
        available.
        """
        assert from_timestamp <= to_timestamp
        if self.__class__ != self.subclass.model_class():
            return self.subclass_instance.get_samples(
                from_timestamp, to_timestamp)

        tz = from_timestamp.tzinfo

        if self.is_continuous():
            dataset = list(self.stored_data.filter(
                timestamp__gte=from_timestamp,
                timestamp__lte=to_timestamp).
                order_by('timestamp'))

            result = [
                self.create_point_sample(
                    data.timestamp,
                    PhysicalQuantity(data.value, self.unit))
                for data in dataset]

            # result may be empty if nothing is found in range. Extrapolation
            # is necessary anyway.
            if result:
                if result[0].from_timestamp != from_timestamp:
                    first_sample = self._interpolate_extrapolate_sample(
                        from_timestamp, data_after=dataset[0])
                    if self.is_accumulation() or not first_sample.extrapolated:
                        result.insert(0, first_sample)
                if result[-1].to_timestamp != to_timestamp:
                    end_sample = self._interpolate_extrapolate_sample(
                        to_timestamp, data_before=dataset[-1])
                    if self.is_accumulation() or not end_sample.extrapolated:
                        result.append(end_sample)
            else:
                first_sample = self._interpolate_extrapolate_sample(
                    from_timestamp)
                if first_sample is None or (self.is_rate() and
                                            first_sample.extrapolated):
                    return []
                elif from_timestamp == to_timestamp:
                    return [first_sample]
                else:
                    end_sample = self._interpolate_extrapolate_sample(
                        to_timestamp)
                    return [first_sample, end_sample]

            # Check post-condition
            if self.is_accumulation():
                assert result == [] or \
                    result[0].from_timestamp == from_timestamp
                assert result == [] or result[-1].to_timestamp == to_timestamp

            return result
        else:
            result = []

            # RangeSamples are stored as (from_timestamp, value), with
            # to_timestamp being the timestamp of the next stored data.
            # Therefore we need to consider the most recent StoredData before
            # the (from_timestamp, to_timestamp) range.
            try:
                first_sample = [
                    self.stored_data.filter(timestamp__lte=from_timestamp).
                    order_by('-timestamp').
                    values_list('timestamp', 'value')[0]]
            except IndexError:
                first_sample = []

            stored_data = first_sample + \
                list(self.stored_data.filter(
                    timestamp__gt=from_timestamp,
                    timestamp__lt=to_timestamp).
                    order_by('timestamp').
                    values_list('timestamp', 'value'))

            for current_data, next_data in pairwise_extended(stored_data):
                if next_data:
                    assert current_data[0] < next_data[0], \
                        'unexpected range for sample (%r < %r)' % \
                        (current_data[0], next_data[0])
                    result.append(
                        self.create_range_sample(
                            tz.normalize(
                                max(from_timestamp,
                                    current_data[0]).astimezone(tz)),
                            tz.normalize(next_data[0]).astimezone(tz),
                            PhysicalQuantity(current_data[1], self.unit)))
                else:
                    assert current_data[0] < to_timestamp
                    result.append(
                        self.create_range_sample(
                            tz.normalize(
                                max(from_timestamp,
                                    current_data[0])).astimezone(tz),
                            tz.normalize(to_timestamp).astimezone(tz),
                            PhysicalQuantity(current_data[1], self.unit)))

                # Check post-condition
                assert result[-1].from_timestamp >= from_timestamp
                assert result[-1].to_timestamp <= to_timestamp

            # Check post-condition
            if self.is_accumulation():
                assert result == [] or \
                    result[0].from_timestamp == from_timestamp
                assert result == [] or result[-1].to_timestamp == to_timestamp

            return result

    def get_condensed_samples(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        Get list of L{Sample}s defined by this C{DataSeries}.

        If the underlying function is a continuous rate the
        samples will have a given symbolic timespan distance.
        Otherwise the samples will cover intervals with the given
        symbolic timespan (not quite the same)

        @param from_timestamp: The earliest time used in the returned samples.

        @param sample_resolution: A L{RelativeTimeDelta} that define the sample
        resolution.

        @param to_timestamp: The final time included in the samples.

        @return: Returns an list of point L{Sample}s if the underlying function
        is a continuous rate.  Otherwise a list of ranged L{Sample} is
        returned.

        @see: L{_get_condensed_samples}.

        @precondition: C{from_timestamp == condense.floor(
        from_timestamp, sample_resolution, from_timestamp.tzinfo)}

        @precondition: C{to_timestamp == condense.floor(
        to_timestamp, sample_resolution, to_timestamp.tzinfo)}

        @precondition: C{from_timestamp.tzinfo is not None}

        @precondition: C{to_timestamp.tzinfo is not None}

        @precondition: C{sample_resolution in condense.RESOLUTIONS}
        """
        assert from_timestamp.tzinfo is not None
        assert to_timestamp.tzinfo is not None
        timezone = from_timestamp.tzinfo

        assert from_timestamp == condense.floor(
            from_timestamp, sample_resolution, timezone), \
            'from_timestamp=%r != ' \
            'floor(from_timestamp, sample_resolution=%r, timezone=%r)=%r' % (
                from_timestamp, sample_resolution, timezone, condense.floor(
                    from_timestamp, sample_resolution, timezone))

        assert to_timestamp == condense.floor(
            to_timestamp, sample_resolution, timezone)

        assert sample_resolution in condense.RESOLUTIONS

        for sample in self.subclass_instance._get_condensed_samples(
                from_timestamp, sample_resolution, to_timestamp):
            assert from_timestamp <= sample.from_timestamp, \
                'error in %s: from_timestamp = %r > sample.from_timestamp = %r ' \
                '(sample resolution = %s)' % (
                    self.subclass_instance.__class__,
                    from_timestamp, sample.from_timestamp, sample_resolution)

            assert sample.to_timestamp <= to_timestamp
            yield sample

    def _get_condensed_samples(
            self, from_timestamp, sample_resolution, to_timestamp):
        data_samples = self._condense_data_samples_recursive(
            from_timestamp, sample_resolution, to_timestamp=to_timestamp)
        next_timestamp = from_timestamp
        for sample_a, sample_b in pairwise_extended(data_samples):
            if sample_b is None:
                yield sample_a
            else:
                while next_timestamp < sample_a.from_timestamp:
                    next_timestamp += sample_resolution
                while sample_a.from_timestamp <= next_timestamp < \
                        sample_b.from_timestamp:
                    if sample_a.from_timestamp == next_timestamp:
                        yield sample_a
                    elif sample_a.is_point and sample_b.is_point:
                        yield self._interpolate_extrapolate_sample(
                            next_timestamp, sample_a, sample_b)
                    next_timestamp += sample_resolution

    def _condense_accumulation_data_samples(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        Condense accumulation data samples within an interval defined by
        C{from_timestamp; to_timestamp]}, with C{sample_resolution} as the
        given resolution.

        Yields condensed range samples.
        """
        def resolution_aligned_acc():
            # convert the sequence of "raw" samples from
            # get_samples() to a sequence of samples aligned to
            # the requested sample_resolution
            raw_accumulation = \
                self.get_samples(from_timestamp, to_timestamp)
            next_timestamp = from_timestamp
            for sample1, sample2 in pairwise(raw_accumulation):
                while sample1.timestamp <= next_timestamp <= \
                        sample2.timestamp:
                    yield self._interpolate_extrapolate_sample(
                        next_timestamp,
                        data_before=sample1, data_after=sample2)
                    next_timestamp += sample_resolution

        for range_begin, range_end in pairwise(
                resolution_aligned_acc()):
            assert range_begin.timestamp >= from_timestamp
            assert range_end.timestamp <= to_timestamp
            yield self.create_range_sample(
                range_begin.timestamp,
                range_end.timestamp,
                range_end.physical_quantity -
                range_begin.physical_quantity,
                uncachable=(range_begin.uncachable or
                            range_end.uncachable),
                extrapolated=(range_begin.extrapolated or
                              range_end.extrapolated))

    def _condense_rate_data_samples(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        Rate specific L{get_condensed_samples()} implementation.
        Arguments are the same (or left out).

        Splits the multiframe ranged rate sample into smaller ranged rate
        samples (C{sample_slices}) that fit inside each requested sample frame.
        While this is visually redundant, it supports caching performance (or
        at least is intended to).

        @return: Returns a list of samples.  For each frame (of length
        C{sample_resolution}) the minimum and maximum samples are included in
        the result.

        @postcondition: The samples in the returned list are ordered by their
        timestamps.

        @precondition: C{self.is_rate()} returns C{True}.
        """
        assert self.is_rate()

        raw_data_samples = list(self.get_samples(from_timestamp, to_timestamp))

        if not raw_data_samples:
            # short-circuit: absolutely no values in this data series.
            return []

        result = []
        next_time = from_timestamp + sample_resolution
        minimum_sample = None
        maximum_sample = None

        def flush_min_max():
            if minimum_sample is not None and maximum_sample is not None:
                if minimum_sample.to_timestamp < maximum_sample.to_timestamp:
                    result.extend([minimum_sample, maximum_sample])
                elif minimum_sample == maximum_sample:
                    result.append(minimum_sample)
                else:
                    assert minimum_sample.to_timestamp > \
                        maximum_sample.to_timestamp
                    result.extend([maximum_sample, minimum_sample])
                return (None, None)
            return (minimum_sample, maximum_sample)

        def update_min_max():
            # work-around while we wait for 'nonlocal' Python 3 keyword
            r1 = minimum_sample
            r2 = maximum_sample
            if minimum_sample is None or \
                    minimum_sample.physical_quantity > \
                    sample.physical_quantity:
                r1 = sample
            if maximum_sample is None or \
                    maximum_sample.physical_quantity < \
                    sample.physical_quantity:
                r2 = sample
            return (r1, r2)

        for sample in raw_data_samples:
            if sample.uncachable:
                # don't condense using uncachable samples (end-points are
                # included after this loop).
                continue

            flush = False
            sample_slices = []

            if sample.is_range and \
                    sample.from_timestamp < next_time and\
                    sample.to_timestamp > next_time:
                sample_slices.append(sample._replace(to_timestamp=next_time))

            while sample.to_timestamp > next_time:
                flush = True
                if sample.is_range and not sample.in_closed_interval(
                        next_time, next_time + sample_resolution) and \
                        sample.from_timestamp < next_time + sample_resolution:
                    assert max(next_time, sample.from_timestamp) < min(
                        next_time + sample_resolution, sample.to_timestamp), \
                        'next_time=%r, sample=%r, sample_resolution=%r' % (
                            next_time, sample, sample_resolution)
                    sample_slices.append(sample._replace(
                        from_timestamp=max(next_time, sample.from_timestamp),
                        to_timestamp=min(
                            next_time + sample_resolution,
                            sample.to_timestamp)))
                next_time += sample_resolution

            if sample_slices:
                assert len(sample_slices) >= 2
                assert flush
                sample = sample_slices[0]
                minimum_sample, maximum_sample = update_min_max()
                minimum_sample, maximum_sample = flush_min_max()
                result.extend(sample_slices[1:-1])
                sample = sample_slices[-1]
            elif flush:
                minimum_sample, maximum_sample = flush_min_max()

            minimum_sample, maximum_sample = update_min_max()

        minimum_sample, maximum_sample = flush_min_max()

        return result

    def get_recursive_condense_resolution(self, resolution):
        """
        Get the recursive condense resolution for the given C{resolution}.

        @return: A resolution to be used for condensing C{resolution}
        recursively or C{None}.  If C{None} is returned, condensation for the
        given resolution will not be calculated recursively.

        This method is abstract so subclasses must implement it.  The following
        implementation would work for most DataSeries specializations.  However
        it would often be verry inefficient for small condense resolutions,
        which is why it is not the default::

            def get_recursive_condense_resolution(self, resolution):
                return condense.next_resolution(resolution)

        @see L{condense.next_resolution()}
        """
        raise NotImplementedError(
            "%s did't implement this method" % self.__class__)

    def _condense_data_samples_recursive(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        Method with similar arguments and result as
        L{get_condensed_samples()}, but intended for being implemented in
        L{DataSeries} specializations that wish to utilize the implicit caching
        implemented in L{DataSeries.get_condensed_samples()}.

        Not intended to be called from outside
        L{DataSeries.get_condensed_samples()}, except for testing of the
        concrete C{_condense_data_samples_recursive()} implementation.
        """
        timezone = from_timestamp.tzinfo
        assert from_timestamp == condense.floor(
            from_timestamp, sample_resolution, timezone)
        to_timestamp = condense.floor(
            to_timestamp, sample_resolution, timezone)

        refined_resolution = self.get_recursive_condense_resolution(
            sample_resolution)

        if refined_resolution is None:
            if self.is_accumulation():
                condensed_samples = self._condense_accumulation_data_samples(
                    from_timestamp, sample_resolution, to_timestamp)
            else:
                assert self.is_rate()
                condensed_samples = self._condense_rate_data_samples(
                    from_timestamp, sample_resolution, to_timestamp)

            for sample in condensed_samples:
                yield sample
        else:
            if self.is_accumulation():
                def extract_target_from_time(sample):
                    return condense.floor(
                        sample.from_timestamp, sample_resolution, timezone)

                for current_from_time, current_samples in itertools.groupby(
                        self.get_condensed_samples(
                            from_timestamp, refined_resolution, to_timestamp),
                        key=extract_target_from_time):
                    current_to_time = current_from_time + sample_resolution
                    assert current_from_time >= from_timestamp
                    assert current_to_time <= to_timestamp

                    for condensed_sample in self.condense_accumulation(
                            current_from_time,
                            current_to_time,
                            list(current_samples)):
                        yield condensed_sample

            else:
                assert self.is_rate()

                condensed_samples = list(
                    self.get_condensed_samples(
                        from_timestamp, refined_resolution, to_timestamp))

                for frame_start, frame_end in pairwise(
                        count_extended(from_timestamp, sample_resolution)):

                    if frame_start == to_timestamp:
                        break

                    for condensed_sample in self.condense_rate(
                            list(
                                itertools.takewhile(
                                    lambda s: s.to_timestamp <= frame_end,
                                    condensed_samples))):
                        yield condensed_sample

                    condensed_samples = list(
                        itertools.dropwhile(
                            lambda s: s.to_timestamp < frame_end,
                            condensed_samples))

    CONTINUOUS_ACCUMULATION_ROLES = (
        DataRoleField.CONSUMPTION,
        DataRoleField.CO2,
        DataRoleField.COST,
        DataRoleField.MASS,
        DataRoleField.TIME,
        DataRoleField.STANDARD_HEATING_DEGREE_DAYS,
        DataRoleField.HEATING_DEGREE_DAYS,
        DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION,
        DataRoleField.VOLUME,
        DataRoleField.ENERGY_DRIVER,
        DataRoleField.PRODUCTION,
        DataRoleField.REACTIVE_ENERGY,
    )

    PIECEWISE_CONSTANT_ACCUMULATION_ROLES = ()

    ACCUMULATION_ROLES = CONTINUOUS_ACCUMULATION_ROLES + \
        PIECEWISE_CONSTANT_ACCUMULATION_ROLES

    PIECEWISE_CONSTANT_RATE_ROLES = (
        DataRoleField.STATE,
        DataRoleField.HEAT_TARIFF,
        DataRoleField.GAS_TARIFF,
        DataRoleField.ELECTRICITY_TARIFF,
        DataRoleField.WATER_TARIFF,
        DataRoleField.OIL_TARIFF,
        DataRoleField.CO2_QUOTIENT,
        DataRoleField.EMPLOYEES,
        DataRoleField.AREA,
        DataRoleField.HIDDEN_ELECTRICITY_TARIFF,
        DataRoleField.HIDDEN_GAS_TARIFF,
        DataRoleField.HIDDEN_HEAT_TARIFF,
        DataRoleField.HIDDEN_WATER_TARIFF,
        DataRoleField.HIDDEN_OIL_TARIFF,
    )

    CONTINUOUS_RATE_ROLES = (
        DataRoleField.POWER,
        DataRoleField.REACTIVE_POWER,
        DataRoleField.POWER_FACTOR,
        DataRoleField.ABSOLUTE_TEMPERATURE,
        DataRoleField.RELATIVE_TEMPERATURE,
        DataRoleField.VOLUME_FLOW,
        DataRoleField.VOLTAGE,
        DataRoleField.CURRENT,
        DataRoleField.FREQUENCY,
        DataRoleField.PRESSURE,
        DataRoleField.LINEAR_REGRESSION,
        DataRoleField.EFFICIENCY,
    )

    RATE_ROLES = PIECEWISE_CONSTANT_RATE_ROLES + CONTINUOUS_RATE_ROLES

    INTERVAL_FUNCTION_ROLES = (
        DataRoleField.MEAN_COOLDOWN_TEMPERATURE,
        DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
        DataRoleField.CONSUMPTION_UTILIZATION_AREA,
        DataRoleField.PRODUCTION_ENPI,
        DataRoleField.HEAT_LOSS_COEFFICIENT,
    )

    HIDDEN_ROLES = (
        DataRoleField.HIDDEN_ELECTRICITY_TARIFF,
        DataRoleField.HIDDEN_GAS_TARIFF,
        DataRoleField.HIDDEN_HEAT_TARIFF,
        DataRoleField.HIDDEN_WATER_TARIFF,
        DataRoleField.HIDDEN_OIL_TARIFF,
        DataRoleField.HIDDEN,
    )

    def get_underlying_function(self):
        """
        Method for retrieving a description of the underlying function of the
        samples kept in this C{DataSeries}.

        @return: One of C{UNDERLYING_FUNCTION_CHOICES}.

        @note: It is always more efficient to check for role inclusion in the
        relevant constant list.  This is useful to know when querying for a
        particular kind of underlying functions.

        @bug: May run clean, though this method returns a result and therefore
        should not be expected to have destructive side-effects.
        """
        if self.role is None:
            self.clean()

        assert self.role is not None
        if self.role in self.CONTINUOUS_ACCUMULATION_ROLES:
            return self.CONTINUOUS_ACCUMULATION
        elif self.role in self.PIECEWISE_CONSTANT_RATE_ROLES:
            return self.PIECEWISE_CONSTANT_RATE
        elif self.role in self.CONTINUOUS_RATE_ROLES:
            return self.CONTINUOUS_RATE
        elif self.role in self.PIECEWISE_CONSTANT_ACCUMULATION_ROLES:
            return self.PIECEWISE_CONSTANT_ACCUMULATION
        elif self.role in self.INTERVAL_FUNCTION_ROLES:
            return self.INTERVAL_FUNCTION

        assert False, "Underlying function for %d is undefined" % self.role

    def is_rate(self):
        """
        Check if this C{DataSeries} is a rate.

        @return: Return C{True} if this C{DataSeries} is a rate.
        """
        return self.get_underlying_function() in [self.CONTINUOUS_RATE,
                                                  self.PIECEWISE_CONSTANT_RATE]

    def is_accumulation(self):
        """
        Check if this C{DataSeries} is an accumulation.

        @return: Returns C{True} if this C{DataSeries} is an
        accumulation. C{False} otherwise.
        """
        return self.get_underlying_function() in [
            self.CONTINUOUS_ACCUMULATION, self.PIECEWISE_CONSTANT_ACCUMULATION]

    def is_continuous(self):
        """
        Check if this C{DataSereis} is continuous.
        """
        return self.get_underlying_function() in [
            self.CONTINUOUS_ACCUMULATION,
            self.CONTINUOUS_RATE]

    def is_piecewise_constant(self):
        """
        Check if this C{DataSeries} has a piecewise constant underlying
        function.

        @return: Returns C{True} if this C{DataSeries} is piecewise constant,
        C{False} otherwise.
        """

        return self.get_underlying_function() in [
            self.PIECEWISE_CONSTANT_RATE, self.PIECEWISE_CONSTANT_ACCUMULATION]

    def is_tariff(self):
        """
        Check if this C{DataSeries} is a tariff

        @return: Returns C{True} if this C{DataSeries} is a tariff C{False}
        otherwise.
        """
        return self.role in DataRoleField.TARIFFS

    def _interpolate_extrapolate_sample(self, timestamp,
                                        data_before=None, data_after=None):
        """
        Get potentially extarpolated or linear interpolated sample at given
        C{timestamp}.

        @keyword data_before: A StoredData or point Sample before C{timestamp}.
        If C{None}, the a query will be made to construct a C{data_before}.

        @keyword data_after: A StoredData or point Sample after C{timestamp}.
        If C{None}, the a query will be made to construct a C{data_after}.

        @return: If a sample at the exact timestamp requested is found, it is
        returned.  If samples on both sides of the timestamp requested are
        found, an interpolated value is computed and returned.  If samples on
        only one side are available, the value from the closest sample is used
        and returned (uncachable and extrapolated).  If no samples are
        available, neither before nor after the requested timestamp, None is
        returned.

        @note: The interpolation used is linear for continuous underlying
        functions, and trivial for piecewise constant underlying functions.

        @note: Extrapolation used is always trivial, i.e. extending with copy
        of end-point value.

        @note: This method is only intended for use with C{DataSeries} that
        actually store their data as L{StoredData}, unless both C{data_before}
        and C{data_after} are given.
        """
        if data_before is not None:
            if isinstance(data_before, StoredData):
                data_before = self.create_point_sample(
                    data_before.timestamp,
                    PhysicalQuantity(data_before.value, self.unit))
            assert isinstance(data_before, Sample)
            assert data_before.timestamp <= timestamp

        if data_after is not None:
            if isinstance(data_after, StoredData):
                data_after = self.create_point_sample(
                    data_after.timestamp,
                    PhysicalQuantity(data_after.value, self.unit))
            assert isinstance(data_after, Sample)
            assert data_after.timestamp >= timestamp

        if self.is_continuous():
            try:
                if data_before is None:
                    stored_data_before = self.stored_data.filter(
                        timestamp__lte=timestamp).order_by('-timestamp')[0]
                    data_before = self.create_point_sample(
                        stored_data_before.timestamp,
                        PhysicalQuantity(stored_data_before.value, self.unit))
                # short circuit; if "before" matches timestamp exactly, return
                # that.
                if data_before.timestamp == timestamp:
                    assert isinstance(data_before, Sample)
                    return data_before
            except IndexError:
                data_before = None
            try:
                if data_after is None:
                    stored_data_after = self.stored_data.filter(
                        timestamp__gte=timestamp).order_by('timestamp')[0]
                    data_after = self.create_point_sample(
                        stored_data_after.timestamp,
                        PhysicalQuantity(stored_data_after.value, self.unit))
                # short circuit; if "after" matches timestamp exactly, return
                # that
                if data_after.timestamp == timestamp:
                    assert isinstance(data_after, Sample)
                    return data_after
            except IndexError:
                data_after = None
            if data_before is not None and data_after is not None:
                assert data_before.timestamp < data_after.timestamp
                timespan_total = (data_after.timestamp -
                                  data_before.timestamp).total_seconds()
                timespan_before = (timestamp -
                                   data_before.timestamp).total_seconds()
                delta_value = data_after.physical_quantity - \
                    data_before.physical_quantity
                rate = delta_value / Fraction(timespan_total)
                val = data_before.physical_quantity + rate * \
                    Fraction(timespan_before)

                # interpolate
                return self.create_point_sample(
                    timestamp, val,
                    uncachable=data_before.uncachable or data_after.uncachable,
                    extrapolated=data_before.extrapolated or
                    data_after.extrapolated)

            elif data_before is not None:
                assert data_after is None
                # extrapolate
                return self.create_point_sample(
                    timestamp, data_before.physical_quantity,
                    uncachable=True, extrapolated=True)
            elif data_after is not None:
                assert data_before is None
                # extrapolate
                return self.create_point_sample(
                    timestamp,
                    data_after.physical_quantity,
                    uncachable=True, extrapolated=True)
            else:
                assert data_before is None and data_after is None
                return None

        else:
            assert self.is_piecewise_constant()
            try:
                if data_before is None:
                    stored_data_before = self.stored_data.filter(
                        timestamp__lte=timestamp).order_by('-timestamp')[0]
                    data_before = self.create_point_sample(
                        stored_data_before.timestamp,
                        PhysicalQuantity(stored_data_before.value, self.unit))
                # short circuit; if "before" matches timestamp exactly, return
                # that
                if data_before.timestamp == timestamp:
                    assert isinstance(data_before, Sample)
                    return data_before
                uncachable = extrapolated = not (
                    data_after is not None and
                    self.stored_data.filter(timestamp__gt=timestamp).exists())
                return self.create_point_sample(
                    timestamp, PhysicalQuantity(data_before.value, self.unit),
                    uncachable=uncachable, extrapolated=extrapolated)
            except IndexError:
                try:
                    if data_after is None:
                        data_after = self.stored_data.filter(
                            timestamp__gt=timestamp).order_by('timestamp')[0]
                    return self.create_point_sample(
                        timestamp,
                        PhysicalQuantity(data_after.value, self.unit),
                        uncachable=True, extrapolated=True)
                except IndexError:
                    return None

    def calculate_development(self, from_timestamp, to_timestamp):
        """
        Calculate the development between two points in time. Extrapolates if
        not enough data.

        @param from_timestamp: The first timestamp.

        @param to_timestamp: The last timestamp.

        @return: Return a L{Range} sample holding the development between
        C{from_timestamp} and C{to_timestamp}.  If no data was available at
        all, None is returned.

        @postcondition: If C{None} is returned, the domain of this
        C{DataSeries} is empty.
        """
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

    def depends_on(self):
        """
        Recursively collects a list of C{DataSeries} that this C{DataSeries}
        depends on.

        @see L{dataseries}

        @return: A list of L{DataSeries} that this C{DataSeries} depends upon.
        """
        return []

    def latest_sample(self, from_timestamp, to_timestamp):
        """
        The latest sample in the given time interval, M{[C{from_timestamp},
        C{to_timestamp})} for this C{DerivedDataSeries}.

        @precondition: C{self.is_rate()}.

        @return: Return a L{PointSample}, L{PointSampleCurrency} if samples
        are available in the given time interval, or C{None} if no sample is
        available.
        """
        assert self.is_rate()
        raw_data = self.get_samples(from_timestamp, to_timestamp)

        for sample in reversed(list(raw_data)):
            if sample.cachable:
                return sample

        return None

    def aggregated_samples(self, from_timestamp, to_timestamp):
        """
        The average sample, minimum sample and maximum sample of the given time
        interval, M{[C{from_timestamp}, C{to_timestamp}]}

        @precondition: C{self.is_rate()}

        @return: A tripple C{(avg, min, max)}, where:

          - C{avg} is a L{RangeSample} or a L{RangeSampleCurrency} holding the
            average value of the given timespan.  If insuficient values were
            available to interpolate at the end-points, the returned C{avg},
            may indicate a subinterval of the given time interval.  If
            insuficient values for calculating an average in the given time
            interval, C{avg} is C{None}.

          - C{min, max} are L{PointSample}s or L{PointSampleCurrency}s holding
            the minimum and maximum value in the given timespan.  If it is not
            even possible to interpolate a single value in the timespan, C{min,
            max} will be C{None, None}.  If there are multiple extremes only
            the earliest minimum and the earliest maximum will be included in
            the result.

        @postcondition: If the domain overlaps the given time interval, neither
        element in the returned tuple shall be None.

        @note: The term aggregates is in this context taken from the SQL
        terminology, where C{AVG}, C{MIN}, C{MAX} (and even C{COUNT}) are
        aggregates of a query result, not to be confused with the object
        oriented programming term spelled the same way.  However, there is an
        important semantic differense between the SQL C{AVG} and the average
        returned by this method.  In particular, the SQL C{AVG} does nothing to
        mimic the average of the underlying function, whereas, the average
        included in the result of this method is the mean value of the curve
        defined by the linear interpolation between the points of this data
        series across the given interval.  But also, the SQL C{MIN} and C{MAX}
        might be wrong, as interpolation values at the end-points of the
        interval should also be considered in case actual StoredData is not
        available at these timestamps.

        @note: This method is implemented strictly on top of
        L{get_samples()}, and so any valid override of
        L{get_samples()} should leave this C{aggregated_samples()}
        method in a working state.
        """
        assert self.is_rate()
        consumption = None
        minimum = None
        maximum = None
        for current_sample, next_sample in \
                pairwise_extended(itertools.ifilter(
                lambda s: not s.extrapolated,
                self.get_samples(from_timestamp, to_timestamp))):

            final_timestamp = current_sample.to_timestamp

            if minimum is None or \
                    current_sample.physical_quantity < \
                    minimum.physical_quantity:
                minimum = current_sample

            if maximum is None or \
                    current_sample.physical_quantity > \
                    maximum.physical_quantity:
                maximum = current_sample

            if self.is_piecewise_constant():
                # Area under horizontal line (piecewise constant)
                delta_consumption = (
                    PhysicalQuantity(
                        (current_sample.to_timestamp -
                         current_sample.from_timestamp).
                        total_seconds(), 'second') *
                    current_sample.physical_quantity)
            else:
                if next_sample is None:
                    break

                # Area under slope (interpolation of continuous)
                delta_consumption = (
                    PhysicalQuantity(
                        (next_sample.timestamp -
                         current_sample.timestamp).
                        total_seconds(), 'second') *
                    (
                        current_sample.physical_quantity +
                        next_sample.physical_quantity) /
                    PhysicalQuantity(2, 'none'))

            if consumption is not None:
                consumption += delta_consumption
            else:
                first_timestamp = current_sample.from_timestamp
                consumption = delta_consumption

        if minimum is not None and maximum is not None:
            if consumption is not None:
                average_value = consumption / PhysicalQuantity(
                    (final_timestamp - first_timestamp).total_seconds(),
                    'second')
                average_sample = self.create_range_sample(
                    first_timestamp, final_timestamp,
                    average_value)
            else:
                average_sample = maximum
        else:
            # Nothing at all yielded from self.get_samples(), or
            # everything yielded was extrapolated.  If there is a
            # non-zero-length overlap between requested period and domain, this
            # should not occur.
            minimum = None
            maximum = None
            average_sample = None

        return (average_sample, minimum, maximum)

    def create_point_sample(
            self, timestamp, physical_quantity,
            uncachable=False, extrapolated=False):
        """
        Factory method for creating a L{PointSample} or L{PointSampleCurrency}
        depending on what will suit this C{DataSeries}.

        @param timestamp: The timestamp of the created sample.

        @param physical_quantity: The value of the created sample.

        @param uncachable: If C{True} the returned point sample will never be
        cached.

        @param extrapolated: If C{True} the returned point sample is marked as
        extrapolated.

        @return: A L{PointSample} or L{PointSampleCurrency} with unit and
        possibly currency set to C{self.unit} and C{self.currency}
        respectively.
        """
        assert physical_quantity.compatible_unit(self.unit), \
            '%s not compatible with %s' % (physical_quantity.units, self.unit)

        return Sample(
            timestamp, timestamp, physical_quantity,
            not uncachable, extrapolated)

    def create_range_sample(
            self, from_timestamp, to_timestamp, physical_quantity,
            uncachable=False, extrapolated=False):
        """
        @param from_timestamp: The start-point of the range of the created
        sample.

        @param to_timestamp: The end-point of the range of the created sample.

        @param physical_quantity: The value of the created sample.

        @param uncachable: If C{True} the returned range sample will never be
        cached.

        @return: A L{RangeSample} or L{RangeSampleCurrency} with unit and
        possibly currency set to C{self.unit} and C{self.currency}
        respectively.
        """
        assert physical_quantity.compatible_unit(self.unit), \
            '%s not compatible with %s' % (physical_quantity.units, self.unit)

        return Sample(
            from_timestamp, to_timestamp, physical_quantity,
            not uncachable, extrapolated)

    def convert(self, value, target_unit):
        """
        Convert C{value} to C{target_unit}, assuming the unit of C{value} is
        C{self.unit}.

        @precondition: C{PhysicalQuantity.compatible_units(target_unit,
        self.unit)} is C{True} or C{target_unit in ['celsius'] and
        PhysicalQuantity.compatible_units('kelvin', self.unit)}.
        """
        quantity = PhysicalQuantity(value, self.unit)
        if target_unit == 'celsius':
            assert PhysicalQuantity.compatible_units('kelvin', self.unit)
            if self.role == DataRoleField.ABSOLUTE_TEMPERATURE:
                quantity -= PhysicalQuantity(Fraction("273.15"), 'kelvin')
            else:
                assert self.role == DataRoleField.RELATIVE_TEMPERATURE
            return quantity.convert('kelvin')
        else:
            assert PhysicalQuantity.compatible_units(target_unit, self.unit)
            return quantity.convert(target_unit)

    def condense_accumulation(self, from_timestamp, to_timestamp, samples):
        return [
            self.create_range_sample(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                physical_quantity=sum(
                    (sample.physical_quantity for sample in samples),
                    PhysicalQuantity(0, self.unit)),
                uncachable=(
                    (not samples) or
                    from_timestamp != samples[0].from_timestamp or
                    to_timestamp != samples[-1].to_timestamp or
                    any((not sample.cachable for sample in samples))),
                extrapolated=any((sample.extrapolated for sample in samples)))]

    def condense_rate(self, samples):
        """
        Condense rate by returning up to two samples that are local extremes
        (minimum, and maximum) within the given C{samples}.

        If there are more than two such local extremes it is not specified
        which valid pair of them will be returned in particular, only that some
        valid pair will be returned.
        """
        if samples:
            # The literal set serves to ensure that the same sample is not
            # yielded twice.
            return sorted(
                {
                    min(samples, key=attrgetter('physical_quantity')),
                    max(samples, key=attrgetter('physical_quantity'))},
                key=attrgetter('from_timestamp'))
        else:
            return []

    def get_preferred_unit_converter(self):
        """
        Get preferred unit converter.

        @see: L{preferredunits.get_preferred_unit_converter}.

        @precondition: C{self.customer is not None}
        """
        assert self.customer is not None or get_customer() is not None

        return get_preferred_unit_converter(
            self.role, utility_type=self.utility_type,
            customer=self.customer, unit=self.unit)

    def is_absolute_temperature(self):
        return self.role == DataRoleField.ABSOLUTE_TEMPERATURE


class StoredData(models.Model):
    """
    C{StoredData} is a class for storing data belonging to a
    L{DataSeries}, or a specialization of such.

    @ivar data_series: The L{DataSeries} this C{StoredData} belongs to.

    @ivar value: The integer value held by this C{StoredData}.  The unit of
    this value is found in C{data_series.unit}.

    @ivar timestamp: A timestamp that this C{StoredData} belongs to.  If this
    C{StoredData} represents a L{PointSample}, the C{timestamp} obviously
    correspond to L{PointSample.timestamp}.  If this C{StoredData} represents a
    L{RangeSample}, the C{timestamp} correspond to
    L{RangeSample.from_timestamp}, and the next C{StoredData} define the
    L{RangeSample.to_timestamp}.
    """
    data_series = models.ForeignKey(DataSeries, on_delete=models.CASCADE,
                                    related_name="stored_data")
    value = models.BigIntegerField(_('value'))
    timestamp = models.DateTimeField(_('timestamp'))

    class Meta:
        verbose_name = _('stored data')
        verbose_name_plural = _('stored data')
        unique_together = ("data_series", "timestamp")
        index_together = [
            ['data_series', 'timestamp'],
        ]
        ordering = ["timestamp"]
        app_label = 'measurementpoints'

    def __unicode__(self):
        return u"%s, %s" % (self.timestamp, self.value)
