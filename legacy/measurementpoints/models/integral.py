# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import operator
import itertools

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import condense
from gridplatform.utils.iter_ext import pairwise
from gridplatform.utils.iter_ext import count_extended

from .dataseries import DataSeries
from .dataseries import UndefinedSamples
from .mixins import CacheOptimizedCalculateDevelopmentMixin


class PiecewiseConstantIntegral(CacheOptimizedCalculateDevelopmentMixin,
                                DataSeries):
    """
    A C{PiecewiseConstantIntegral} is a L{DataSeries} that represent the
    definite integral of a piecewise constant L{DataSeries}, C{data}.
    """
    data = models.ForeignKey(
        DataSeries,
        related_name='piecewise_constant_integrals_set')

    class Meta(DataSeries.Meta):
        verbose_name = _('piecewise constant integral')
        verbose_name_plural = _('piecewise constant integrals')
        app_label = 'measurementpoints'

    def save(self, *args, **kwargs):
        assert PhysicalQuantity.compatible_units(
            self.unit, 'second*' + self.data.unit)
        assert self.data.role in self.PIECEWISE_CONSTANT_RATE_ROLES
        super(PiecewiseConstantIntegral, self).save(*args, **kwargs)

    def clean_fields(self, exclude=None):
        def should_clean_field(field_name):
            return not (exclude and field_name in exclude)

        if self.data:
            if should_clean_field('utility_type'):
                self.utility_type = self.data.utility_type
            if should_clean_field('customer'):
                self.customer_id = self.data.customer_id
            if should_clean_field('unit'):
                self.unit = self.data.unit + '*second'

        super(PiecewiseConstantIntegral, self).clean_fields(exclude=exclude)

    def _integrate_sample(
            self, sample, from_timestamp=None, to_timestamp=None):
        if from_timestamp is None or from_timestamp < sample.from_timestamp:
            from_timestamp = sample.from_timestamp
        if to_timestamp is None or to_timestamp > sample.to_timestamp:
            to_timestamp = sample.to_timestamp
        return (
            sample.physical_quantity *
            PhysicalQuantity(
                (to_timestamp - from_timestamp).total_seconds(),
                'second'))

    def _calculate_development_fallback(self, from_timestamp, to_timestamp):
        """
        Override of L{CacheOptimizedCalculateDevelopmentMixin.
        _calculate_development_fallback()}, because parent class'
        C{calculate_development()} does not do the right thing.
        """
        data_samples = list(
            self.data.subclass_instance.get_samples(
                from_timestamp, to_timestamp))

        if not data_samples:
            return None

        integral_quantity = reduce(
            operator.add,
            (self._integrate_sample(sample) for sample in data_samples))

        integral_cachable = all(
            sample.cachable for sample in data_samples)

        integral_extrapolated = any(
            sample.extrapolated for sample in data_samples)

        return self.create_range_sample(
            from_timestamp,
            to_timestamp,
            physical_quantity=integral_quantity,
            uncachable=not integral_cachable,
            extrapolated=integral_extrapolated)

    def depends_on(self):
        return [self.data.subclass_instance] + \
            self.data.subclass_instance.depends_on()

    def _get_samples(self, from_timestamp, to_timestamp):
        raise UndefinedSamples('This is a definite integral')

    def get_recursive_condense_resolution(self, resolution):
        # Computations not assumed to be harder than loading hours cache.
        # Therefore recursion is stopped at days resolution.
        if condense.is_coarser_resolution(resolution, condense.DAYS):
            return condense.next_resolution(resolution)
        else:
            return None

    def _condense_accumulation_data_samples(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        Override of C{DataSeries._condense_accumulation_data_samples()}
        """
        timezone = from_timestamp.tzinfo

        def extract_frame_start(sample):
            return condense.floor(
                sample.from_timestamp, sample_resolution, timezone)

        def frame_timestamps(from_timestamp, to_timestamp):
            return pairwise(
                itertools.takewhile(
                    lambda t: t <= to_timestamp,
                    count_extended(from_timestamp, sample_resolution)))

        def chop_samples(samples):
            for s in samples:
                first_frame_start = condense.floor(
                    s.from_timestamp, sample_resolution, from_timestamp.tzinfo)
                last_frame_end = condense.ceil(
                    s.to_timestamp, sample_resolution, from_timestamp.tzinfo)

                frames = frame_timestamps(first_frame_start, last_frame_end)

                for frame_start, frame_end in frames:
                    chopped_sample_start = max(s.from_timestamp, frame_start)
                    chopped_sample_end = min(s.to_timestamp, frame_end)
                    chopped_sample = s._replace(
                        from_timestamp=chopped_sample_start,
                        to_timestamp=chopped_sample_end)
                    yield chopped_sample

        data_samples = list(chop_samples(
            self.data.subclass_instance.get_samples(
                from_timestamp, to_timestamp)))

        if data_samples:

            domain_start = condense.floor(
                data_samples[0].from_timestamp, sample_resolution,
                from_timestamp.tzinfo)
            domain_end = condense.ceil(
                data_samples[-1].to_timestamp, sample_resolution,
                from_timestamp.tzinfo)

            for frame_start, frame_end in frame_timestamps(from_timestamp,
                                                           domain_start):
                yield self.create_range_sample(
                    frame_start, frame_end, PhysicalQuantity(0, self.unit),
                    uncachable=True, extrapolated=True)

            # assumes each data sample is contained in a signle frame.
            frames = itertools.groupby(data_samples, extract_frame_start)
            for frame_start, frame_samples in frames:
                frame_samples = list(frame_samples)
                assert frame_samples
                frame_quantity = reduce(
                    operator.add,
                    (
                        self._integrate_sample(
                            sample, frame_start,
                            frame_start + sample_resolution) for
                        sample in frame_samples))

                frame_cachable = all(
                    sample.cachable for sample in frame_samples)
                frame_extrapolated = any(
                    sample.extrapolated for sample in frame_samples)

                assert from_timestamp <= frame_start
                assert frame_start + sample_resolution <= to_timestamp
                frame_sample = self.create_range_sample(
                    frame_start,
                    frame_start + sample_resolution,
                    physical_quantity=frame_quantity,
                    uncachable=not frame_cachable,
                    extrapolated=frame_extrapolated)
                yield frame_sample

            for frame_start, frame_end in frame_timestamps(domain_end,
                                                           to_timestamp):
                yield self.create_range_sample(
                    frame_start, frame_end, PhysicalQuantity(0, self.unit),
                    uncachable=True, extrapolated=True)

        else:
            assert not data_samples
            for frame_start, frame_end in frame_timestamps(
                    from_timestamp, to_timestamp):
                yield self.create_range_sample(
                    frame_start, frame_end, PhysicalQuantity(0, self.unit),
                    uncachable=True, extrapolated=True)
