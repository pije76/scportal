# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property

from gridplatform.consumptions.models import MainConsumption
from gridplatform.datasources.models import DataSource
from gridplatform.datasequences.models import PiecewiseConstantPeriodManager
from gridplatform.datasequences.models.piecewiseconstant import FixedPiecewiseConstantPeriodValueSequenceMixin  # noqa
from gridplatform.datasequences.models.base import is_five_minute_multiplum
from gridplatform.utils.models import TimestampRangeModelMixin
from gridplatform.utils.models import StoreSubclass
from gridplatform.utils.decorators import virtual
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.validators import clean_overlapping
from gridplatform.utils import units
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.samples import RangedSample
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils import condense


class Co2ConversionManager(PiecewiseConstantPeriodManager):
    use_for_related_fields = True

    def value_sequence(self, from_timestamp, to_timestamp):
        """
        Yield ``RangedSample``s in five-minute resolution.
        """
        for sample in super(Co2ConversionManager, self).value_sequence(
                from_timestamp, to_timestamp):
            assert RelativeTimeDelta(
                sample.to_timestamp, sample.from_timestamp) == \
                RelativeTimeDelta(minutes=5)
            yield sample


class Co2Conversion(TimestampRangeModelMixin, StoreSubclass):
    """
    Base class for defining CO₂ conversions of a
    :py:class:`gridplatform.consumptions.models.MainConsumption`
    within a timestamp range.

    CO₂ conversion samples are ``RangedSamples`` with a five minute
    duration.

    :ivar mainconsumption: The ``MainConsumption`` for which this
        instance defines CO₂ conversions.

    :ivar from_timestamp: The start of the timestamp range.

    :ivar to_timestamp: The end of the timestamp range.
    """

    mainconsumption = models.ForeignKey(
        MainConsumption, verbose_name=_('main consumption'))

    objects = Co2ConversionManager()

    class Meta:
        verbose_name = _('CO₂ conversion')
        verbose_name = _('CO₂ conversions')

    def clean(self):
        """
        :raises ValidationError: if timestamp range overlaps with that of
            another ``Co2Conversion`` for the same ``mainconsumption``.

        :raises ValidationError: if ``self.from_timestamp`` is not in
            five-minute resolution.

        :raises ValidationError: if ``self.to_timestamp`` is not in
            five-minute resolution.
        """
        super(Co2Conversion, self).clean()
        if self.from_timestamp:
            # NOTE: does not support formset validation.  See how that is done
            # in PeriodBase.
            co2conversions = [
                co2conversion
                for co2conversion
                in self.mainconsumption.co2conversion_set.all()
                if co2conversion.id != self.id]
            co2conversions.append(self)
            clean_overlapping(co2conversions)

        if self.from_timestamp and not is_five_minute_multiplum(
                self.from_timestamp):
            raise ValidationError(
                {
                    'from_timestamp': [
                        ugettext(
                            'Timestamp must be in five-minute resolution.')]})

        if self.to_timestamp and not is_five_minute_multiplum(
                self.to_timestamp):
            raise ValidationError(
                {
                    'to_timestamp': [
                        ugettext(
                            'Timestamp must be in five-minute resolution.')]})

    def unit_is_valid(self, unit):
        return (
            PhysicalQuantity(1, unit) *
            PhysicalQuantity(
                1, self.mainconsumption.utility_unit)).compatible_unit('gram')

    def __unicode__(self):
        timezone = self.mainconsumption.customer.timezone
        return self.format_timestamp_range_unicode(
            self._get_description(), timezone)

    @virtual
    def _value_sequence(self, from_timestamp, to_timestamp):
        """
        :return: A sequence of conversion ranged samples with five-minute
            durations, each specifying how utility consumptions within
            their time range is converted to CO₂ emissions.

        :param from_timestamp: Marks the beginning of the returned
            sequence.

        :param to_timestamp: Marks the end of the returned sequence.
        """
        raise NotImplementedError(self.__class__)

    @virtual
    def _get_description(self):
        raise NotImplementedError(self.__class__)


class DynamicCo2Conversion(Co2Conversion):
    """
    A CO₂ conversion defined in terms of a
    :py:class:`gridplatform.datasources.models.DataSource`.

    :ivar datasource: The ``DataSource`` in terms of which this
        ``DynamicCo2Conversion`` is defined.
    """
    datasource = models.ForeignKey(
        DataSource,
        limit_choices_to=models.Q(unit__in=units.CO2_CONVERSION_BASE_UNITS),
        verbose_name=_('data source'))

    class Meta:
        verbose_name = _('dynamic CO₂ conversion')
        verbose_name_plural = _('dynamic CO₂ conversions')

    def clean(self):
        """
        :raises ValidationError: if ``self.datasource.unit`` is incompatible with
            ``self.mainconsumption.unit``
        """
        super(DynamicCo2Conversion, self).clean()
        if hasattr(self, 'datasource') and not self.unit_is_valid(
                self.datasource.unit):
            raise ValidationError(
                {
                    'datasource': [
                        ugettext(
                            'Invalid data source for utility unit of '
                            'main consumption.')]})

    def _value_sequence(self, from_timestamp, to_timestamp):
        rawdata = self.datasource.rawdata_set.filter(
            timestamp__gte=from_timestamp,
            timestamp__lt=to_timestamp).order_by(
                'timestamp').values_list('timestamp', 'value')
        for timestamp, value in rawdata:
            yield RangedSample(
                timestamp,
                timestamp + RelativeTimeDelta(minutes=5),
                PhysicalQuantity(value, self.datasource.unit))

    def _get_description(self):
        return unicode(self.datasource)


class FixedCo2Conversion(
        FixedPiecewiseConstantPeriodValueSequenceMixin, Co2Conversion):
    """
    A CO₂ conversion defined from a fixed factor.

    :ivar value: The value of the fixed factor.
    :ivar unit: The unit of the fixed factor.
    """
    value = models.DecimalField(_('value'), max_digits=12, decimal_places=3)
    unit = BuckinghamField(_('unit'), choices=units.CO2_CONVERSION_CHOICES)

    resolution = condense.FIVE_MINUTES

    class Meta:
        verbose_name = _('fixed CO₂ conversion')
        verbose_name_plural = _('fixed CO₂ conversions')

    def clean(self):
        """
        :raises ValidationError: if ``self.unit`` is incompatible with
            ``self.mainconsumption.unit``
        """
        super(FixedCo2Conversion, self).clean()
        if self.unit and not self.unit_is_valid(self.unit):
            raise ValidationError(
                {
                    'unit': [
                        ugettext(
                            'Invalid unit for utility unit of '
                            'main consumption.')]})

    def _get_description(self):
        return '%s %s' % (self.value, self.get_unit_display())

    @cached_property
    def _quantity(self):
        return PhysicalQuantity(self.value, self.unit)
