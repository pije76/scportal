# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import itertools

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.utils import condense
from gridplatform.utils.samples import Sample
from gridplatform.utils.unitconversion import PhysicalQuantity

from ..interpolationcloud import InterpolationCloud
from .dataseries import DataSeries


class Stream(object):
    """
    Iterator wrapper which provides a `peek()` method by reading one ahead in
    the underlying iterator.

    NOTE: This will always have read one ahead in the underlying iterator ---
    which allows a simpler implementation than lazy/on-demand evaluation of the
    underlying iterator, and does not matter for the immediate use.

    NOTE: This will yield an infinite sequence of `None` after the elements of
    the underlying sequence.  This, again, allows for a simpler implementation
    than one raising `StopIteration` when the underlying iterator does.
    """
    def __init__(self, sequence):
        self._iterator = iter(sequence)
        self._head = next(self._iterator, None)

    def __iter__(self):
        return self

    def peek(self):
        return self._head

    def next(self):
        val = self._head
        self._head = next(self._iterator, None)
        return val


class Summation(DataSeries):
    """
    A C{Summation} is a L{DataSeries} that is defined as the sum of other
    L{DataSeries} through the L{SummationTerm} relation, which also defines the
    sign to be used for the particular term in the sum.

    @ivar plus_data_series: A list of L{DataSeries} to add in this
    C{Summation}.

    @ivar minus_data_series: A list of L{DataSeries} to subtract in this
    C{Summation}.
    """

    included_data_series = models.ManyToManyField(
        DataSeries, related_name='summation_derivative_set',
        through='measurementpoints.SummationTerm',
        symmetrical=False)

    class Meta(DataSeries.Meta):
        verbose_name = _('summation')
        verbose_name_plural = _('summations')
        app_label = 'measurementpoints'

    def __init__(self, *args, **kwargs):
        """
        Construct a C{Summation}.  Optionally, the data series to add and
        subtract may be given here.

        @keyword plus_data_series: An optional list of L{DataSeries} to add in
        this C{Summation}.

        @keyword minus_data_series: An optional list of L{DataSeries} to
        subtract in this C{Summation}.
        """
        if 'plus_data_series' in kwargs:
            self.plus_data_series = kwargs.pop('plus_data_series')
        if 'minus_data_series' in kwargs:
            self.minus_data_series = kwargs.pop('minus_data_series')
        super(Summation, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        """
        Save this C{Summation} and the involved relations.
        """
        super(Summation, self).save(*args, **kwargs)

        # Ensure data series to be added in this summation are stored.
        add_data_series_ids = []
        for add_ds in self.plus_data_series:
            self.terms.get_or_create(
                sign=SummationTerm.PLUS,
                data_series=add_ds)
            add_data_series_ids.append(add_ds.id)
        # Remove those no longer required.
        self.terms.filter(
            sign=SummationTerm.PLUS).exclude(
            data_series__in=add_data_series_ids).delete()

        # Ensure data series to be subtracted in this summation are stored.
        subtract_data_series_ids = []
        for subtract_ds in self.minus_data_series:
            self.terms.get_or_create(
                sign=SummationTerm.MINUS,
                data_series=subtract_ds)
            subtract_data_series_ids.append(subtract_ds.id)
        # Remove those, no longer required.
        self.terms.filter(
            sign=SummationTerm.MINUS).exclude(
            data_series__in=subtract_data_series_ids).delete()

    def _set_plus_data_series(self, ds_list):
        self._plus_data_series = ds_list

    def _get_plus_data_series(self):
        if not hasattr(self, '_plus_data_series'):
            self._plus_data_series = [
                ds.subclass_instance for ds in
                DataSeries.objects.filter(
                    summationterm__sign=SummationTerm.PLUS,
                    summationterm__summation=self)]
        return self._plus_data_series

    plus_data_series = property(_get_plus_data_series, _set_plus_data_series)

    def _set_minus_data_series(self, ds_list):
        self._minus_data_series = ds_list

    def _get_minus_data_series(self):
        if not hasattr(self, '_minus_data_series'):
            self._minus_data_series = [
                ds.subclass_instance for ds in
                DataSeries.objects.filter(
                    summationterm__sign=SummationTerm.MINUS,
                    summationterm__summation=self)]
        return self._minus_data_series

    minus_data_series = property(_get_minus_data_series,
                                 _set_minus_data_series)

    def get_included_data_series(self):
        return itertools.chain(
            self.plus_data_series,
            self.minus_data_series)

    def calculate_development(self, from_timestamp, to_timestamp):
        result_quantity = PhysicalQuantity(0, self.unit)
        result_cachable = True
        result_extrapolated = False

        for pds in self.plus_data_series:
            s = pds.calculate_development(from_timestamp, to_timestamp)
            if s is None:
                result_cachable = False
                result_extrapolated = True
            else:
                result_cachable = s.cachable and result_cachable
                result_extrapolated = s.extrapolated or result_extrapolated
                result_quantity = result_quantity + s.physical_quantity

        for pds in self.minus_data_series:
            s = pds.calculate_development(from_timestamp, to_timestamp)
            if s is None:
                result_cachable = False
                result_extrapolated = True
            else:
                result_cachable = s.cachable and result_cachable
                result_extrapolated = s.extrapolated or result_extrapolated
                result_quantity = result_quantity - s.physical_quantity

        return self.create_range_sample(
            from_timestamp, to_timestamp, result_quantity,
            uncachable=not result_cachable, extrapolated=result_extrapolated)

    def _get_samples(self, from_timestamp, to_timestamp):
        """
        C{Summation} implementation of L{DataSeries.get_raw_data_samples()}.
        """
        data_series_list = self.get_included_data_series()

        zero = PhysicalQuantity(0, self.unit)

        for sample_vector in InterpolationCloud(data_series_list,
                                                from_timestamp, to_timestamp):
            t = None
            for sample in sample_vector:
                if sample is not None:
                    t = sample.timestamp
                    break
            if t is None:
                break

            quantities = [getattr(s, 'physical_quantity', zero) for
                          s in sample_vector]
            plus_quantities = quantities[:len(self.plus_data_series)]
            minus_quantities = quantities[len(self.plus_data_series):]
            physical_quantity = (sum(plus_quantities,
                                     -1 * sum(minus_quantities, zero)))

            uncachable = any(
                (sample is None or sample.uncachable for
                 sample in sample_vector))

            extrapolated = any(
                (sample is None or sample.extrapolated for
                 sample in sample_vector))
            yield Sample(t, t, physical_quantity, not uncachable, extrapolated)

    def depends_on(self):
        """
        C{Summation} implementation of L{DataSeries.depends_on()}.
        """
        if self.id:
            deps = []
            for ds in self.get_included_data_series():
                deps.append(ds)
                for dep in ds.depends_on():
                    deps.append(dep)
            return deps
        else:
            return []

    def _get_condensed_samples(
            self, from_timestamp, sample_resolution, to_timestamp):
        plus_data = [
            Stream(ds.get_condensed_samples(
                from_timestamp, sample_resolution, to_timestamp))
            for ds in self.plus_data_series
        ]
        minus_data = [
            Stream(ds.get_condensed_samples(
                from_timestamp, sample_resolution, to_timestamp))
            for ds in self.minus_data_series
        ]
        all_data = plus_data + minus_data
        zero = PhysicalQuantity(0, self.unit)
        while True:
            uncachable = False
            extrapolated = False
            next_samples = [
                elem.peek() for elem in all_data if elem.peek() is not None]
            if not next_samples:
                break
            from_timestamp = min(
                [sample.from_timestamp for sample in next_samples])
            to_timestamp = from_timestamp + sample_resolution
            val = zero
            for elem in plus_data:
                if getattr(elem.peek(), 'from_timestamp', None) == \
                        from_timestamp:
                    sample = elem.next()
                    assert sample.from_timestamp == from_timestamp
                    assert sample.to_timestamp == to_timestamp
                    val += sample.physical_quantity
                    extrapolated = extrapolated or sample.extrapolated
                    uncachable = uncachable or sample.uncachable
            for elem in minus_data:
                if getattr(elem.peek(), 'from_timestamp', None) == \
                        from_timestamp:
                    sample = elem.next()
                    assert sample.from_timestamp == from_timestamp
                    assert sample.to_timestamp == to_timestamp
                    val -= sample.physical_quantity
                    extrapolated = extrapolated or sample.extrapolated
                    uncachable = uncachable or sample.uncachable
            yield self.create_range_sample(
                from_timestamp, to_timestamp, val, uncachable, extrapolated)

    def _condense_data_samples_recursive(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        C{Summation} override of the L{DataSeries} method.
        """
        data_series_list = self.get_included_data_series()

        zero = PhysicalQuantity(0, self.unit)

        sample_vectors = itertools.izip_longest(
            *[
                iter(ds.get_condensed_samples(
                    from_timestamp, sample_resolution, to_timestamp)) for
                ds in data_series_list])

        for sample_vector in sample_vectors:
            from_t = None
            to_t = None
            for sample in sample_vector:
                if sample is not None:
                    from_t = sample.from_timestamp
                    to_t = sample.to_timestamp
                    break
            if from_t is None:
                assert to_t is None
                break

            quantities = [getattr(s, 'physical_quantity', zero) for
                          s in sample_vector]
            plus_quantities = quantities[:len(self.plus_data_series)]
            minus_quantities = quantities[len(self.plus_data_series):]

            physical_quantity = (sum(plus_quantities,
                                     -1 * sum(minus_quantities, zero)))

            uncachable = any(
                (sample is None or sample.uncachable for
                 sample in sample_vector))

            extrapolated = any(
                (sample is None or sample.extrapolated for
                 sample in sample_vector))

            yield self.create_range_sample(
                from_t, to_t, physical_quantity, uncachable, extrapolated)

    def get_recursive_condense_resolution(self, resolution):
        if condense.is_finer_resolution(resolution, condense.HOURS):
            return None
        else:
            return condense.next_resolution(resolution)


class SummationTerm(models.Model):
    """
    A C{SummationTerm} associates a L{DataSeries} with a C{SumInclusionPeriod}.

    @ivar sign: The sign used to include the given L{DataSeries} in the sum.

    @ivar summation: The C{Summation} the given L{DataSeries} should be
    included in.

    @ivar data_series. The given L{dataSeries} to include in the sum.
    """
    PLUS = 1
    MINUS = 2
    SIGN_CHOICES = (
        (PLUS, '+'),
        (MINUS, '-'))

    sign = models.IntegerField(choices=SIGN_CHOICES)
    summation = models.ForeignKey(Summation, on_delete=models.CASCADE,
                                  related_name='terms')
    data_series = models.ForeignKey(DataSeries, on_delete=models.PROTECT)

    class Meta:
        app_label = 'measurementpoints'

    def __repr__(self):
        return '<SummationTerm(sign=%r, period=%r, data_series=%r)>' % (
            self.sign, self.period, self.data_series)
