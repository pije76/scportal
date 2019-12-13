# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError
from model_utils import Choices

from gridplatform.datasources.models import DataSource
from gridplatform.datasequences.models import piecewiseconstant
from gridplatform.datasequences.models import PiecewiseConstantPeriodManager
from gridplatform.utils import units
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.decorators import virtual
from gridplatform.utils import sum_or_none
from gridplatform.utils import condense
from gridplatform.utils.samples import Sample
from gridplatform.datasequences.models import CurrencyUnitMixin


class Tariff(CurrencyUnitMixin, piecewiseconstant.PiecewiseConstantBase):
    """
    Base model for tariffs.

    :ivar name: The name of the tariff
    :ivar customer: The customer owning the tariff.
    """

    class Meta:
        verbose_name = _('tariff')
        verbose_name_plural = _('tariff')

    @virtual
    def _unit(self):
        raise NotImplementedError(self.__class__)

    @cached_property
    def unit(self):
        return self._unit()


class EnergyTariff(Tariff):
    """
    Specialization of :py:class:`.Tariff` for energy.
    """
    class Meta:
        verbose_name = _('energy tariff')
        verbose_name_plural = _('energy tariff')

    def _unit(self):
        return self.customer.currency_unit + '*megawatt^-1*hour^-1'


class VolumeTariff(Tariff):
    """
    Specialization of :py:class:`.Tariff` for volume.
    """

    class Meta:
        verbose_name = _('volume tariff')
        verbose_name_plural = _('volume tariff')

    def _unit(self):
        return self.customer.currency_unit + '*meter^-3'


class TariffPeriodManager(PiecewiseConstantPeriodManager):
    """
    Manager defining methods useful for reverse relations to tariff periods.
    E.g.::

        mainconsumption.tariff.period_set.value_sequence()

    or::

        mainconsumption.tariff.period_set.subscription_cost_sum()

    These would of course look nicer if the periods were attached directly to
    the :py:class:`~gridplatform.consumptions.models.MainConsumption`.  E.g.::

        mainconsumption.tariff_set.value_sequence()

    :note: The methods being intended for reverse relations will also polute
        the default manager.  Reverse relation methods that don't work on the
        default manager like this should be avoided, in fact they are
        considered wrong.  Given no obvious means for doing this right a free
        function would be preferred.
    """
    use_for_related_fields = True

    def subscription_cost_sum(self, from_timestamp, to_timestamp):
        """
        :return: The total subscription cost of all periods in the given range.
        :param from_timestamp: The start of the given range.
        :param to_timestamp: The end of the given range.
        """
        periods = self.in_range(from_timestamp, to_timestamp)
        return sum_or_none(
            period.subscription_cost_sum(
                *period.overlapping(from_timestamp, to_timestamp))
            for period in periods)

    def value_sequence(self, from_timestamp, to_timestamp):
        """
        A sequence of tariff samples of all periods in the given range.

        :param from_timestamp: The start of the given range.
        :param to_timestamp: The end of the given range.
        :return: A sequence of ranged tariff samples in one hour resolutions.
        """
        for sample in super(TariffPeriodManager, self).value_sequence(
                from_timestamp, to_timestamp):
            assert RelativeTimeDelta(
                sample.to_timestamp, sample.from_timestamp) == \
                RelativeTimeDelta(hours=1)
            yield sample


class Period(piecewiseconstant.PiecewiseConstantPeriodBase):
    datasequence = models.ForeignKey(
        Tariff,
        verbose_name=_('data sequence'),
        editable=False)

    objects = TariffPeriodManager()

    class Meta:
        verbose_name = _('tariff period')
        verbose_name_plural = _('tariff periods')
        ordering = ('from_timestamp',)

    def subscription_cost_sum(self, from_timestamp, to_timestamp):
        assert from_timestamp >= self.from_timestamp
        assert self.to_timestamp is None or to_timestamp <= self.to_timestamp
        return self._subscription_cost_sum(from_timestamp, to_timestamp)

    @virtual
    def _subscription_cost_sum(self, from_timestamp, to_timestamp):
        raise NotImplementedError(self.__class__)

    @property
    def currency_unit(self):
        return self.datasequence.currency_unit


