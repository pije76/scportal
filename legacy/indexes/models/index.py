# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Django model for indexes.

An index maps points in time to numeric values, such as dkr/kWh.
These are implemented in a L{Index} Django model and L{Entry} Django
model, where each L{Entry} belongs to an L{Index}.

Throughout this module, the term tariff will be used to abstractly
describe that which define the charges (pr unit cost) under certain
circumstances, say the price for a kWh within a given time period.
"""

from decimal import Decimal
from fractions import Fraction
import datetime
import itertools
import operator

from django.db import models
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from django.core.exceptions import ValidationError

from timezones2.models import TimeZoneField

from legacy.measurementpoints.models import Collection
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.utils.fields import BuckinghamField
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import CostCalculation
from legacy.measurementpoints.models import DataSeries
from legacy.measurementpoints.models import DegreeDayCorrection
from legacy.measurementpoints.models import Utilization
from legacy.measurementpoints.models.dataseries import UndefinedSamples
from gridplatform.utils.iter_ext import pairwise
from gridplatform.utils.preferredunits import PhysicalUnitConverter
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import utilitytypes
from gridplatform.utils.decorators import virtual
from gridplatform.trackuser import get_timezone

from .period import normalize_periods


class IndexUpdateError(Exception):
    pass


class Index(DataSeries, EncryptedModel):
    """
    An index maps points in time to values.

    @ivar unit: A short string describing the unit, say "dkr/kWh".

    @ivar name: A less short string naming the index, say "NOE
    el-priser"  This field is encrypted.

    @ivar name_plain: The unencrypted version of the C{name} member.

    @ivar _cached_entries: A list holding a cache of entries
    retrieved from the database using L{generate_cached_entries()}
    """
    SPOT = 0
    SEASONS = 1
    DERIVED = 2
    STANDARD_MONTH_INDEX = 3
    DATASOURCEADAPTER = 4

    DATA_FORMAT_CHOICES = (
        (SPOT, _('Spot data')),
        (SEASONS, _('Season data')),
        (DERIVED, _('Derived data')),
        (STANDARD_MONTH_INDEX, _('Monthly defined data')),
        (DATASOURCEADAPTER, _('Data source adapter')),
    )

    name = EncryptedCharField(max_length=100, verbose_name=_('name'))

    data_format = models.IntegerField(
        _('Entry data format'),
        choices=DATA_FORMAT_CHOICES,
        help_text=_("""
                    <p><b>Spot data:</b> Entry data is stored as
                    concrete time intervals mapped to constant entry
                    data values.</p>

                    <p><b>Season data:</b> Entry data is stored in
                    seasons, where each season is defined in terms
                    repeating the entry data values of one day.  The
                    entry data values of that day is stored as time
                    intervals mapped to constant entry data
                    values.</p>

                    <p><b>Derived data:</b> Entry data is not stored
                    directly, but rather derived from the entry data
                    of another index by multiplying with a coefficient
                    and adding a constant, where the coefficient and
                    constant may be defined differently for different
                    concrete periods of time.</p>
                    """))

    collection = models.ForeignKey(
        Collection, on_delete=models.PROTECT,
        blank=True, null=True, verbose_name=_('group'),
        limit_choices_to={'role': Collection.GROUP})

    timezone = TimeZoneField(verbose_name=_('timezone'),
                             default=get_timezone, blank=False)

    class Meta:
        verbose_name = _('index')
        verbose_name_plural = _('indexes')
        app_label = 'indexes'
        # inherit ordering from DataSeries

    @virtual
    def __unicode__(self):
        """
        @return: Return the decrypted name of the index if the index
        is owned by a customer, or the translated public name of the
        index otherwise
        """
        can_be_translated = self.name == self.name_plain

        if can_be_translated:
            name = _(self.name_plain)
        else:
            name = self.name_plain or self.name

        return _('{name} ({unit})').format(
            name=name,
            unit=self.get_preferred_unit_converter().get_display_unit())

    @models.permalink
    def get_absolute_url(self):
        if self.data_format == self.SEASONS:
            return (
                'manage_indexes-seasons-index-update-view', (),
                {'pk': str(self.id)})
        elif self.data_format == self.DERIVED:
            return (
                'manage_indexes-derived-index-update-view', (),
                {'pk': str(self.id)})
        raise IndexUpdateError('%r cannot be updated.' % self)

    def can_be_updated(self):
        try:
            self.get_absolute_url()
        except IndexUpdateError:
            return False
        else:
            return True

    def __init__(self, *args, **kwargs):
        """
        Construct a new L{Index}.
        """
        self._cached_entries = None
        super(Index, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        """
        """
        if self.customer_id is None:
            self._exclude_field_from_validation = ['name']
        super(Index, self).save(*args, **kwargs)

    def get_delete_prevention_reason(self):
        """
        Returns a HTML formated string with a description of why
        this index cannot be deleted.
        Returning None, if no reason exist, meaning the index can
        be deleted without breaking anything.
        """
        utilization = Utilization.objects.filter(
            needs=self)

        cost = CostCalculation.objects.filter(
            index__chain__links__data_series=self)

        degree_days = DegreeDayCorrection.objects.filter(
            standarddegreedays=self)

        num_dependencies = len(utilization) + len(cost) + len(degree_days)

        if num_dependencies == 0:
            return None

        mp_string = "<ul>"
        for util in itertools.chain(utilization, cost, degree_days):
            collection_name = util.consumption.graph.collection.name_plain
            mp_string += "<li>%s</li>" % escape(collection_name)
        mp_string += "</ul>"

        return ungettext_lazy(
            'This index cannot be deleted because the following '
            'depends on it: <br> {measurement_points_list}',
            'This index cannot be deleted because the following '
            'depend on it: <br> {measurement_points_list}',
            num_dependencies).format(measurement_points_list=mp_string)

    def is_deletable(self):
        """
        Returns true or false whether
        this index can be deleted or not.
        """
        # Get indexes used for utilization
        utilization = Utilization.objects.filter(needs=self)

        # Get indexes used for tariffs
        cost = CostCalculation.objects.filter(
            index__chain__links__data_series=self)

        # Get indexes used for standard heating degree
        degree_days = DegreeDayCorrection.objects.filter(
            standarddegreedays=self)

        if len(cost) == 0 and len(utilization) == 0 and len(degree_days) == 0:
            return True
        return False

    def generate_cached_entries(self, from_timestamp, to_timestamp):
        """
        Use this method rather than _iterate_entries() to minimize the
        number of database queries.
        """
        entry_generator = {
            Index.SPOT: self._iterate_entries,
            Index.SEASONS: self._generate_period_entries,
            Index.DERIVED: self._generate_period_entries}[self.data_format]

        if not self._cached_entries:
            self._cached_entries = list(
                entry_generator(from_timestamp, to_timestamp))
        elif self._cached_entries[0].from_timestamp > from_timestamp or \
                to_timestamp > self._cached_entries[-1].to_timestamp:
            self._cached_entries = list(
                entry_generator(
                    min(self._cached_entries[0].from_timestamp,
                        from_timestamp),
                    max(self._cached_entries[-1].to_timestamp, to_timestamp)))

        for entry in self._cached_entries:
            if entry and entry.from_timestamp < to_timestamp \
                    and entry.to_timestamp > from_timestamp:
                yield entry

    def _generate_period_entries(self, from_timestamp, to_timestamp):
        """
        Generate entries for season or derived periods within a given
        time interval.

        @param from_timestamp: The beginning of the interval.

        @param to_timestamp: The end of the interval.

        @invariant: All entries C{e} yielded, the interval C{[t,t']}
        of C{e} will overlap C{[from_timestamp, to_timestamp)}.
        """
        def assert_invariant(entry):
            assert(entry.from_timestamp < to_timestamp)
            assert(entry.to_timestamp > from_timestamp)

        if self.data_format == Index.SEASONS:
            period_set = self.seasonindexperiod_set
        else:
            assert(self.data_format == Index.DERIVED)
            period_set = self.derivedindexperiod_set

        head_period = period_set.filter(
            from_date__lte=from_timestamp.date()).order_by("-from_date")[:1]
        tail_periods = period_set.filter(
            from_date__lte=to_timestamp.date(),
            from_date__gt=from_timestamp.date()).order_by("from_date")

        # Initial condition: The first interval yielded will start at
        # from_timestamp.
        #
        # Terminal condition: The final interval yielded will end at
        # to_timestamp
        #
        # Loop variant: The _from_time of any subsequently yielded
        # period equals the _to_time of the previously yielded period.
        def iterate_periods():
            _from_time = from_timestamp
            _to_time = None
            _period = None
            for p in head_period:
                _period = p
            for p in tail_periods:
                _to_time = p.from_timestamp()
                if _from_time != _to_time:
                    # don't yield empty period
                    assert _from_time < _to_time, '%s %s' % (
                        _from_time, _to_time)
                    # yield the previous period, as the current period
                    # defines the end of that.
                    yield (_period, _from_time, _to_time)
                _period = p
                _from_time = _to_time
            _to_time = to_timestamp
            # yield the final period, as no subsequent period define
            # the end of that.
            if _period:
                yield (_period, _from_time, _to_time)

        for period, from_time_, to_time_ in iterate_periods():
            if period:
                for entry in period.generate_entries(from_time_, to_time_):
                    assert_invariant(entry)
                    yield entry

    def _iterate_entries(self, from_timestamp, to_timestamp):
        """
        Iterate over entries covering a given interval.

        This method will make sure that the entire interval is
        covered, but the entries yielded may be phony (covering for
        missing entries).

        @param from_timestamp: The beginning of the interval covered by the
        yielded entries.

        @param to_timestamp: The end of the interval covered by the yielded
        entries.

        @invariant: For each yielded entry C{e}, the set union of
        C{[e.from_timestamp; e.to_timestamp)} and C{[from_timestamp;
        to_timestamp)} is not empty.

        @precondition: You can only iterate entries for spot indexes:
        C{self.data_format == Index.SPOT}
        """
        def assert_invariant(e):
            assert e.from_timestamp <= e.to_timestamp, \
                'e.from_timestamp=%r, e.to_timestamp=%r' % (
                    e.from_timestamp, e.to_timestamp)
            assert e.from_timestamp < to_timestamp, \
                'e.from_timestamp=%r, to_timestamp=%r' % (
                    e.from_timestamp, to_timestamp)
            assert from_timestamp < e.to_timestamp, \
                'from_timestamp=%r, e.to_timestamp=%r' % (
                    from_timestamp, e.to_timestamp)
            assert e.value is not None, \
                'e.from_timestamp=%r, e.to_timestamp=%r. Value was None.' % (
                    e.from_timestamp, e.to_timestamp)

        assert(self.data_format == Index.SPOT)

        assert(to_timestamp.tzinfo is not None)
        assert(from_timestamp is not None)
        assert(from_timestamp.tzinfo is not None)

        entries = self.entry_set.filter(
            from_timestamp__lt=to_timestamp,
            to_timestamp__gt=from_timestamp).order_by("from_timestamp")

        for e in entries:
            assert_invariant(e)
            yield e

    def minimize_noncontiguous(self, from_timestamp, to_timestamp, duration):
        """
        Generate a list of periods, within an interval, with a given
        combined duration that minimize the underlying index values.

        @param from_timestamp: The start of the interval, containing the
        resulting periods.

        @param to_timestamp: The end of the interval, containing the
        resulting periods.

        @param duration: The combined duration of the resulting
        periods.

        @return: A list of normalized periods.  See also
        L{normalize_periods()}.  If insufficient entries are available, the
        result will be extended with the earliest untaken periods to cover the
        entire C{duration}.

        @precondition: C{duration} must fit between C{from_timestamp} and
        C{to_timestamp}.

        @postcondition: The entire duration is covered
        """
        assert(from_timestamp + duration <= to_timestamp)

        # The algorithm of this method consists of two steps:
        #
        #
        #   1) Ensure RangedSamples cover the entire [from_timestamp,
        #      to_timestamp] interval.
        #
        #   2) Allocate the cheapest subintervals that combined add up to
        #      duration.

        ZERO = PhysicalQuantity(0, self.unit)

        # Patch holes in samples with extra_samples
        samples = list(self.get_samples(from_timestamp, to_timestamp))
        if not samples:
            # one big hole.
            extra_samples = [
                self.create_range_sample(from_timestamp, to_timestamp, ZERO)]
        else:
            extra_samples = []
            if samples[0].from_timestamp > from_timestamp:
                # patch hole in front of samples
                extra_samples.append(
                    self.create_range_sample(
                        from_timestamp, samples[0].from_timestamp, ZERO))

            for s1, s2 in pairwise(samples):
                if s1.to_timestamp != s2.from_timestamp:
                    # patch holes between samples
                    assert s1.to_timestamp < s2.from_timestamp
                    extra_samples.append(
                        self.create_range_sample(
                            s1.to_timestamp, s2.from_timestamp, ZERO))

            if samples[-1].to_timestamp < to_timestamp:
                # patch hole after samples
                extra_samples.append(
                    self.create_range_sample(
                        samples[-1].to_timestamp, to_timestamp, ZERO))

        # Sort samples in ascending order according to their values to allocate
        # the cheapest subintervals that combined add up to duration.
        minimized_periods = []
        remaining_duration = duration

        sorted_samples = itertools.chain(
            sorted(samples, key=operator.attrgetter('physical_quantity')),
            extra_samples)

        for sample in sorted_samples:
            new_from_time = max(sample.from_timestamp, from_timestamp)
            new_to_time = min(sample.to_timestamp, to_timestamp)

            if remaining_duration <= new_to_time - new_from_time:
                minimized_periods.append(
                    (new_from_time,
                     new_from_time + remaining_duration))
                remaining_duration = datetime.timedelta()
                break
            else:
                minimized_periods.append((new_from_time, new_to_time))
                remaining_duration -= (new_to_time - new_from_time)

        # allocated intervals must add up to duration.
        assert not remaining_duration
        return normalize_periods(minimized_periods)

    def calculate_average_value(self, from_timestamp, to_timestamp):
        """
        Calculate average value between two points in time.
        """
        result = PhysicalQuantity(0, self.unit)
        total_duration = PhysicalQuantity(
            Fraction((to_timestamp - from_timestamp).total_seconds()),
            'second')
        for sample in self.get_samples(from_timestamp, to_timestamp):
            sample_duration = PhysicalQuantity(
                Fraction(
                    (sample.to_timestamp - sample.from_timestamp).
                    total_seconds()), 'second')

            result += sample.physical_quantity * sample_duration / \
                total_duration

        return result

    def minimize_contiguous(self, from_timestamp, to_timestamp, duration):
        """
        Minimize contiguous usage in a given interval.

        @param from_timestamp: The start of the interval.

        @param to_timestamp: The end of the interval.

        @param duration: The duration of the contiguous usage.

        @return: Returns the start of the contiguous usage with
        minimized cost.
        """
        assert(to_timestamp - from_timestamp >= duration)

        # Overall approach: intervals starting at the start of an
        # entry or ending at the end of an entry are interesting
        # candidates.  Apart from that, starting at from_timestamp or
        # ending at to_timestamp are also candidates.
        candidates = {from_timestamp, to_timestamp - duration}

        for sample in self.get_samples(from_timestamp, to_timestamp):
            # Potential candidate: Start at this samples from_timestamp.
            if from_timestamp <= sample.from_timestamp <= \
                    to_timestamp - duration:
                candidates.add(sample.from_timestamp)

            # Potential candidate: Stop at this samples to_timestamp.
            if from_timestamp + duration <= sample.to_timestamp <= \
                    to_timestamp:
                candidates.add(sample.to_timestamp - duration)

        # Return the candidate with the minimum cost
        return min([(
                    candidate,
                    self.calculate_average_value(
                        candidate, candidate + duration).
                    convert(self.unit))
                    for candidate in candidates], key=lambda e: e[1])[0]

    def generate_true_periods(self, from_timestamp, to_timestamp, predicate):
        """
        Generate a list of disjunctive periods within a given interval
        where the L{Entry.value} checked with a C{predicate} evaluates
        to C{True}.

        @param from_timestamp: The start of the given interval.

        @param to_timestamp: The end of the given interval.

        @param predicate: A predicate function that takes a C{Decimal} as
        argument and returns a C{bool}.

        @return: Returns a list of nonoverlapping distinct periods in
        the form of tuples where the first element is a
        C{datetime.datetime} marking the start of the period, and the
        second element is a C{datetime.datetime} marking the end of
        the period.  For instance::

            index.generate_true_periods(
                datetime.datetime(2011, 2, 1, 4),
                datetime.datetime(2011, 2, 1, 9),
                lambda x: x <= Decimal("0.32"))

        will return a list of periods C{(from_timestamp, to_timestamp)} all
        somewhere between 4am and 9am on February 1st, 2011, in which
        the underlying value is less than or equal to C{0.32}.
        """
        assert(isinstance(from_timestamp, datetime.datetime))
        assert(isinstance(to_timestamp, datetime.datetime))
        assert(from_timestamp <= to_timestamp)

        return [(max(period_from_time, from_timestamp),
                 min(period_to_time, to_timestamp))
                for period_from_time, period_to_time in
                normalize_periods([
                    (sample.from_timestamp, sample.to_timestamp)
                    for sample in self.get_samples(
                        from_timestamp, to_timestamp)
                    if predicate(sample.physical_quantity)])]

    def satisfies_search(self, substring):
        """
        Check if this C{Index} matches a search in the form of a
        substring.

        @param substring: The substring to match against this
        C{Index}.

        @return: Return C{True} if this C{Index} matches C{substring},
        C{False} otherwise.
        """
        return substring.lower() in self.name.lower()

    def _encrypt(self, request):
        """
        Encrypt L{EncryptedField}s of this L{Index} unless
        C{self.customer} is None, in which case we just store the
        plain text values as encrypted fields.

        @param request: The request used for encryption.
        """
        if self.customer_id:
            super(Index, self)._encrypt(request)
        else:
            self._name_ciphertext = self.name_plain

    def _decrypt(self, request):
        """
        Decrypt L{EncryptedField}s of this L{Index} unless
        C{self.customer} is None, in which case we just recover the
        plain text values directly from the encrypted fields.

        @param request: The request used for decryption.
        """
        if self.customer_id:
            super(Index, self)._decrypt(request)
        else:
            self._name_plaintext = self.name

    def get_derivatives(self):
        """
        Method for recursively getting C{Index}es derived from this
        C{Index}.

        @return: Return a list of C{Index}es derived from this
        C{Index}.
        """
        result = [self]
        for p in self.period_derivative_set.all():
            result += p.index.get_derivatives()
        return result

    @virtual
    def _get_samples(self, from_timestamp, to_timestamp):
        """
        Override of L{DataSeries}.

        This override return entries converted to piecewise constant rate
        samples.
        """
        values = [
            self.create_range_sample(
                max(from_timestamp, entry.from_timestamp),
                min(to_timestamp, entry.to_timestamp),
                PhysicalQuantity(entry.value, self.unit))
            for entry in self.generate_cached_entries(
                from_timestamp, to_timestamp)
            if entry.value is not None]

        return sorted(values, key=lambda x: x.from_timestamp)

    def _condense_data_samples_recursive(self, from_timestamp,
                                         sample_resolution, to_timestamp=None):
        raise UndefinedSamples()

    def get_icon(self):
        """
        Returns icon string for this C{Index}
        """
        if self.role in (DataRoleField.CO2, DataRoleField.CO2_QUOTIENT):
            return 'co2'
        elif self.role == DataRoleField.EMPLOYEES:
            return 'human'
        elif self.role == DataRoleField.AREA:
            return 'area'
        elif self.utility_type == utilitytypes.METER_CHOICES.electricity:
            return 'electricity'
        elif self.utility_type == utilitytypes.METER_CHOICES.water:
            return 'water'
        elif self.utility_type == utilitytypes.METER_CHOICES.gas:
            return 'gas'
        elif self.utility_type == utilitytypes.METER_CHOICES.district_heating:
            return 'heat'
        elif self.utility_type == utilitytypes.METER_CHOICES.oil:
            return 'oil'
        else:
            return None

    @virtual
    def get_preferred_unit_converter(self):
        """
        Get preferred unit converter.

        Override of L{DataSeries.get_preferred_unit_converter()} because
        C{Index}es usually do not require conversion, and in particular
        customer may not be set on C{Index}es.
        """
        return PhysicalUnitConverter(self.unit)


class Entry(models.Model):
    """
    An C{Entry} holds a constant index value within a given
    C{datetime} interval.

    @ivar index: The L{Index} that this entry belongs to.

    @ivar from_timestamp: The start of the interval.

    @ivar to_timestamp: The end of the interval.

    @ivar value: The value held by the index in this interval.
    """
    index = models.ForeignKey(Index, on_delete=models.CASCADE)
    from_timestamp = models.DateTimeField()
    to_timestamp = models.DateTimeField()
    value = models.DecimalField(decimal_places=5,
                                max_digits=10)

    class Meta:
        verbose_name = _('entry')
        verbose_name_plural = _('entries')
        ordering = ['from_timestamp']
        app_label = 'indexes'
        unique_together = (
            ('index', 'from_timestamp'),
            ('index', 'to_timestamp'))

    def __unicode__(self):
        if self.index_id:
            return u'%s: %s -- %s: %s' % (
                self.index, self.from_timestamp, self.to_timestamp, self.value)
        else:
            return u'%s -- %s: %s' % (
                self.from_timestamp, self.to_timestamp, self.value)

    def save(self, *args, **kwargs):
        assert self.from_timestamp < self.to_timestamp
        super(Entry, self).save(*args, **kwargs)


class Period(models.Model):
    """
    A C{Period} defines index values within a given date interval.
    The C{Period} class is abstract, see L{SeasonIndexPeriod} and
    L{DerivedIndexPeriod} for concrete classes.

    @ivar index: The Index that this C{Period} defines a
    period for.

    @ivar from_date: The date at which the period defined by this
    C{Period} starts.
    """
    index = models.ForeignKey(Index, on_delete=models.CASCADE)
    from_date = models.DateField()

    class Meta(object):
        abstract = True
        verbose_name = _('period')
        verbose_name_plural = _('periods')
        ordering = ['from_date']
        app_label = 'indexes'

    def from_timestamp(self):
        """
        Return when this period starts.

        @return: Returns a C{datetime.datetime} indicating when this
        period starts.
        """
        return self.index.timezone.localize(
            datetime.datetime.combine(
                self.from_date,
                datetime.time()))

    def generate_entries(self, from_timestamp, to_timestamp):
        """
        Generate entries.

        @param from_timestamp: The start of the interval.

        @param to_timestamp: The end of the interval.

        @precondition: C{from_timestamp >= self.from_timestamp()}

        @invariant: All entries C{e} yielded, the interval C{[t,t']}
        of C{e} will overlap C{[from_timestamp, to_timestamp)}.
        """
        raise NotImplementedError(
            "Specializations of this class must implement this method.")


class DerivedIndexPeriod(Period):
    """
    A C{DerivedIndexPeriod} define the tariff of an index within a
    certain period.  The defined tariff is on the form C{y = ax + b},
    where C{y} is the defined tariff, C{a} is a coefficient, C{x}
    represent the tariff of another index and C{b} is a constant.
    There is also an optional C{roof}, so that if C{y} becomes larger
    than this C{roof}, the C{roof} is used instead.

    @ivar other_index:  The index defining C{x}.

    @ivar coefficient:  The coefficient defining C{a}.

    @ivar constant: The constant defining C{b}.

    @ivar roof:  The optional roof, defining C{roof}
    """
    other_index = models.ForeignKey(Index, on_delete=models.PROTECT,
                                    related_name='period_derivative_set')

    coefficient = models.DecimalField(decimal_places=5,
                                      max_digits=10,
                                      default=Decimal("1.000"))
    constant = models.DecimalField(decimal_places=5,
                                   max_digits=10,
                                   default=Decimal("0.000"))

    roof = models.DecimalField(decimal_places=5,
                               max_digits=10,
                               null=True,
                               blank=True,
                               default=None)

    class Meta(Period.Meta):
        verbose_name = _('derived index period')
        verbose_name_plural = _('derived index periods')
        app_label = 'indexes'
        # inherit ordering from Period

    def clean(self):
        super(DerivedIndexPeriod, self).clean()
        try:
            other_index = self.other_index
            index = self.index
        except Index.DoesNotExist:
            pass
        else:
            if other_index.utility_type != index.utility_type:
                raise ValidationError(_('Utility types must match'))
            if not PhysicalQuantity.compatible_units(other_index.unit,
                                                     index.unit):
                raise ValidationError(_('Units must be compatible'))
            if other_index in index.get_derivatives():
                raise ValidationError(
                    _('Other index is defined in terms of this index'))

    def generate_entries(self, from_timestamp, to_timestamp):
        """
        Generate entries.

        @param from_timestamp: The start of the interval.

        @param to_timestamp: The end of the interval.

        @precondition: C{from_timestamp >= self.from_timestamp()}

        @invariant: All entries C{e} yielded, the interval C{[t,t']}
        of C{e} will overlap C{[from_timestamp, to_timestamp)}.
        """
        def assert_invariant(entry):
            assert(entry.from_timestamp < to_timestamp)
            assert(entry.to_timestamp > from_timestamp)

        assert(from_timestamp >= self.from_timestamp())

        for sample in self.other_index._get_samples(
                from_timestamp, to_timestamp):
            value = self.coefficient * sample.physical_quantity + \
                PhysicalQuantity(self.constant, self.index.unit)
            if self.roof is not None:
                value = min(
                    value, PhysicalQuantity(self.roof, self.index.unit))
            e = Entry(value=value.convert(self.index.unit),
                      from_timestamp=max(
                          sample.from_timestamp, from_timestamp),
                      to_timestamp=min(sample.to_timestamp, to_timestamp))
            assert_invariant(e)
            yield e


class SeasonIndexPeriod(Period):
    """
    A C{SeasonIndexPeriod} define the tariff of an index within a
    certain period by repeating the entries of a 24 hour day.

    The hourly entries are stored in C{[value_at_hour_0, ...,
    value_at_hour_23]}, where for example C{value_at_hour_0} contains
    the value at hour 0:00-1:00 in the timezone of the owning
    L{Index}.  Use the L{get_value_at_hour()} method to retrieve the
    values given an integer hour, time object or datetime object.
    """
    value_at_hour_0 = models.DecimalField(
        _('value between midnight and 1:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_1 = models.DecimalField(
        _('value between 1:00 am and 2:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_2 = models.DecimalField(
        _('value between 2:00 am and 3:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_3 = models.DecimalField(
        _('value between 3:00 am and 4:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_4 = models.DecimalField(
        _('value between 4:00 am and 5:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_5 = models.DecimalField(
        _('value between 5:00 am and 6:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_6 = models.DecimalField(
        _('value between 6:00 am and 7:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_7 = models.DecimalField(
        _('value between 7:00 am and 8:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_8 = models.DecimalField(
        _('value between 8:00 am and 9:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_9 = models.DecimalField(
        _('value between 9:00 am and 10:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_10 = models.DecimalField(
        _('value between 10:00 am and 11:00 am'),
        decimal_places=5, max_digits=10)
    value_at_hour_11 = models.DecimalField(
        _('value between 11:00 am and noon'),
        decimal_places=5, max_digits=10)
    value_at_hour_12 = models.DecimalField(
        _('value between noon am and 1:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_13 = models.DecimalField(
        _('value between 1:00 pm and 2:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_14 = models.DecimalField(
        _('value between 2:00 pm and 3:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_15 = models.DecimalField(
        _('value between 3:00 pm and 4:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_16 = models.DecimalField(
        _('value between 4:00 pm and 5:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_17 = models.DecimalField(
        _('value between 5:00 pm and 6:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_18 = models.DecimalField(
        _('value between 6:00 pm and 7:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_19 = models.DecimalField(
        _('value between 7:00 pm and 8:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_20 = models.DecimalField(
        _('value between 8:00 pm and 9:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_21 = models.DecimalField(
        _('value between 9:00 pm and 10:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_22 = models.DecimalField(
        _('value between 10:00 pm and 11:00 pm'),
        decimal_places=5, max_digits=10)
    value_at_hour_23 = models.DecimalField(
        _('value between 11:00 pm and midnight'),
        decimal_places=5, max_digits=10)

    class Meta:
        verbose_name = _('season index period')
        verbose_name_plural = _('season index periods')
        app_label = 'indexes'
        # inherit ordering from Period

    def __init__(self, *args, **kwargs):
        """
        Construct a new L{SeasonIndexPeriod}.

        @param args: Arguments forwarded to C{super(SeasonIndexPeriod,
        self)}

        @param kwargs: Arguments forwarded to
        C{super(SeasonIndexPeriod, self)}, except that the keyword
        C{value_at_hour} will be transformed into the corresponding
        C{value_at_hour_1},...C{value_at_hour_23} keywords
        """
        if "value_at_hour" in kwargs:
            assert(len(kwargs["value_at_hour"]) == 24)
            for i in range(24):
                kwargs["value_at_hour_%d" % i] = kwargs["value_at_hour"][i]
            del kwargs["value_at_hour"]

        super(SeasonIndexPeriod, self).__init__(*args, **kwargs)

    def get_value_at_hour(self, key):
        """
        Get value at a given hour.

        @param key: The given hour: this may be an integer in the
        range C{[0, 23]}, or a datetime.datetime in which case the
        corresponding hour of the timezone of this index is used.

        @return: Returns the value at the given hour.
        """
        if isinstance(key, datetime.datetime):
            key = self.index.timezone.normalize(
                key.astimezone(self.index.timezone))
            key = key.hour
        return getattr(self, "value_at_hour_%d" % key)

    def generate_entries(self, from_timestamp, to_timestamp):
        """
        Generate entries using C{value_at_hour} for each hour in the
        given interval.

        @param from_timestamp: The start of the interval.

        @param to_timestamp: The end of the interval.

        @precondition: C{from_timestamp >= self.from_timestamp()}

        @invariant: All entries C{e} yielded, the interval C{[t,t']}
        of C{e} will overlap C{[from_timestamp, to_timestamp)}.
        """
        def assert_invariant(entry):
            assert(entry.from_timestamp < to_timestamp)
            assert(entry.to_timestamp > from_timestamp)

        assert(from_timestamp >= self.from_timestamp())

        # whole-hour times
        entry_from_time = from_timestamp.replace(
            minute=0, second=0, microsecond=0)
        while entry_from_time < to_timestamp:
            e = Entry(value=self.get_value_at_hour(entry_from_time),
                      from_timestamp=entry_from_time,
                      to_timestamp=(
                          entry_from_time + datetime.timedelta(hours=1)))
            assert_invariant(e)
            yield e
            entry_from_time += datetime.timedelta(hours=1)


class SpotMapping(models.Model):
    """
    A C{SpotMapping} contains information used when importing data, for
    translating external identifiers to L{Index} IDs.

    Currently used only for importing from Nordpool.

    @ivar index: The L{Index} data should be inserted for.
    @ivar area: For Nordpool, the area "alias".
    @ivar timezone: For Nordpool, timezone of input data.

    @attention: Not represented in the UI.
    """
    index = models.OneToOneField(Index)
    area = models.CharField(max_length=3)
    unit = BuckinghamField()
    timezone = TimeZoneField()

    class Meta:
        verbose_name = _('spot mapping')
        verbose_name_plural = _('spot mappings')
        ordering = ['area', 'unit']
        app_label = 'indexes'

    def __unicode__(self):
        return u'%s-%s: %s' % (
            self.area, self.currency, self.index)

    def save(self, *args, **kwargs):
        assert self.index.data_format == Index.SPOT
        super(SpotMapping, self).save(*args, **kwargs)

    @property
    def currency(self):
        """
        For Nordpool, the price "unit", i.e. currency.
        """
        if 'currency_dkk' in self.unit:
            return 'DKK'
        elif 'currency_eur' in self.unit:
            return 'EUR'
        else:
            raise ValueError('no currency in %s' % self.unit)
