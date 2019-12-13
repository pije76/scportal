# -*- coding: utf-8 -*-
"""
.. data:: _PERIOD_KEYS

    Dictionary mapping condense resolutions to key function factories.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import itertools
import operator

from gridplatform.utils import condense
from gridplatform.utils.samples import RangedSample


def _pad_ranged_sample_sequence(
        ranged_sample_sequence, from_timestamp, to_timestamp, resolution):
    """
    Pad a possibly incomplete ``ranged_sample_sequence`` by yielding `None`
    where :class:`RangedSamples<.RangedSample>` appear to be missing.
    """
    current_timestamp = from_timestamp
    for sample in ranged_sample_sequence:
        while current_timestamp < sample.from_timestamp:
            yield None
            current_timestamp = current_timestamp + resolution
        yield sample
        current_timestamp = sample.to_timestamp

    while current_timestamp < to_timestamp:
        yield None
        current_timestamp = current_timestamp + resolution


def multiply_ranged_sample_sequences(sequence_a, sequence_b):
    """
    Multiply two ranged sample sequences (`sequence_a` and `sequence_b`) sample
    by sample and yield the samples of the resulting ranged sample sequence.
    """
    sequence_a = iter(sequence_a)
    sequence_b = iter(sequence_b)

    while True:
        # Will stop on either input raising StopIteration...
        a, b = next(sequence_a), next(sequence_b)
        if a.from_timestamp != b.from_timestamp:
            # Missing entries in either; skip in the other.
            while a.from_timestamp < b.from_timestamp:
                a = next(sequence_a)
            while b.from_timestamp < a.from_timestamp:
                b = next(sequence_b)
        assert a.from_timestamp == b.from_timestamp
        assert a.to_timestamp == b.to_timestamp
        val = a.physical_quantity * b.physical_quantity
        yield a._replace(physical_quantity=val)


def subtract_ranged_sample_sequences(sequence_a, sequence_b):
    """
    Subtract two ranged sample sequences (`sequence_a` and `sequence_b`) sample
    by sample and yield the samples of the resulting ranged sample sequence.
    """
    sequence_a = iter(sequence_a)
    sequence_b = iter(sequence_b)

    a, b = next(sequence_a, None), next(sequence_b, None)

    while a is not None and b is not None:
        if a.from_timestamp < b.from_timestamp:
            yield a
            a = next(sequence_a, None)
        elif b.from_timestamp < a.from_timestamp:
            yield b._replace(physical_quantity=-b.physical_quantity)
            b = next(sequence_b, None)
        else:
            yield a._replace(
                physical_quantity=a.physical_quantity - b.physical_quantity)
            a, b = next(sequence_a, None), next(sequence_b, None)

    assert a is None or b is None

    while b is not None:
        assert a is None
        yield b._replace(physical_quantity=-b.physical_quantity)
        b = next(sequence_b, None)
    assert b is None

    while a is not None:
        assert b is None
        yield a
        a = next(sequence_a, None)
    assert a is None


def add_ranged_sample_sequences(
        ranged_sample_sequences, from_timestamp, to_timestamp, resolution):
    """
    Add multiple `ranged_sample_sequences` into one sample sequence.
    """
    padded_sequences = [
        _pad_ranged_sample_sequence(
            ranged_sample_sequence, from_timestamp, to_timestamp, resolution)
        for ranged_sample_sequence in ranged_sample_sequences]

    for padded_vector in itertools.izip(*padded_sequences):
        samples = [sample for sample in padded_vector if sample is not None]
        if samples:
            yield RangedSample(
                samples[0].from_timestamp, samples[0].to_timestamp,
                sum([sample.physical_quantity for sample in samples[1:]],
                    samples[0].physical_quantity))


def _fiveminutes_period_key(timezone):
    """
    Key function factory for five minute condense resolutions.

    :return: A key function for five minute condense resolutions.
    :rtype: :class:`datetime.datetime` -> :class:`datetime.datetime`

    :param timezone: The timezone in which the :class:`datetime.datetime` given
        to the key function should be interpreted when being rounded down to
        nearest five minute multiplum.

    :see: :func:`gridplatform.utils.condense.floor`.
    """
    def key(sample):
        timestamp = timezone.normalize(
            sample.from_timestamp.astimezone(timezone))
        return timestamp.replace(
            minute=timestamp.minute - (timestamp.minute % 5),
            second=0, microsecond=0)
    return key


def _hour_period_key(timezone):
    """
    Key function factory for hour condense resolutions.

    :return: A key function for hour condense resolutions.
    :rtype: :class:`datetime.datetime` -> :class:`datetime.datetime`

    :param timezone: The timezone in which the :class:`datetime.datetime` given
        to the key function should be interpreted when being rounded down to
        nearest hour.

    :see: :func:`gridplatform.utils.condense.floor`.
    """
    def key(sample):
        timestamp = timezone.normalize(
            sample.from_timestamp.astimezone(timezone))
        return timestamp.replace(minute=0, second=0, microsecond=0)
    return key


def _day_period_key(timezone):
    """
    Key function factory for day condense resolutions.

    :return: A key function for day condense resolutions.
    :rtype: :class:`datetime.datetime` -> :class:`datetime.datetime`

    :param timezone: The timezone in which the :class:`datetime.datetime` given
        to the key function should be interpreted when being rounded down to
        nearest day.

    :see: :func:`gridplatform.utils.condense.floor`.
    """
    def key(sample):
        timestamp = timezone.normalize(
            sample.from_timestamp.astimezone(timezone))
        return timezone.localize(timestamp.replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None))
    return key


def _month_period_key(timezone):
    """
    Key function factory for month condense resolutions.

    :return: A key function for month condense resolutions.
    :rtype: :class:`datetime.datetime` -> :class:`datetime.datetime`

    :param timezone: The timezone in which the :class:`datetime.datetime` given
        to the key function should be interpreted when being rounded down to
        nearest month.

    :see: :func:`gridplatform.utils.condense.floor`.
    """
    def key(sample):
        timestamp = timezone.normalize(
            sample.from_timestamp.astimezone(timezone))
        return timezone.localize(timestamp.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None))
    return key


def _quarter_period_key(timezone):
    """
    Key function factory for quarter condense resolutions.

    :return: A key function for quarter condense resolutions.
    :rtype: :class:`datetime.datetime` -> :class:`datetime.datetime`

    :param timezone: The timezone in which the :class:`datetime.datetime` given
        to the key function should be interpreted when being rounded down to
        nearest quarter.

    :see: :func:`gridplatform.utils.condense.floor`.
    """
    def key(sample):
        timestamp = timezone.normalize(
            sample.from_timestamp.astimezone(timezone))
        month = timestamp.month - ((timestamp.month - 1) % 3)
        return timezone.localize(timestamp.replace(
            month=month, day=1, hour=0, minute=0, second=0, microsecond=0,
            tzinfo=None))
    return key


def _year_period_key(timezone):
    """
    Key function factory for year condense resolutions.

    :return: A key function for year condense resolutions.
    :rtype: :class:`datetime.datetime` -> :class:`datetime.datetime`

    :param timezone: The timezone in which the :class:`datetime.datetime` given
        to the key function should be interpreted when being rounded down to
        nearest year.

    :see: :func:`gridplatform.utils.condense.floor`.
    """
    def key(sample):
        timestamp = timezone.normalize(
            sample.from_timestamp.astimezone(timezone))
        return timezone.localize(timestamp.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0,
            tzinfo=None))
    return key


_PERIOD_KEYS = {
    condense.FIVE_MINUTES: _fiveminutes_period_key,
    condense.HOURS: _hour_period_key,
    condense.DAYS: _day_period_key,
    condense.MONTHS: _month_period_key,
    condense.QUARTERS: _quarter_period_key,
    condense.YEARS: _year_period_key,
}


def aggregate_sum_ranged_sample_sequence(data, resolution, timezone):
    """
    Aggregate given sequence of accumulating
    :class:`RangedSamples<.RangedSample>` to new sequence of accumlating
    :class:`RangedSamples<.RangedSample>` with given resolution by summing
    sample values.

    :see: :meth:`.ConsumptionUnionBase.variable_cost_sequence` for example
        usage.  There variable costs are calculated in hourly accumulation
        samples first and then aggregated to the desired resolution afterwards.

    :param data: The sequence of accumulating
        :class:`RangedSamples<.RangedSample>`.
    :param resolution: The given condense resolution.  See
        :mod:`gridplatform.utils.condense`.
    :param tzinfo timezone: Used to determine the timespan of generated
        :class:`RangedSamples<.RangedSample>`.

    :return:  A sequence of accumulating :class:`RangedSamples<.RangedSample>`
    """
    assert resolution in _PERIOD_KEYS
    assert hasattr(timezone, 'localize')
    key = _PERIOD_KEYS[resolution](timezone)
    grouped = itertools.groupby(data, key)
    for timestamp, samples in grouped:
        yield RangedSample(
            timestamp, timestamp + resolution,
            reduce(
                operator.add,
                (s.physical_quantity for s in samples)))