class SubscriptionMixin(models.Model):
    # how awesome it would have been if these were represented as
    # their corresponding unit strings in the db.
    SUBSCRIPTION_PERIODS = Choices(
        (1, 'monthly', _('monthly')),
        (2, 'quarterly', _('quarterly')),
        (3, 'yearly', _('yearly')),
    )
    # The unit this value is currency unit from the datasequence,
    # i.e. either currency_dkk or currency_eur.  Quite obvious
    # considering the currency_unit property.
    subscription_fee = models.DecimalField(
        _('subscription fee'), max_digits=12, decimal_places=3)
    subscription_period = models.IntegerField(
        _('subscription period'), choices=SUBSCRIPTION_PERIODS)

    class Meta:
        abstract = True

    @classmethod
    def time_quantity(cls, db_value):
        """
        Translates a ``subscription_period`` ``db_value`` to the corresponding
        :class:`PhysicalQuantity` time quantity.
        """
        if db_value == cls.SUBSCRIPTION_PERIODS.monthly:
            return PhysicalQuantity(1, 'month')
        elif db_value == cls.SUBSCRIPTION_PERIODS.quarterly:
            return PhysicalQuantity(1, 'quarteryear')
        else:
            assert db_value == cls.SUBSCRIPTION_PERIODS.yearly
            return PhysicalQuantity(1, 'year')

    def _subscription_cost_sum(self, from_timestamp, to_timestamp):
        # NOTE: This appraoch does not work if we really care about
        # calendar months, quarters and years (none of which
        # correspond to a fixed number of seconds).  So the result may
        # be off by up to 4%, but that should be insignificant
        # compared to the actual utility costs that goes with the
        # subscription cost.
        subscription_fee = PhysicalQuantity(
            self.subscription_fee, self.currency_unit)
        subscription_time = self.time_quantity(self.subscription_period)
        duration_time = PhysicalQuantity(
            (to_timestamp - from_timestamp).total_seconds(), 'second')
        return subscription_fee * duration_time / subscription_time


class FixedPricePeriod(
        piecewiseconstant.FixedPiecewiseConstantPeriodValueSequenceMixin,
        SubscriptionMixin, Period):
    """
    A tariff period defining a fixed price and subscription costs.

    :ivar datasequence:  The aggregating tariff.
    :ivar subscription_fee: The subscription fee.
    :ivar subscription_period: The rate at which the subscription fee should be
        payed.  Must be one of
        :py:attr:`~.SubscriptionMixin.SUBSCRIPTION_PERIODS`.
    :ivar value:  The value of the fixed price.
    :ivar unit: The unit of the fixed price value.  Must be in the ones
        returned by :py:meth:`.get_unit_choices`.
    """
    value = models.DecimalField(_('value'), max_digits=12, decimal_places=3)
    unit = BuckinghamField(_('unit'), choices=units.TARIFF_CHOICES)
    resolution = condense.HOURS

    class Meta:
        verbose_name = _('fixed price period')
        verbose_name_plural = _('fixed price periods')

    def __unicode__(self):
        return '%s - %s: Fixed price period' % (
            self.from_timestamp, self.to_timestamp)

    def clean(self):
        """
        :raise ValidationError: If ``self.unit`` and ``self.datasequence.unit``
            are not compatible.
        """
        super(FixedPricePeriod, self).clean()
        if not PhysicalQuantity.compatible_units(
                self.unit, self.datasequence.unit):
            raise ValidationError(_('Incompatible unit.'))

    @cached_property
    def _quantity(self):
        return PhysicalQuantity(self.value, self.unit)

    def get_unit_choices(self):
        """
        :return: A list of valid unit choices for this period.
        """
        return [
            (unit, label) for unit, label in units.TARIFF_CHOICES
            if PhysicalQuantity.compatible_units(unit, self.datasequence.unit)]


