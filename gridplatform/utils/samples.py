# -*- coding: utf-8 -*-
"""
Defiens various sample types.

.. class:: RangedSample(from_timestamp, to_timestamp, physical_quantity)

    A sample in the forms of a :class:`.PhysicalQuantity` covering a
    timestamp range.

.. class:: PointSample(timestamp, physical_quantity)

    A sample in the forms of a :class:`.PhysicalQuantity` of a point
    in time.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import itertools
import datetime
from collections import namedtuple

from .unitconversion import PhysicalQuantity
from .decorators import deprecated


RangedSample = namedtuple(
    'RangedSample', ('from_timestamp', 'to_timestamp', 'physical_quantity'))


PointSample = namedtuple(
    'PointSample', ('timestamp', 'physical_quantity'))


_Sample = namedtuple(
    'Sample', ('from_timestamp', 'to_timestamp', 'physical_quantity',
               'cachable', 'extrapolated'))


class Sample(_Sample):
    """
    Class for measurement/data samples.

    :deprecated: This class is deprecated (due to overly complex
        implementation of features not needed), use
        :class:`.RangedSample` or :class:`PointSample` instead.  The
        implementation resembles a C-style union of
        :class:`.RangedSample` and :class:`PointSample`.
    """
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        """
        Immutable subclass of tuple --- members are set up in __new__; this is
        for sanity checks, and to support use in multiple inheritance.

        :warning: Does not support multiple inheritance, as ``__init__()`` is
        not forwarded to super.  Forwarding causes run-time warnings, and
        should only be introduced when needed.
        """
        self._check_valid()

    def _check_valid(self):
        """
        Basic checks that this specifies a valid sample.
        """
        assert isinstance(self.from_timestamp, datetime.datetime), \
            'not a datetime: %r' % (self.from_timestamp,)
        assert self.from_timestamp.tzinfo is not None
        assert isinstance(self.to_timestamp, datetime.datetime), \
            'not a datetime: %r' % (self.to_timestamp,)
        assert self.to_timestamp.tzinfo is not None
        assert self.from_timestamp <= self.to_timestamp, \
            'from_timestamp=%r > to_timestamp=%r' % (
                self.from_timestamp, self.to_timestamp)
        assert isinstance(self.physical_quantity, PhysicalQuantity), \
            'not a PhysicalQuantity: %r' % (self.physical_quantity,)
        assert isinstance(self.cachable, bool)
        assert isinstance(self.extrapolated, bool)

    def _replace(self, **kwargs):
        """
        Return a new Sample object replacing specified fields with new
        values.  Taskes the "extra" parameter ``timestamp`` to set
        both ``from_timestamp`` and ``to_timestamp`` for a point
        sample.
        """
        if 'timestamp' in kwargs:
            if not self.is_point:
                raise ValueError('Setting timestamp not legal for range ')
            if 'from_timestamp' in kwargs:
                raise ValueError(
                    'Cannot specify both from_timestamp and timestamp')
            if 'to_timestamp' in kwargs:
                raise ValueError(
                    'Cannot specify both to_timestamp and timestamp')
            timestamp = kwargs.pop('timestamp')
            kwargs['from_timestamp'] = timestamp
            kwargs['to_timestamp'] = timestamp
        obj = super(Sample, self)._replace(**kwargs)
        obj._check_valid()
        return obj

    def in_closed_interval(self, from_timestamp, to_timestamp):
        """
        Check whether the time point or range defined by this sample is
        entirely contained within the closed interval specified by
        [``from_timestamp``, ``to_timestamp``].

        :param from_timestamp: The start-point of the given range.
        :param to_timestamp: The end-point of the given range.
        """
        return from_timestamp <= self.from_timestamp <= \
            self.to_timestamp <= to_timestamp

    @property
    def timestamp(self):
        """
        For point samples --- samples with identical ``from_timestamp`` and
        ``to_timestamp`` --- return the timestamp.
        """
        if not self.is_point:
            raise ValueError('%r is not a point sample.' % (self,))
        return self.from_timestamp

    @property
    def is_point(self):
        """
        A point sample is a sample with ``from_timestamp`` equal to
        ``to_timestamp``.
        """
        return self.from_timestamp == self.to_timestamp

    @property
    def is_range(self):
        """
        A range sample is a sample with ``from_timestamp`` strictly less than
        ``to_timestamp``.
        """
        return self.from_timestamp < self.to_timestamp

    @property
    def uncachable(self):
        return not self.cachable

    def __nonzero__(self):
        return bool(self.physical_quantity)


def wrap_ranged_sample(sample):
    return Sample(
        sample.from_timestamp, sample.to_timestamp, sample.physical_quantity,
        True, False)


def wrap_ranged_sample_sequence(ranged_sample_sequence):
    return itertools.imap(wrap_ranged_sample, ranged_sample_sequence)
