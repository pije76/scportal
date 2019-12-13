# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from model_utils import FieldTracker

from gridplatform.customer_datasources.models import DataSource
from gridplatform.datasources.models import RawData
from gridplatform.utils import deprecated
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.units import NONACCUMULATION_BASE_UNITS
from gridplatform.utils.units import NONACCUMULATION_BASE_UNIT_CHOICES
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.samples import Sample

from .base import DataSequenceBase
from .base import PeriodBase


class NonaccumulationDataSequence(DataSequenceBase):
    """
    Data sequence class for sequences of continuous :class:`.PointSample`.

    :ivar unit: The unit of this :class:`.NonaccumulationDataSequence`.

    :see: :ref:`sequences-of-continuous-point-samples`
    """

    # Do not update:
    unit = BuckinghamField(choices=NONACCUMULATION_BASE_UNIT_CHOICES)

    tracker = FieldTracker(fields=['unit'])

    class Meta:
        verbose_name = _('nonaccumulation data sequence')
        verbose_name_plural = _('nonaccumulation data sequences')
        app_label = 'datasequences'

    def clean(self):
        """
        :raise ValidationError:  If ``self.unit`` is updated.
        """
        super(NonaccumulationDataSequence, self).clean()
        previous_unit = self.tracker.previous('unit')
        if previous_unit is not None:
            if not PhysicalQuantity.compatible_units(previous_unit, self.unit):
                raise ValidationError(
                    {
                        'unit': [
                            ugettext('Field cannot be updated.'),
                        ]})

    def raw_sequence(self, from_timestamp, to_timestamp):
        """
        :return: A sequence of continuous :class:`.PointSample` in the given
            timespan.
        :param from_timestamp:  The start of the given timespan.
        :param to_timestamp:  The end of the given timespan.
        """
        for period in self.period_set.in_range(
                from_timestamp, to_timestamp).order_by('from_timestamp'):
            period_from, period_to = period.overlapping(
                from_timestamp, to_timestamp)
            for sample in period._raw_sequence(period_from, period_to):
                yield sample

    @deprecated
    def _get_samples(self, from_timestamp, to_timestamp):
        input_periods = self.period_set.in_range(
            from_timestamp, to_timestamp).order_by('from_timestamp')

        for input_period in input_periods:
            for sample in input_period.get_samples(
                    max(from_timestamp, input_period.from_timestamp),
                    min(to_timestamp, input_period.to_timestamp)):
                if sample.timestamp != input_period.to_timestamp or \
                        input_period.to_timestamp == to_timestamp:
                    yield sample