class SpotPricePeriod(SubscriptionMixin, Period):
    """
    A tariff period defined in terms of a
    :py:class:`~gridplatform.datasources.models.DataSource`, and subscription
    costs.

    :ivar datasequence:  The aggregating tariff.
    :ivar subscription_fee: The subscription fee.
    :ivar subscription_period: The rate at which the subscription fee should be
        payed.  Must be one of
        :py:attr:`~.SubscriptionMixin.SUBSCRIPTION_PERIODS`.
    :ivar spotprice: The
        :py:class:`~gridplatform.datasources.models.DataSource` defining the
        spot price.
    :ivar coefficient: A unitless coefficient that each spot price value is
        multiplied by.
    :ivar unit_for_constant_and_ceiling: The unit for ``self.constant`` and
        ``self.ceiling``.

    :ivar constant: A constant added to the spot price value after it has been
        multiplied with ``self.coefficient``.

    :ivar ceiling: A ceiling for the resulting tariff value after
        ``self.coefficient`` and ``self.constant`` has been applied.
    """

    spotprice = models.ForeignKey(
        DataSource, verbose_name=_('spot price'))
    coefficient = models.DecimalField(
        _('coefficient'), max_digits=12, decimal_places=3)
    unit_for_constant_and_ceiling = BuckinghamField(
        _('unit for constant and ceiling'),
        choices=units.TARIFF_CHOICES)
    constant = models.DecimalField(
        _('constant'), max_digits=12, decimal_places=3)
    ceiling = models.DecimalField(
        _('ceiling'), max_digits=12, decimal_places=3, null=True, blank=True)

    def __unicode__(self):
        return '%s - %s: Spot price period' % (
            self.from_timestamp, self.to_timestamp)

    def clean(self):
        """
        :raise ValidationError: If ``self.unit_for_constant_and_ceiling`` is
            not compatible with the aggregating tariff.
        :raise ValidationError: If the spot price unit and the unit of the
            aggregating tariff are not compatible.
        """
        super(SpotPricePeriod, self).clean()
        if not PhysicalQuantity.compatible_units(
                self.unit_for_constant_and_ceiling, self.datasequence.unit):
            raise ValidationError(
                _('Incompatible unit for constant and ceiling.'))
        if not PhysicalQuantity.compatible_units(
                self.spotprice.unit, self.datasequence.unit):
            raise ValidationError(
                _('Incompatible spot price unit.'))

    def _get_unit(self):
        return self.spotprice.unit

    def _value_sequence(self, from_timestamp, to_timestamp):
        unit = self.spotprice.unit
        constant = PhysicalQuantity(
            self.constant, self.unit_for_constant_and_ceiling)
        coefficient = self.coefficient

        if self.ceiling is not None:
            def value(spot_value):
                ceiling = PhysicalQuantity(
                    self.ceiling, self.unit_for_constant_and_ceiling)
                return min(
                    PhysicalQuantity(
                        spot_value, unit) * coefficient + constant,
                    ceiling)
        else:
            def value(spot_value):
                return PhysicalQuantity(
                    spot_value, unit) * coefficient + constant

        # NOTE: this assumes that the "spotprice" datasource delivers hourly
        # data.
        spot_data = self.spotprice.rawdata_set.filter(
            timestamp__gte=from_timestamp,
            timestamp__lt=to_timestamp
        ).order_by('timestamp').values_list('timestamp', 'value')

        for timestamp, spot_value in spot_data:
            # BUG: timezone retreived from db as utc.  RelativeTimeDelta is
            # equivalent with datetime.timedelta in that case, and the DST
            # transitions may not be handled correctly.
            yield Sample(
                timestamp,
                timestamp + RelativeTimeDelta(hours=1), value(spot_value),
                False, False)
