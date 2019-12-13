# -*- coding: utf-8 -*-
"""
.. data:: CACHABLE_UNITS

    Set of units of various accumulations that may have been used as unit for
    :class:`DataSources<.DataSource>`.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from fractions import Fraction
import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from gridplatform.customer_datasources.models import DataSource
from gridplatform.datasources.models import RawData
from gridplatform.utils.iter_ext import pairwise
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.units import ACCUMULATION_BASE_UNITS
from gridplatform.utils.units import IMPULSE_BASE_UNITS
from gridplatform.utils.samples import Sample


CACHABLE_UNITS = set(ACCUMULATION_BASE_UNITS + IMPULSE_BASE_UNITS)


def validate_hour(timestamp):
    """
    Validator that ensures given ``timestamp`` is on the hour.

    :raise ValidationError: If given ``timestamp`` is not on the hour.
    :raise ValidationError: If given ``timestamp`` does not have a timezone.
    """
    if timestamp.tzinfo is None:
        raise ValidationError(
            'Missing timezone for timestamp %s.' % (timestamp,))
    if (timestamp.minute, timestamp.second, timestamp.microsecond) != \
            (0, 0, 0):
        raise ValidationError(
            'Timestamp %s does not match clock hour.' % (timestamp,))


def validate_five_minutes(timestamp):
    """
    Validator that ensures given ``timestamp`` is a five minute multiplum.

    :raise ValidationError: If given ``timestamp`` is not a five minute multiplum.
    :raise ValidationError: If given ``timestamp`` does not have a timezone.
    """
    if timestamp.tzinfo is None:
        raise ValidationError(
            'Missing timezone for timestamp %s.' % (timestamp,))
    if (timestamp.second, timestamp.microsecond) != (0, 0) or \
            timestamp.minute % 5 != 0:
        raise ValidationError(
            'Timestamp %s does not match five minute interval.' % (timestamp,))


class AccumulatedData(models.Model):
    """
    Abstract base model for accumulated data.

    :ivar datasource: The :class:`.DataSource` whose data is being accumulated.
    :ivar value:  The accumulated value.
    """
    datasource = models.ForeignKey(DataSource, db_index=False)
    value = models.BigIntegerField()

    class Meta:
        abstract = True
        # NOTE: unique_together creates an index; index_together would create
        # would create an extra, redundant index
        unique_together = ('datasource', 'timestamp')
        ordering = ['timestamp']


class HourAccumulatedData(AccumulatedData):
    """
    Concrete specialization of :class:`.AccumulatedData` for hourly accumulations.

    :ivar timestamp: The leading timestamp of the hour this accumulation data
        belongs to.
    """
    timestamp = models.DateTimeField(validators=[validate_hour])

    class Meta(AccumulatedData.Meta):
        verbose_name = _('hour accumulated data')
        verbose_name_plural = _('hour accumulated data')

    def __unicode__(self):
        return u"%s, %s" % (self.timestamp, self.value)

    def save(self, *args, **kwargs):
        """
        :precondition: ``self.timestamp`` is on the hour and has a timezone.
        """
        validate_hour(self.timestamp)
        super(HourAccumulatedData, self).save(*args, **kwargs)


class FiveMinuteAccumulatedData(AccumulatedData):
    """
    Concrete specialization of :class:`.AccumulatedData` for five-minute accumulations.

    :ivar timestamp: The leading timestamp of the five minutes this
        accumulation data belongs to.
    """
    timestamp = models.DateTimeField(validators=[validate_five_minutes])

    class Meta(AccumulatedData.Meta):
        verbose_name = _('five minutes accumulated data')
        verbose_name_plural = _('five minutes accumulated data')

    def __unicode__(self):
        return u"%s, %s" % (self.timestamp, self.value)

    def save(self, *args, **kwargs):
        """
        :precondition: ``self.timestamp`` is a five minute multiplum and has a
            timezone.
        """
        validate_five_minutes(self.timestamp)
        super(FiveMinuteAccumulatedData, self).save(*args, **kwargs)


@receiver(post_delete, sender=RawData)
def cleanup_cache_for_rawdata_delete(sender, instance, **kwargs):
    """
    Signal handler called when a :class:`.RawData` is deleted.

    The time period between between the :class:`RawData` just before the
    deleted and the RawData just after the deleted is considered tainted.  (Use
    timestamp from deleted for edge case of no data before or no data after.)
    Cache data whose time period starts or ends within this period will be
    deleted.
    """
    datasource_id = instance.datasource_id
    previous_timestamp = RawData.objects.filter(
        datasource_id=datasource_id,
        timestamp__lt=instance.timestamp,
    ).order_by('timestamp').values_list('timestamp', flat=True).last()
    range_start = previous_timestamp or instance.timestamp
    next_timestamp = RawData.objects.filter(
        datasource_id=datasource_id,
        timestamp__gt=instance.timestamp,
    ).order_by('timestamp').values_list('timestamp', flat=True).first()
    range_end = next_timestamp or instance.timestamp
    if range_start == range_end:
        # There was only a single data point in data sequence --- no cache
        # could have been computed from that.
        assert range_start == instance.timestamp == range_end
        # The sanity check is perhaps a bit expensive --- but optimising this
        # special case by avoiding it would not be worthwhile; the normal case
        # will query both cache tables anyway.
        assert not HourAccumulatedData.objects.filter(
            datasource_id=datasource_id).exists()
        assert not FiveMinuteAccumulatedData.objects.filter(
            datasource_id=datasource_id).exists()
        return
    # Hours that start or end inside range; the first hour that ends inside
    # range may have started an hour before...
    hour_range_start = range_start - datetime.timedelta(hours=1)
    HourAccumulatedData.objects.filter(
        datasource_id=datasource_id,
        timestamp__gte=hour_range_start,
        timestamp__lte=range_end).delete()
    five_minute_range_start = range_start - datetime.timedelta(minutes=5)
    FiveMinuteAccumulatedData.objects.filter(
        datasource_id=datasource_id,
        timestamp__gte=five_minute_range_start,
        timestamp__lte=range_end).delete()


def get_hourly_accumulated(datasource, from_timestamp, to_timestamp):
    """
    Get hourly accumulated data as ranged `Sample` instances; using existing
    cached values when possible.
    """
    validate_hour(from_timestamp)
    validate_hour(to_timestamp)
    return get_accumulated(
        datasource, datasource.houraccumulateddata_set,
        from_timestamp, to_timestamp, datetime.timedelta(hours=1))


def get_five_minute_accumulated(datasource, from_timestamp, to_timestamp):
    """
    Get hourly accumulated data as ranged `Sample` instances; using existing
    cached values when possible.
    """
    validate_five_minutes(from_timestamp)
    validate_five_minutes(to_timestamp)
    return get_accumulated(
        datasource, datasource.fiveminuteaccumulateddata_set,
        from_timestamp, to_timestamp, datetime.timedelta(minutes=5))


def get_accumulated(
        datasource, cache_queryset,
        from_timestamp, to_timestamp, period_length):
    """
    Shared logic for `get_hourly_accumulated()` and
    `get_five_minute_accumulated()`.  Try to read from cache; if necessary,
    supplement by computing missing entries, return result as list of `Sample`
    objects.
    """
    entries = list(cache_queryset.filter(
        timestamp__gte=from_timestamp,
        timestamp__lt=to_timestamp).order_by('timestamp').values_list(
        'timestamp', 'value'))
    period_count = (to_timestamp - from_timestamp).total_seconds() / \
        period_length.total_seconds()
    interpolate_fn = datasource._get_interpolate_fn()
    assert period_count == round(period_count)
    assert len(entries) <= period_count
    if len(entries) < period_count:
        # We skip logic for finding/generating missing periods if cached data
        # is present for all of the requested.  That should hopefully be the
        # common case, making optimising it worthwhile.
        timestamps = [timestamp for timestamp, value in entries]
        missing = missing_periods(
            from_timestamp, to_timestamp, timestamps, period_length)
        for missing_from, missing_to in missing:
            data = raw_data_for_cache(datasource, missing_from, missing_to)
            generated = generate_period_data(
                data, missing_from, missing_to, period_length, interpolate_fn)
            entries.extend(generated)
        entries.sort()
    assert len(entries) <= period_count
    unit = datasource.unit
    return [
        Sample(timestamp, timestamp + period_length,
               PhysicalQuantity(value, unit), False, False)
        for timestamp, value in entries
    ]


INT64_MIN = -2**63
INT64_MAX = 2**63-1


def generate_cache(datasource, from_timestamp, to_timestamp):
    """
    Generate and store `HourAccumulatedData` and `FiveMinuteAccumulatedData`.
    """
    validate_hour(from_timestamp)
    validate_hour(to_timestamp)
    assert datasource.unit in CACHABLE_UNITS

    ONE_HOUR = datetime.timedelta(hours=1)
    FIVE_MINUTES = datetime.timedelta(minutes=5)
    interpolate_fn = datasource._get_interpolate_fn()
    present_five_minutes = list(
        datasource.fiveminuteaccumulateddata_set.filter(
            timestamp__gte=from_timestamp,
            timestamp__lt=to_timestamp).order_by('timestamp').values_list(
            'timestamp', flat=True))
    missing_five_minutes = set(missing_periods(
        from_timestamp, to_timestamp, present_five_minutes, FIVE_MINUTES))
    present_hours = list(datasource.houraccumulateddata_set.filter(
        timestamp__gte=from_timestamp,
        timestamp__lt=to_timestamp).order_by('timestamp').values_list(
        'timestamp', flat=True))
    missing_hours = set(missing_periods(
        from_timestamp, to_timestamp, present_hours, ONE_HOUR))
    # Combine RawData reading when both missing the same periods.  We only
    # optimise for the case of them missing the exact same periods, as we would
    # expect cache generation to have been run for the same periods for both
    # if/when run; other cases of missing periods should be less common, and
    # are handled but not optimised.
    missing_both = missing_five_minutes & missing_hours
    missing_five_minutes_only = missing_five_minutes - missing_both
    missing_hour_only = missing_hours - missing_both
    five_minute_data = []
    hour_data = []
    for missing_from, missing_to in missing_both:
        data = raw_data_for_cache(datasource, missing_from, missing_to)
        five_minute_data.extend(generate_period_data(
            data, missing_from, missing_to, FIVE_MINUTES, interpolate_fn))
        hour_data.extend(generate_period_data(
            data, missing_from, missing_to, ONE_HOUR, interpolate_fn))

    for missing_from, missing_to in missing_five_minutes_only:
        data = raw_data_for_cache(datasource, missing_from, missing_to)
        five_minute_data.extend(generate_period_data(
            data, missing_from, missing_to, FIVE_MINUTES, interpolate_fn))
    for missing_from, missing_to in missing_hour_only:
        data = raw_data_for_cache(datasource, missing_from, missing_to)
        hour_data.extend(generate_period_data(
            data, missing_from, missing_to, ONE_HOUR, interpolate_fn))
    if five_minute_data:
        five_minute_objects = []
        for timestamp, value in five_minute_data:
            obj = FiveMinuteAccumulatedData(
                datasource=datasource,
                timestamp=timestamp,
                value=int(Fraction(value).limit_denominator(1)))
            if obj.value <= INT64_MIN:
                obj.value = INT64_MIN
            if obj.value >= INT64_MAX:
                obj.value = INT64_MAX
            five_minute_objects.append(obj)
        FiveMinuteAccumulatedData.objects.bulk_create(five_minute_objects)
    if hour_data:
        hour_objects = []
        for timestamp, value in hour_data:
            obj = HourAccumulatedData(
                datasource=datasource,
                timestamp=timestamp,
                value=int(Fraction(value).limit_denominator(1)))
            if obj.value <= INT64_MIN:
                obj.value = INT64_MIN
            if obj.value >= INT64_MAX:
                obj.value = INT64_MAX
            hour_objects.append(obj)
        HourAccumulatedData.objects.bulk_create(hour_objects)


def missing_periods(from_timestamp, to_timestamp, present, period_length):
    """
    Find contiguous periods within `from_timestamp`, `to_timestamp` not
    represented by timestamps from `present`.  Each element in `present`
    represents a time period of length `period_length` by its starting point.

    This function, and how it is used, may be considered a "brute force"
    approach, but if we work with datasets/period where iterating over the
    condensed representation becomes problematic, we'll have other problems
    too...
    """
    assert from_timestamp <= to_timestamp
    assert (to_timestamp - from_timestamp).total_seconds() % \
        period_length.total_seconds() == 0
    if present == []:
        # Everything missing.
        yield (from_timestamp, to_timestamp)
        return
    if from_timestamp < present[0]:
        # Missing data before first present.
        yield from_timestamp, present[0]
    for a, b in pairwise(present):
        if a + period_length < b:
            # Missing data between present elements.
            yield (a + period_length, b)
    if present[-1] + period_length < to_timestamp:
        # Missing data after last present.
        yield (present[-1] + period_length, to_timestamp)


def generate_period_data(
        data, from_timestamp, to_timestamp, period_length, interpolate_fn):
    """
    Transform ordered list of `(timestamp, accumulated_value)` from `data` into
    sequence of `(timestamp, increase)`, where `increase` represents the growth
    in accumulated value between `timestamp` and `timestamp + period_length`.

    Only periods within both the range represented by elements in `data` and
    the range represented by [`from_timestamp`, `to_timestamp`] are included.
    `from_timestamp` and `to_timestamp` should be aligned to `period_length`.
    """
    adjusted_from, adjusted_to = adjust_from_to(
        data, from_timestamp, to_timestamp, period_length)
    if adjusted_from is None or adjusted_to is None:
        return
    aligned = period_aligned(
        data, adjusted_from, adjusted_to, period_length, interpolate_fn)
    for (timestamp_a, value_a), (timestamp_b, value_b) in pairwise(aligned):
        assert timestamp_b - timestamp_a == period_length
        yield (timestamp_a, value_b - value_a)


def raw_data_for_cache(
        datasource, from_timestamp, to_timestamp,
        border=datetime.timedelta(minutes=1)):
    """
    Obtain raw data for the requested period, and, if possible, also a few
    samples outside the requested, in order to be able to use the result to
    interpolate the values at `from_timestamp` and `to_timestamp`.

    Returns empty list if no data inside specified range is found *and* finding
    data outside the range to enable interpolation failed.  (I.e. empty list if
    insufficient data to specify or interpolate any points in closed range
    [`from_timestamp`, `to_timestamp`].  This will occur if no data is
    available for the data source, or all available data is outside the
    specified range in the same direction.)
    """
    assert border >= datetime.timedelta()
    before_from = from_timestamp - border
    after_to = to_timestamp + border
    data = list(datasource.rawdata_set.filter(
        timestamp__gte=before_from,
        timestamp__lte=after_to).order_by('timestamp').values_list(
        'timestamp', 'value'))
    TIMESTAMP = 0
    # VALUE = 1
    if data == [] or data[-1][TIMESTAMP] < to_timestamp:
        # If no data *or* last data element before to_timestamp, attempt to
        # load next data element after.  (If no data present, loading
        # "after"-data here and "before"-data subsequently may still provide
        # sufficient data for interpolation.)
        after = datasource.rawdata_set.filter(
            timestamp__gte=to_timestamp).order_by('timestamp').values_list(
            'timestamp', 'value').first()
        if after is not None:
            # Stuff will break in other places if we don't maintain the order
            # in data.
            assert data == [] or data[-1][TIMESTAMP] < after[TIMESTAMP]
            data.append(after)
    if data != [] and data[0][TIMESTAMP] > from_timestamp:
        # If data present *and* first data element after from_timestamp,
        # attempt to load last data element before.  (If no data present, then
        # we failed to load "after"-data, and querying the database here would
        # be pointless; even if we succeed in loading "before"-data, that would
        # not be enough.)
        before = datasource.rawdata_set.filter(
            timestamp__lte=from_timestamp).order_by('timestamp').values_list(
            'timestamp', 'value').last()
        if before is not None:
            # Stuff will break in other places if we don't maintain the order
            # in data.
            assert data == [] or data[0][TIMESTAMP] > before[TIMESTAMP]
            data.insert(0, before)
    if data == [] or data[0][TIMESTAMP] > to_timestamp or \
            data[-1][TIMESTAMP] < from_timestamp:
        # No data, or all data fourd after to_timestamp, or all data found
        # before from_timestamp.  (As we obtain some data outside the range to
        # help interpolation, data is not necessarily empty for these cases.)
        return []
    # Ideally, at this point we have
    #     data[0][TIMESTAMP] <= from_timestamp <= \
    #         to_timestamp <= data[-1][TIMESTAMP]
    # but we might have
    #     from_timestamp <= data[0][TIMESTAMP] <= \
    #         data[-1][TIMESTAMP] <= to_timestamp
    # or other variations, depending on available data.
    assert data[0][TIMESTAMP] <= to_timestamp
    assert from_timestamp <= data[-1][TIMESTAMP]
    return data


def adjust_from_to(data, from_timestamp, to_timestamp, period_length):
    """
    Compute new from/to timestamps such that the resulting range is a subset of
    the range of [`from_timestamp`, `to_timestamp`] and *also* a subset of the
    time range represented in `data`, while keeping the alignment to
    `period_length` of `from_timestamp` and `to_timestamp`.

    The greatest such range is returned as a pair; if no such range exists,
    `(None, None)` is returned.

    With the current implementation, `period_length` must be a divisor of
    `datetime.timedelta(days=1)`.  (At least conceptually --- division is not
    directly defined for timedelta objects.)
    """
    assert from_timestamp <= to_timestamp
    # Period_length must be a divisor of datetime.timedelta(days=1) --- or the
    # attempt to be clever and jump days at a time will fail.
    assert datetime.timedelta(days=1).total_seconds() % \
        period_length.total_seconds() == 0
    if not data:
        # If there is no data, then the resulting range is empty.  (Return
        # *after* input validation --- other parameters should be well-formed
        # even if there is no data.)
        return (None, None)
    TIMESTAMP = 0
    # VALUE = 1
    if from_timestamp < data[0][TIMESTAMP]:
        # Skip the appropriate number of whole days before adjusting
        # hour-by-hour, to ensure a limited number of loop iterations even in
        # the worst case.
        difference_days = (data[0][TIMESTAMP] - from_timestamp).days
        from_timestamp += datetime.timedelta(days=difference_days)
        # Day adjustment should not overshoot ...
        assert from_timestamp <= data[0][TIMESTAMP]
        # ... nor leave us further than a day away from the correct value.
        assert (data[0][TIMESTAMP] - from_timestamp) < \
            datetime.timedelta(days=1)
        # We avoid trying to be clever with the seconds/microseconds fields of
        # timedelta; adding one hour at a time is straightforward, and we'll
        # need to add at most 23 hours.
        while from_timestamp < data[0][TIMESTAMP]:
            from_timestamp += period_length
    assert from_timestamp >= data[0][TIMESTAMP]
    if to_timestamp > data[-1][TIMESTAMP]:
        # As for from_timestamp; skip days before adjusting hour-by-hour.
        difference_days = (to_timestamp - data[-1][TIMESTAMP]).days
        to_timestamp -= datetime.timedelta(days=difference_days)
        # Did not overshoot, did not miss a whole day.
        assert to_timestamp >= data[-1][TIMESTAMP]
        assert (to_timestamp - data[-1][TIMESTAMP]) < \
            datetime.timedelta(days=1)
        while to_timestamp > data[-1][TIMESTAMP]:
            to_timestamp -= period_length
    assert to_timestamp <= data[-1][TIMESTAMP]
    if from_timestamp > to_timestamp:
        # Not a single period-length aligned point present inside data.
        return (None, None)
    return (from_timestamp, to_timestamp)


def period_aligned(
        data, from_timestamp, to_timestamp, period_length, interpolate_fn):
    """
    Transform sequence of `(timestamp, value)`-tuples to sequence of
    `(timestamp, value)`-tuples aligned to `period_length`, starting from
    `from_timestamp`, using interpolation to determine value if timestamp
    between entries in input.

    `data` a list of `(timestamp, value)`-tuples, sorted by timestamp.

    First data element must be before or at `from_timestamp`, last data element
    must be at or after `to_timestamp`.

    `from_timestamp` and `to_timestamp` must represent absolute timestamps
    aligned to `period_length`.  `from_timestamp` must be before or the same as
    `to_timestamp`.  Adding `period_length` some number of times to
    `from_timestamp` must eventually lead to `to_timestamp`.
    """
    TIMESTAMP = 0
    VALUE = 1
    assert from_timestamp <= to_timestamp
    # Partial check only --- both might be equally misaligned.
    assert (to_timestamp - from_timestamp).total_seconds() % \
        period_length.total_seconds() == 0
    assert data[0][TIMESTAMP] <= from_timestamp
    assert data[-1][TIMESTAMP] >= to_timestamp
    next_timestamp = from_timestamp
    # Yield one interpolated value per hour-point, including the endpoints at
    # from_timestamp, to_timestamp.
    for point_a, point_b in pairwise(data):
        # Initially; from data[0][TIMESTAMP] <= from_timestamp
        # In loop; from point_a being point_b from previous iteration where
        #   point_b[TIMESTAMP] <= next_timestamp
        assert point_a[TIMESTAMP] <= next_timestamp
        # From (unchecked) precondition for function; that data is sorted
        assert point_a[TIMESTAMP] < point_b[TIMESTAMP]
        while point_a[TIMESTAMP] <= next_timestamp < point_b[TIMESTAMP]:
            # One or more period-aligned points between the current pair; yield
            # for each of those.
            yield (next_timestamp, interpolate_fn(
                next_timestamp, point_a, point_b))
            next_timestamp += period_length
            if next_timestamp > to_timestamp:
                return
        assert point_a[TIMESTAMP] < point_b[TIMESTAMP] <= next_timestamp
    # We know that
    #     data[-1][TIMESTAMP] >= to_timestamp
    # and that if
    #     data[-1][TIMESTAMP] > to_timestamp
    # then the function have retured after yielding a value for `to_timestamp`
    # from inside the loop.  Hence we have:
    assert data[-1][TIMESTAMP] == to_timestamp
    # Also, any `next_timestamp` fulfilling
    #     next_timestamp < data[-1][TIMESTAMP]
    # would have been yielded from the inner loop; hence:
    assert next_timestamp == to_timestamp
    # Intentionally avoiding use of point_a/point_b here --- to implicitly
    # handle the edge case of
    #     from_timestamp == to_timestamp == data[0][TIMESTAMP] and \
    #         len(data) == 1
    # where `point_a` and `point_b` would be uninitialised.
    yield (next_timestamp, Fraction(data[-1][VALUE]))
