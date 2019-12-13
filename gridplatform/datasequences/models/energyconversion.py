# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.customer_datasources.models import DataSource
from gridplatform.utils.iter_ext import pairwise_extended
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.units import ENERGY_PER_VOLUME_BASE_UNITS
from gridplatform.utils.samples import RangedSample
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils import condense

from .piecewiseconstant import PiecewiseConstantBase
from .base import PeriodBase
from .base import is_clock_hour
from .base import is_five_minute_multiplum
from .piecewiseconstant import PiecewiseConstantPeriodManagerBase


def _break_into_hourly_samples(ranged_samples, from_timestamp, to_timestamp):
    """
    Yield hourly subsamples (RangedSamples) of each RangedSample in
    ranged_samples
    """
    assert is_five_minute_multiplum(from_timestamp), \
        '%r is not a 5 minute multiplum' % from_timestamp
    assert is_five_minute_multiplum(to_timestamp), \
        '%r is not a 5 minute multiplum' % to_timestamp

    timestamp = from_timestamp
    for sample in ranged_samples:
        while timestamp < sample.from_timestamp:
            timestamp += condense.HOURS
        while timestamp < sample.to_timestamp:
            subsample = sample._replace(
                from_timestamp=timestamp,
                to_timestamp=timestamp + condense.HOURS)
            assert sample.from_timestamp <= subsample.from_timestamp
            assert sample.to_timestamp >= subsample.to_timestamp
            yield subsample

            timestamp = subsample.to_timestamp


class EnergyPerVolumeDataSequence(PiecewiseConstantBase):
    """
    Data sequence for energy conversion.  Inherits from
    :class:`PiecewiseConstantBase`.

    :cvar unit:  The unit is always energy per volume.
    """
    class Meta:
        verbose_name = _('energy conversion data sequence')
        verbose_name_plural = _('energy conversion data sequences')
        app_label = 'datasequences'

    unit = 'milliwatt*hour/meter^3'


class VolumeToEnergyConversionPeriodManager(
        PiecewiseConstantPeriodManagerBase):
    """
    A :class:`.PiecewiseConstantPeriodManagerBase` specialization whose samples
    are always in one-hour resolution.
    """
    use_for_related_fields = True

    def value_sequence(self, from_timestamp, to_timestamp):
        """
        Specialization of
        :meth:`.PiecewiseConstantPeriodManagerBase.value_sequence`.  Yields
        :class:`.RangedSample` in one-hour resolution.
        """
        for sample in super(
                VolumeToEnergyConversionPeriodManager, self).value_sequence(
                    from_timestamp, to_timestamp):
            assert RelativeTimeDelta(
                sample.to_timestamp, sample.from_timestamp) == \
                RelativeTimeDelta(hours=1)
            yield sample


class EnergyPerVolumePeriod(PeriodBase):
    """
    A :class:`.PeriodBase` specialization for
    :class:`.EnergyPerVolumeDataSequence`.  Defines data in terms of a
    :class:`.DataSource`.

    :ivar datasequence: The owning :class:`.EnergyPerVolumeDataSequence`.
    :ivar datasource: The :class:`.DataSource` defining the data sequence
        within this period.
    :cvar objects: The default manager of :class:`.EnergyPerVolumePeriod` is
        :class:`.VolumeToEnergyConversionPeriodManager`.

    :see: :ref:`sequences-of-conversion-ranged-samples`
    """
    datasequence = models.ForeignKey(
        EnergyPerVolumeDataSequence,
        verbose_name=_('data sequence'),
        related_name='period_set')
    datasource = models.ForeignKey(
        DataSource,
        verbose_name=_('data source'),
        limit_choices_to={'unit__in': ENERGY_PER_VOLUME_BASE_UNITS},
        on_delete=models.PROTECT)

    objects = VolumeToEnergyConversionPeriodManager()

    class Meta:
        verbose_name = _('volume to energy conversion period')
        verbose_name_plural = _('volume to energy conversion periods')
        app_label = 'datasequences'

    def _raw_samples(self, from_timestamp, to_timestamp):
        """
        :return: a sequence of conversion ranged samples in the given timespan.
            The conversion samples may have mixed duration, so for efficient
            conversion use :meth:`.EnergyPerVolumePeriod._value_sequence` instead.

        :param from_timestamp: the start of the given timespan.
        :param to_timestamp: the end of the given timespan.
        """
        start = self.datasource.rawdata_set.filter(
            timestamp__lte=from_timestamp
        ).order_by('-timestamp')[0:1].values_list('timestamp', 'value')
        in_period = self.datasource.rawdata_set.filter(
            timestamp__gt=from_timestamp,
            timestamp__lt=to_timestamp
        ).order_by('timestamp').values_list('timestamp', 'value')
        if start:
            raw = [start[0]] + list(in_period)
        else:
            raw = list(in_period)

        for current_raw, next_raw in pairwise_extended(raw):
            sample_from_timestamp, value = current_raw
            if next_raw is None:
                sample_to_timestamp = to_timestamp
            else:
                sample_to_timestamp = next_raw[0]
            yield RangedSample(
                sample_from_timestamp,
                sample_to_timestamp,
                PhysicalQuantity(value, self.datasource.unit))

    def _value_sequence(self, from_timestamp, to_timestamp):
        """
        :return: A sequence of conversion :class:`.RangedSample` in hourly
            resolution in the given timespan.

        :param from_timestamp: the start of the given timespan.
        :param to_timestamp: the end of the given timespan.
        """
        assert is_clock_hour(from_timestamp), \
            '%r does not match clock hour' % from_timestamp
        assert is_clock_hour(to_timestamp), \
            '%r does not match clock hour' % to_timestamp
        data = self._raw_samples(from_timestamp, to_timestamp)
        # For energy conversion the convention is that each RawData defines the
        # conversion quotient until the next raw data value.
        return _break_into_hourly_samples(
            data, from_timestamp, to_timestamp)
