# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from fractions import Fraction

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.core.exceptions import ValidationError

from gridplatform.utils.samples import Sample
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import units
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.fields import BigAutoField
from gridplatform.utils.units import BASE_UNIT_CHOICES
from gridplatform.utils.models import StoreSubclass
from gridplatform.utils.decorators import virtual

from .managers import DataSourceManager


def interpolate(timestamp, point_a, point_b):
    timestamp_a, value_a = point_a
    timestamp_b, value_b = point_b
    assert timestamp_a <= timestamp < timestamp_b
    assert timestamp.microsecond == 0
    assert timestamp_a.microsecond == 0
    assert timestamp_b.microsecond == 0
    return value_a + (value_b - value_a) * \
        Fraction(int((timestamp - timestamp_a).total_seconds()),
                 int((timestamp_b - timestamp_a).total_seconds()))


def impulse_interpolate(timestamp, point_a, point_b):
    timestamp_a, value_a = point_a
    timestamp_b, value_b = point_b
    assert timestamp_a <= timestamp < timestamp_b
    assert timestamp.microsecond == 0
    assert timestamp_a.microsecond == 0
    assert timestamp_b.microsecond == 0
    return value_a


class DataSourceBase(models.Model):
    unit = BuckinghamField(_('unit'), choices=BASE_UNIT_CHOICES)
    hardware_id = models.CharField(
        _('hardware id'), max_length=120, blank=True)

    class Meta:
        abstract = True

    def hourly_accumulated(self, from_timestamp, to_timestamp):
        """
        Yields :class:`~gridplatform.utils.samples.RangedSample` with a duration of
        one hour in the given range.  Each sample yielded holds the development
        of the accumulation across the timespan of the sample.

        :param from_timestamp: The start of the given range.
        :param to_timestamp: The end of the given range.
        """
        from gridplatform.condensing.models import get_hourly_accumulated
        return get_hourly_accumulated(self, from_timestamp, to_timestamp)

    def five_minute_accumulated(self, from_timestamp, to_timestamp):
        """
        Yields :class:`~gridplatform.utils.samples.RangedSample` with a duration of
        five minutes in the given range.  Each sample yielded holds the
        development of the accumulation across the timespan of the sample.

        :param from_timestamp: The start of the given range.
        :param to_timestamp: The end of the given range.
        """
        from gridplatform.condensing.models import get_five_minute_accumulated
        return get_five_minute_accumulated(self, from_timestamp, to_timestamp)

    def _get_interpolate_fn(self):
        """
        :return: :func:`.impulse_interpolate` if ``self.unit`` is 'impulse' and
            :func:`.interpolate` otherwise.
        """
        if self.unit == 'impulse':
            return impulse_interpolate
        else:
            return interpolate

    def raw_sequence(self, from_timestamp, to_timestamp):
        """
        Yields :class:`~gridplatform.utils.samples.PointSample` for each
        :class:`.RawData` in the given range.

        :param from_timestamp: The start of the given range.
        :param to_timestamp: The end of the given range.
        """
        for timestamp, value in self.rawdata_set.filter(
                timestamp__gte=from_timestamp,
                timestamp__lte=to_timestamp).order_by('timestamp').values_list(
                    'timestamp', 'value'):
            yield Sample(
                timestamp, timestamp,
                PhysicalQuantity(value, self.unit),
                False, False)

    def next_valid_date(self, date, timezone):
        """
        :return: The next date that holds :class:`.RawData` for this data source or
            ``None``.

        :param date:  The date after which `next valid date` is found.
        :param timezone: :class:`.RawData` are stored using timestamps, so to
            translate a date to a timestamp range we need a timezone; this is
            the timezone.
        """
        end_of_day = timezone.localize(
            datetime.datetime.combine(
                date + datetime.timedelta(days=1), datetime.time()))
        next_rawdata = self.rawdata_set.filter(
            timestamp__gt=end_of_day).order_by('timestamp').first()
        if next_rawdata is not None:
            return timezone.normalize(
                next_rawdata.timestamp.astimezone(timezone)).date()
        else:
            return None

    def previous_valid_date(self, date, timezone):
        """
        :return: The previous date that holds :class:`.RawData` for this data
            source or ``None``.

        :param date:  The date before which `previous valid date` is found.
        :param timezone: :class:`.RawData` are stored using timestamps, so to
            translate a date to a timestamp range we need a timezone; this is
            the timezone.
        """
        beginning_of_day = timezone.localize(
            datetime.datetime.combine(date, datetime.time()))
        previous_rawdata = self.rawdata_set.filter(
            timestamp__lt=beginning_of_day).order_by('timestamp').last()
        if previous_rawdata is not None:
            return timezone.normalize(
                previous_rawdata.timestamp.astimezone(timezone)).date()
        else:
            None