class NonaccumulationPeriod(PeriodBase):
    """
    A :class:`.PeriodBase` specialization defining the continuous
    :class:`PointSample` of a :class:`.NonaccumulationDataSequence` within its
    period in terms of a :class:`.DataSource`.
    """
    datasequence = models.ForeignKey(
        NonaccumulationDataSequence,
        verbose_name=_('data sequence'),
        related_name='period_set')
    datasource = models.ForeignKey(
        DataSource,
        verbose_name=_('data source'),
        limit_choices_to={'unit__in': NONACCUMULATION_BASE_UNITS},
        on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('nonaccumulation period')
        verbose_name_plural = _('nonaccumulation periods')
        app_label = 'datasequences'

    # HACK
    @property
    def subclass_instance(self):
        return self

    def _raw_sequence(self, from_timestamp, to_timestamp):
        """
        Delegate method for :meth:`.NonaccumulationDataSequence.raw_sequence`
        within this :class:`.NonaccumulationPeriod`.
        """
        for timestamp, value in self.datasource.rawdata_set.filter(
                timestamp__gte=from_timestamp,
                timestamp__lte=to_timestamp).order_by('timestamp').values_list(
                    'timestamp', 'value'):
            yield Sample(
                timestamp, timestamp,
                PhysicalQuantity(value, self.datasource.unit),
                False, False)

    @deprecated
    def _get_samples_pure_implementation(self, from_timestamp, to_timestamp):
        assert hasattr(self, 'datasource')
        assert from_timestamp <= to_timestamp

        raw_data_iterator = iter(
            self.datasource.rawdata_set.filter(
                timestamp__gte=max(from_timestamp, self.from_timestamp),
                timestamp__lte=min(to_timestamp, self.to_timestamp)))

        try:
            first_raw_data = next(raw_data_iterator)
        except StopIteration:
            leading_raw_data = self._get_leading_raw_data(from_timestamp)
            following_raw_data = self._get_following_raw_data(to_timestamp)
            if leading_raw_data is not None and following_raw_data is not None:
                if from_timestamp == to_timestamp:
                    # single sample interpolated
                    yield self._interpolate_sample(
                        from_timestamp, leading_raw_data, following_raw_data)
                else:
                    # two samples interpolated
                    yield self._interpolate_sample(
                        from_timestamp, leading_raw_data, following_raw_data)
                    yield self._interpolate_sample(
                        to_timestamp, leading_raw_data, following_raw_data)
            return

        # yield sample before first raw data if missing
        if first_raw_data.timestamp != from_timestamp:
            leading_raw_data = self._get_leading_raw_data(from_timestamp)
            if leading_raw_data:
                yield self._interpolate_sample(
                    from_timestamp, leading_raw_data, first_raw_data)

        # yield the sample of the first raw data
        yield self.create_point_sample(
            first_raw_data.timestamp,
            PhysicalQuantity(first_raw_data.value, self.unit))
        final_raw_data = first_raw_data

        # yield samples for remaining raw data
        for raw_data in raw_data_iterator:
            yield self.create_point_sample(
                raw_data.timestamp,
                PhysicalQuantity(raw_data.value, self.unit))
            final_raw_data = raw_data

        # yield final sample after final raw data if missing
        if final_raw_data.timestamp != to_timestamp:
            following_raw_data = self._get_following_raw_data(to_timestamp)
            if following_raw_data:
                yield self._interpolate_sample(
                    to_timestamp, final_raw_data, following_raw_data)

    @deprecated
    def _get_samples(self, from_timestamp, to_timestamp):
        return self._get_samples_pure_implementation(
            from_timestamp, to_timestamp)

    # HACK: copy from legacy.py
    @deprecated
    def get_samples(self, from_timestamp, to_timestamp):
        assert from_timestamp <= to_timestamp
        assert from_timestamp >= self.from_timestamp
        assert to_timestamp <= self.to_timestamp
        return self._get_samples(from_timestamp, to_timestamp)

    # HACK: copy from legacy.py
    @deprecated
    def create_point_sample(self, timestamp, physical_quantity,
                            cachable=True, extrapolated=False):
        return Sample(
            timestamp,
            timestamp,
            physical_quantity,
            cachable,
            extrapolated)

    # HACK: copy from legacy.py
    def _get_unit(self):
        return self.datasource.unit

    # HACK: copy from legacy.py
    @deprecated
    def _get_leading_raw_data(self, timestamp):
        assert hasattr(self, 'datasource')
        # last before or None
        return self.datasource.rawdata_set.filter(
            timestamp__lt=timestamp).order_by('timestamp').last()

    # HACK: copy from legacy.py
    @cached_property
    @deprecated
    def _leading_raw_data(self):
        assert hasattr(self, 'datasource')
        return self._get_leading_raw_data(self.from_timestamp)

    # HACK: copy from legacy.py
    @deprecated
    def _get_following_raw_data(self, timestamp):
        assert hasattr(self, 'datasource')
        # first after or None
        return self.datasource.rawdata_set.filter(
            timestamp__gt=timestamp).order_by('timestamp').first()

    # HACK: copy from legacy.py
    @cached_property
    @deprecated
    def _first_raw_data(self):
        assert hasattr(self, 'datasource')
        return self.datasource.rawdata_set.filter(
            timestamp__gte=self.from_timestamp,
            timestamp__lte=self.to_timestamp).order_by('timestamp').first()

    # HACK: copy from legacy.py
    @deprecated
    def _interpolate_sample(self, timestamp, raw_data_before, raw_data_after):
        return self.create_point_sample(
            timestamp,
            PhysicalQuantity(
                RawData.interpolate(
                    timestamp,
                    raw_data_before,
                    raw_data_after),
                self.unit))
