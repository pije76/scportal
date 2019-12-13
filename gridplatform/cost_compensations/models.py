# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError

from gridplatform.utils.fields import BuckinghamField
from gridplatform.datasequences.models import piecewiseconstant
from gridplatform.datasequences.models import PiecewiseConstantPeriodManager
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.units import ENERGY_TARIFF_CHOICES
from gridplatform.utils.decorators import virtual
from gridplatform.utils import condense
from gridplatform.utils.relativetimedelta import RelativeTimeDelta


class CostCompensation(piecewiseconstant.PiecewiseConstantBase):
    """
    Cost compensation data sequence.  Defines sequences of conversion ranged
    samples for calculating a cost compensation amount from an energy
    consumption.

    :ivar name: The name of the tariff
    :ivar customer: The customer owning the tariff.
    """

    class Meta:
        verbose_name = _('cost compensation')
        verbose_name_plural = _('cost compensations')

    @cached_property
    def unit(self):
        result = self.customer.currency_unit + '*kilowatt^-1*hour^-1'
        assert any((
            PhysicalQuantity.compatible_units(
                result, 'currency_dkk*kilowatt^-1*hour^-1'),
            PhysicalQuantity.compatible_units(
                result, 'currency_eur*kilowatt^-1*hour^-1')))
        return result


class CostCompensationPeriodManager(PiecewiseConstantPeriodManager):
    """
    Manager defining methods useful for reverse relations to cost compensation
    periods.  E.g.::

        mainconsumption.cost_compensation.period_set.value_sequence()

    The concept is similar to
    :py:class:`gridplatform.tariffs.models.TariffPeriodManager`.
    """

    def value_sequence(self, from_timestamp, to_timestamp):
        """
        A sequence of cost compensation samples of all periods in the given range.

        :param from_timestamp: The start of the given range.
        :param to_timestamp: The end of the given range.
        :return: A sequence of ranged cost compensation samples in one hour
            resolutions.
        """
        for sample in super(
                CostCompensationPeriodManager, self).value_sequence(
                    from_timestamp, to_timestamp):
            assert RelativeTimeDelta(
                sample.to_timestamp, sample.from_timestamp) == \
                RelativeTimeDelta(hours=1)
            yield sample


class Period(piecewiseconstant.PiecewiseConstantPeriodBase):
    """
    Base class for cost compensation periods.

    :ivar datasequence: The aggregating :class:`.CostCompensation`.
    """
    datasequence = models.ForeignKey(
        CostCompensation,
        verbose_name=_('data sequence'),
        editable=False)

    objects = CostCompensationPeriodManager()

    class Meta:
        verbose_name = _('cost compensation period')
        verbose_name_plural = _('cost compensation periods')

    @virtual
    def __unicode__(self):
        raise NotImplementedError(self.__class__)


class FixedCompensationPeriod(
        piecewiseconstant.FixedPiecewiseConstantPeriodValueSequenceMixin,
        Period):
    """
    Specialization of cost compensation
    :class:`~gridplatform.cost_compensations.models.Period` for fixed cost
    compensation.

    :ivar value: The value of the fixed compensation.
    :ivar unit: The unit of the value fo the fixed compensation.
    """

    value = models.DecimalField(_('value'), max_digits=12, decimal_places=3)
    unit = BuckinghamField(_('unit'), choices=ENERGY_TARIFF_CHOICES)
    resolution = condense.HOURS

    class Meta:
        verbose_name = _('fixed compensation period')
        verbose_name_plural = _('fixed compensation periods')

    def __unicode__(self):
        if self.to_timestamp is None:
            return '%s - ...: %s %s' % (
                self.from_timestamp,
                self.value,
                self.get_unit_display())
        else:
            return '%s - %s: %s %s' % (
                self.from_timestamp, self.to_timestamp,
                self.value,
                self.get_unit_display())

    def clean(self):
        """
        :raise ValidationError: if ``self.unit`` is not compatible with the unit of
            aggregating :class:`.CostCompensation`.
        """
        super(FixedCompensationPeriod, self).clean()
        if not PhysicalQuantity.compatible_units(
                self.unit, self.datasequence.unit):
            raise ValidationError(
                {
                    'unit': [
                        ugettext(
                            'Selected unit is not compatible with '
                            'unit of cost compensation.')]
                }
            )

    @cached_property
    def _quantity(self):
        return PhysicalQuantity(self.value, self.unit)