class RawDataBase(models.Model):
    id = BigAutoField(primary_key=True)
    value = models.BigIntegerField(_('value'))
    timestamp = models.DateTimeField(_('timestamp'))

    class Meta:
        abstract = True

    @staticmethod
    def interpolate(timestamp, raw_data_before, raw_data_after):
        """
        :return: Returns an interpolated value at the given ``timestamp``
            interpolated from ``raw_data_before`` and ``raw_data_after``.

        :precondition: The open interval (``raw_data_before.timestamp``;
            ``raw_data_after.timestamp``) contains ``timestamp``.
        """
        assert raw_data_before.timestamp < timestamp
        assert raw_data_after.timestamp > timestamp
        return interpolate(
            timestamp.replace(microsecond=0),
            (raw_data_before.timestamp.replace(microsecond=0),
             raw_data_before.value),
            (raw_data_after.timestamp.replace(microsecond=0),
             raw_data_after.value))

    @property
    def unit(self):
        if self.id:
            return self.datasource.unit
        return None


class DataSource(StoreSubclass, DataSourceBase):
    """
    :class:`.DataSource` is the base class for
    :class:`~gridplatform.customer_datasources.models.CustomerDataSource`,
    :class:`~gridplatform.provider_datasources.models.ProviderDataSource` and
    :class:`~gridplatform.global_datasources.models.GlobalDataSource`.

    :ivar rawdata_set: The data of data sources are stored as
        :class:`.RawData`.

        However, accessing the raw data directly via the ``rawdata_set``
        manager is rarely needed.  Use :meth:`.hourly_accumulated` and
        :meth:`.five_minute_accumulated` for accumulated data and
        :meth:`~gridplatform.datasources.models.DataSource.raw_sequence`
        for raw data. All these methods will yield samples which are more
        lightwight than
        :class:`.RawData`, and case of accumulated data fewer samples will
        be yielded than the amount of potential :class:`.RawData` in the same
        range.

    :see: :class:`gridplatform.utils.samples.RangedSample` and
        :class:`gridplatform.utils.samples.PointSample`.

    :ivar unit: A Buckingham unit that holds for all the :class:`RawData`
        associated with this data source.

    :ivar hardware_id: A char field used by external components (say REST
        enabled meters) to identify this data source.

    :cvar objects: A :class:`.DataSourceManager` that ensures that noone gets
        their hands on data sources that they shouldn't see.  Note that this
        manager is not inherited and will not work on any subclass model.
    """
    objects = DataSourceManager()

    class Meta:
        verbose_name = _('data source')
        verbose_name_plural = _('data sources')

    @virtual
    def __unicode__(self):
        raise NotImplementedError(self.__class__)


def is_clock_hour(timestamp):
    return timestamp.minute == timestamp.second == timestamp.microsecond == 0


def is_five_minute_multiplum(timestamp):
    return timestamp.minute % 5 == timestamp.second == \
        timestamp.microsecond == 0


class RawData(RawDataBase):
    """
    Used for storing raw data of data sources.

    :ivar value: The value of this raw data.  Can be converted to a
        :class:`gridplatform.utils.unitconversion.PhysicalQuantity` using
        :attr:`.DataSource.unit`.

    :ivar timestamp: A timestamp describing when this raw data was sampled.

    :ivar datasource:  The owning :class:`.DataSource`.
    """
    datasource = models.ForeignKey(
        DataSource,
        verbose_name=_('data source'),
        on_delete=models.PROTECT,
        db_index=False)

    class Meta:
        verbose_name = _('raw data')
        verbose_name_plural = _('raw data')
        # NOTE: unique_together creates an index; index_together would create
        # an extra, redundant index
        unique_together = ('datasource', 'timestamp')
        ordering = ['timestamp']

    def clean(self):
        super(RawData, self).clean()
        if hasattr(self, 'datasource') and self.timestamp:
            if any(PhysicalQuantity.compatible_units(
                    self.datasource.unit, unit)
                   for unit in units.TARIFF_BASE_UNITS):
                if not is_clock_hour(self.timestamp):
                    raise ValidationError(
                        {'timestamp': [ugettext('Must be clock hour.')]})

            if any(PhysicalQuantity.compatible_units(
                    self.datasource.unit, unit)
                   for unit in units.CO2_CONVERSION_BASE_UNITS):
                if not is_five_minute_multiplum(self.timestamp):
                    raise ValidationError(
                        {'timestamp': [
                            ugettext('Must be five-minute multiplum.')]})
