# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from operator import attrgetter
from gridplatform.utils.iter_ext import pairwise


class InterpolationFrame(object):
    """
    An C{InterpolationFrame} is a frame of a L{DataSeries} inside which
    interpolations can be made efficiently; see L{get_sample_at()}.

    C{InterpolationFrame}s can be advanced, to efficiently interpolate the next
    range of samples; see L{advance()}.

    @ivar pivot_timestamp: The interpolation frame ends at this timestamp.  To
    get interpolations beyond this timestamp, this C{InterpolationFrame} must
    be advanced.  Interpolation is only well-defined between the previous
    C{pivot_timestamp} and the current C{pivot_timestamp}, both ends included.

    @invariant: C{from_timestamp <= pivot_timestamp <= to_timestamp}, where
    C{from_timestamp} and C{to_timestamp} are defined as C{__init__()}
    arguments.
    """

    def __init__(self, data_series, from_timestamp, to_timestamp):
        """
        Construct a new C{InterpolationFrame} ready to iterate across a
        L{DataSeries} in a given time interval.

        @param data_series: The given L{DataSeries}.

        @param from_timestamp: The start of the time interval.

        @param to_timestamp: The end of the time interval.
        """
        self.data_series = data_series
        self._from_time = from_timestamp
        self._to_time = to_timestamp
        if from_timestamp == to_timestamp:
            # Only one sample. next(self.iterator) must raise StopIteration,
            # and both _from_sample and _to_sample are set to the same sample.
            self.iterator = iter([])
            self._from_sample = self._to_sample = next(
                data_series.get_samples(
                    from_timestamp,
                    to_timestamp),
                None)
        else:
            self.iterator = pairwise(
                data_series.get_samples(self._from_time, self._to_time))
            self._from_sample, self._to_sample = \
                next(self.iterator, (None, None))

    def advance(self):
        """
        Attempt to advance this C{InterpolationFrame}.

        @return: Returns C{True} if this C{InterpolationFrame} was successfully
        advanced, C{False} otherwise.

        @postcondition: C{from_timestamp < pivot_timestamp <= to_timestamp},
        where C{from_timestamp} and C{to_timestamp} are defined as
        C{__init__()} arguments.

        @postcondition: If the return value was C{False}, C{pivot_timestamp ==
        to_timestamp}, where C{to_timestamp} is defined as C{__init__()}
        arguments.
        """
        try:
            self._from_sample, self._to_sample = next(self.iterator)
            assert self._from_time < self.pivot_timestamp <= self._to_time
            return True
        except StopIteration:
            assert self.pivot_timestamp == self._to_time
            return False

    def get_sample_at(self, timestamp):
        """
        @precondition: C{timestamp} lies between the current C{pivot_timestamp}
        and the previous C{pivot_timestamp}.

        @return: Returns a sample representing C{timestamp}, possibly using
        interpolation or extrapolation. If no such sample can be constructed,
        C{None} is returned.
        """
        assert self._from_sample is None or \
            self._from_sample.timestamp <= timestamp
        assert self._to_sample is None or \
            timestamp <= self._to_sample.timestamp
        return self.data_series._interpolate_extrapolate_sample(
            timestamp, self._from_sample, self._to_sample)

    @property
    def pivot_timestamp(self):
        if self._to_sample is not None:
            return self._to_sample.timestamp
        else:
            return self._to_time


class InterpolationCloud(object):
    """
    An C{InterpolationCloud} is a sample vector iterator, keeping track of
    which sample pairs for each of a number of L{DataSeries} surround a given
    timestamp (the timestamp of the currently yielded sample vector).
    Example::

        interpolation_cloud = InterpolationCloud(data_series_list,
                                                 from_timestamp, to_timestamp)
        for sample_vector in interpolation_cloud:
            # do stuff here

    This class is intended to be used in L{DataSeries} that are defined in
    terms of a number of continuous L{DataSeries}; i.e. C{DataSeries} whose raw
    samples are point samples, where linear interpolation is sound.
    """

    def __init__(self, data_series_list, from_timestamp, to_timestamp):
        """
        For each timestamp between C{from_timestamp} and C{to_timestamp} that
        holds a sample in any of the underlying L{DataSeries}, a sample vector
        will constructed.  Each entry in such a sample vector is a sample of
        the corresponding L{DataSeries}.  The sample index in the sample vector
        equals the corresponding L{DataSeries} index in the
        C{data_series_list}.
        """
        self.data_series_list = data_series_list
        self.from_timestamp = from_timestamp
        self.to_timestamp = to_timestamp
        self.interpolation_iterators = [
            InterpolationFrame(
                data_series, self.from_timestamp, self.to_timestamp)
            for data_series in self.data_series_list]
        self.current_timestamp = self.from_timestamp
        self.final_sample_yielded = False

    def __iter__(self):
        return self

    def next(self):
        """
        The next sample vector.

        @return: Returns the next vector of samples.  All samples in this
        sample vector share the same timestamp. If one or more of the
        underlying C{DataSeries} is unable to define a sample at this
        timestamp, their sample is replaced with None.

        @postcondition: The next sample vector being yielded (if any) has a
        larger timestamp than the one returned this time (loop variant).

        @raise StopIteration: when called after the final sample has been
        yielded.
        """
        if self.final_sample_yielded or len(self.interpolation_iterators) == 0:
            raise StopIteration()

        sample_vector = [interpolation_iterator.get_sample_at(
            self.current_timestamp) for
            interpolation_iterator in
            self.interpolation_iterators]

        for i in self.interpolation_iterators:
            if i.pivot_timestamp == self.current_timestamp and not i.advance():
                self.final_sample_yielded = True

        if not self.final_sample_yielded:
            self.current_timestamp = min(
                self.interpolation_iterators,
                key=attrgetter('pivot_timestamp')).pivot_timestamp

        return sample_vector
