# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from model_utils import FieldTracker
from model_utils import Choices

import gridplatform.datasequences.models
from gridplatform.cost_compensations.models import CostCompensation
from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from gridplatform.datasequences.utils import add_ranged_sample_sequences
from gridplatform.datasequences.utils import multiply_ranged_sample_sequences
from gridplatform.datasequences.utils import subtract_ranged_sample_sequences
from gridplatform.datasequences.utils import aggregate_sum_ranged_sample_sequence  # noqa
from gridplatform.datasequences.models import EnergyPerVolumeDataSequence
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.fields import EncryptedTextField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.tariffs.models import Tariff
from gridplatform.trackuser.managers import CustomerBoundManager
from gridplatform.utils import condense
from gridplatform.utils import sum_or_none
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.utilitytypes import ENERGY_UTILITY_TYPE_CHOICES
from gridplatform.utils.utilitytypes import ENERGY_UTILITY_TYPE_TO_BASE_UNIT_MAP  # noqa
from gridplatform.utils.api import next_valid_date_for_datasequence
from gridplatform.utils.api import previous_valid_date_for_datasequence
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.models import DateRangeModelMixin
from gridplatform.utils.managers import DateRangeManagerMixin


class Consumption(gridplatform.datasequences.models.AccumulationBase):
    """
    A data sequence for energy consumption via various utilities.

    :ivar unit: The utility unit of this data sequence.  This field is
        never supposed to be changed.

    :ivar volumetoenergyconversion: If the utility itself is not
        measured directly as energy, this
        :py:class:`EnergyPerVolumeDataSequence` foreign key may be set
        to enable the conversion.
    """

    UNIT_CHOICES = Choices(
        ('joule', 'energy', _('energy')),
        ('meter^3', 'volume', _('volume')),
        ('second', 'time', _('time'))
    )

    # DO NOT UPDATE
    unit = BuckinghamField(_('unit'), choices=UNIT_CHOICES)

    tracker = FieldTracker(fields=['unit'])

    volumetoenergyconversion = models.ForeignKey(
        EnergyPerVolumeDataSequence,
        verbose_name=_('volume to energy conversion'),
        null=True, blank=True)

    class Meta:
        verbose_name = _('consumption data sequence')
        verbose_name_plural = _('consumption data sequences')

    def clean(self):
        """
        :raises ValidationError: if ``self.volumetoenergyconversion`` is
            set, but the utility is energy.
        """
        previous_unit = self.tracker.previous('unit')
        if previous_unit is not None:
            if not PhysicalQuantity.compatible_units(previous_unit, self.unit):
                raise ValidationError(
                    {
                        'unit': [ugettext('Must not be changed')]})

        if not PhysicalQuantity.compatible_units(self.unit, 'meter^3') and \
                self.volumetoenergyconversion is not None:
            raise ValidationError(
                {
                    'volumetoenergyconversion': [
                        ugettext(
                            'Should only be set for volumeric consumptions.')
                    ]})

    def _hourly_conversion_sequence(self, from_timestamp, to_timestamp):
        assert not PhysicalQuantity.compatible_units(self.unit, 'joule')
        if self.volumetoenergyconversion is not None:
            return self.volumetoenergyconversion.period_set.value_sequence(
                from_timestamp, to_timestamp)
        else:
            return []

    def energy_sequence(self, from_timestamp, to_timestamp, resolution):
        """
        :return: a sequence of accumulating ranged samples of energy for
            given period in given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        if PhysicalQuantity.compatible_units(self.unit, 'joule') or \
                PhysicalQuantity.compatible_units(self.unit, 'second'):
            return self.utility_sequence(
                from_timestamp, to_timestamp, resolution)

        # NOTE: Conversion happens in hourly resolution.
        utility_samples = self.utility_sequence(
            from_timestamp, to_timestamp, condense.HOURS)
        conversion_samples = self._hourly_conversion_sequence(
            from_timestamp, to_timestamp)
        hourly_energy_samples = multiply_ranged_sample_sequences(
            utility_samples, conversion_samples)

        return aggregate_sum_ranged_sample_sequence(
            hourly_energy_samples, resolution, self.customer.timezone)

    def energy_sum(self, from_timestamp, to_timestamp):
        """
        :return: the total energy in the given period.  If
            undefined, ``None`` is returned.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        """
        if PhysicalQuantity.compatible_units(self.unit, 'joule') or \
                PhysicalQuantity.compatible_units(self.unit, 'second'):
            return self.utility_sum(from_timestamp, to_timestamp)
        return sum_or_none(
            sample.physical_quantity for sample in
            self.energy_sequence(
                from_timestamp, to_timestamp, condense.HOURS))

    def utility_sequence(self, from_timestamp, to_timestamp, resolution):
        """
        :return: a sequence of accumulating ranged samples of utility for
            given period in given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        return self.development_sequence(
            from_timestamp, to_timestamp, resolution)

    def utility_sum(self, from_timestamp, to_timestamp):
        """
        :return: the total utility in the given period.  If
            undefined, ``None`` is returned.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        """
        return self.development_sum(from_timestamp, to_timestamp)

    @property
    def utility_unit(self):
        return self.unit


class ConsumptionUnionManager(DateRangeManagerMixin, CustomerBoundManager):
    pass


class ConsumptionUnionBase(
        DateRangeModelMixin, EncryptionCustomerFieldMixin, EncryptedModel):
    """
    Base class for ``MainConsumption`` and ``ConsumptionGroup``.  To
    support historical changes fields defining a date range are
    included.

    :ivar name: The name of this instance.

    :ivar description: A description of this instance.

    :ivar from_date: The first date in the date range.

    :ivar to_date: The final date in the date range.

    :ivar consumptions: The ``Consumption`` objects that belong to this
        instance.
    """

    name = EncryptedCharField(_('name'), max_length=100)
    description = EncryptedTextField(_('description'), blank=True)

    # WARNING: removing anything from this relation is almost always an error.
    consumptions = models.ManyToManyField(
        Consumption, verbose_name=_('consumptions'), blank=True)

    cost_compensation = models.ForeignKey(
        CostCompensation, verbose_name=_('cost compensation'),
        blank=True, null=True)

    objects = ConsumptionUnionManager()
    tracker = FieldTracker(fields=['cost_compensation_id'])

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name_plain

    def clean(self):
        super(ConsumptionUnionBase, self).clean()

        previous_costcompensation_id = self.tracker.previous(
            'cost_compensation_id')

        if previous_costcompensation_id is not None:
            if self.cost_compensation_id is None:
                raise ValidationError(
                    _('Cost compensation cannot be cleared once selected'))
            if previous_costcompensation_id != self.cost_compensation_id:
                raise ValidationError(
                    _('Cost compensation cannot be changed once selected'))

    def energy_sum(self, from_timestamp, to_timestamp):
        """
        :return: the total energy in the given period.  If
            undefined, ``None`` is returned.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        """
        intersection = self.timestamp_range_intersection(
            from_timestamp, to_timestamp, self.customer.timezone)

        if intersection is None:
            return None

        return sum_or_none(
            quantity for quantity in (
                consumption.energy_sum(
                    intersection.from_timestamp, intersection.to_timestamp)
                for consumption in self.consumptions.all())
            if quantity is not None)

    def energy_sequence(self, from_timestamp, to_timestamp, resolution):
        """
        :return: a sequence of accumulating ranged samples of energy for
            given period in given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        intersection = self.timestamp_range_intersection(
            from_timestamp, to_timestamp, self.customer.timezone)

        if intersection is None:
            return []

        return add_ranged_sample_sequences(
            [
                consumption.energy_sequence(
                    intersection.from_timestamp, intersection.to_timestamp,
                    resolution)
                for consumption in self.consumptions.all()
            ],
            intersection.from_timestamp, intersection.to_timestamp, resolution)

    def utility_sum(self, from_timestamp, to_timestamp):
        """
        :return: the total utility in the given period.  If
            undefined, ``None`` is returned.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        """
        intersection = self.timestamp_range_intersection(
            from_timestamp, to_timestamp, self.customer.timezone)

        if intersection is None:
            return None

        return sum_or_none(
            quantity for quantity in (
                consumption.utility_sum(
                    intersection.from_timestamp, intersection.to_timestamp)
                for consumption in self.consumptions.all())
            if quantity is not None)

    def utility_sequence(self, from_timestamp, to_timestamp, resolution):
        """
        :return: a sequence of accumulating ranged samples of utility for
            given period in given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        intersection = self.timestamp_range_intersection(
            from_timestamp, to_timestamp, self.customer.timezone)

        if intersection is None:
            return []

        return add_ranged_sample_sequences(
            [
                consumption.utility_sequence(
                    intersection.from_timestamp, intersection.to_timestamp,
                    resolution)
                for consumption in self.consumptions.all()
            ],
            intersection.from_timestamp, intersection.to_timestamp, resolution)

    def next_valid_date(self, date, timezone):
        return next_valid_date_for_datasequence(
            self.consumptions.all(), date, timezone)

    def previous_valid_date(self, date, timezone):
        return previous_valid_date_for_datasequence(
            self.consumptions.all(), date, timezone)

    def net_cost_sequence(self, from_timestamp, to_timestamp, resolution):
        """
        The net costs are calculated by applying the tariff directly on
        the consumed utility.

        :return: a sequence of accumulating ranged samples of net
            costs for given period in given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        if not self.tariff:
            return []

        tariff_sequence = self.tariff.period_set.value_sequence(
            from_timestamp, to_timestamp)

        utility_sequence = self.utility_sequence(
            from_timestamp, to_timestamp, condense.HOURS)

        hourly_net_cost_sequence = multiply_ranged_sample_sequences(
            utility_sequence, tariff_sequence)

        return aggregate_sum_ranged_sample_sequence(
            hourly_net_cost_sequence, resolution, self.customer.timezone)

    def net_cost_sum(self, from_timestamp, to_timestamp):
        """
        The net costs are calculated by applying the tariff directly on
        the consumed utility.

        :return: the total energy in the given period.  If
            undefined, ``None`` is returned.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        """
        net_cost_sequence = self.net_cost_sequence(
            from_timestamp, to_timestamp, condense.HOURS)

        return sum_or_none(
            sample.physical_quantity for sample in net_cost_sequence)

    def variable_cost_sum(self, from_timestamp, to_timestamp):
        """
        Variable costs are net costs minus cost compensation amounts.

        :return: the variable costs in the given period.  If
            undefined, ``None`` is returned.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        """
        net_cost = self.net_cost_sum(from_timestamp, to_timestamp)
        costcompensation_amount = self.costcompensation_amount_sum(
            from_timestamp, to_timestamp)

        if costcompensation_amount is None:
            return net_cost
        elif net_cost is not None:
            return net_cost - costcompensation_amount
        else:
            return None

    def variable_cost_sequence(self, from_timestamp, to_timestamp, resolution):
        """
        Variable costs are net costs minus cost compensation amounts.

        :return: a sequence of accumulating ranged samples of variable
            cost for given period in given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        net_cost_samples = self.net_cost_sequence(
            from_timestamp, to_timestamp, condense.HOURS)
        costcompensation_amount_samples = \
            self.costcompensation_amount_sequence(
                from_timestamp, to_timestamp, condense.HOURS)

        hourly_variable_cost_sequence = subtract_ranged_sample_sequences(
            net_cost_samples, costcompensation_amount_samples)

        return aggregate_sum_ranged_sample_sequence(
            hourly_variable_cost_sequence, resolution, self.customer.timezone)

    def costcompensation_amount_sum(self, from_timestamp, to_timestamp):
        """
        The cost compensation amount is calculated by applying the cost
        compensation directly to the consumed energy.

        :return: the total cost compensation amount in the given period.
            If undefined, ``None`` is returned.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        """
        return sum_or_none(
            sample.physical_quantity for sample in
            self.costcompensation_amount_sequence(
                from_timestamp, to_timestamp, condense.HOURS))

    def costcompensation_amount_sequence(
            self, from_timestamp, to_timestamp, resolution):
        raise NotImplementedError(self.__class__)

    def fiveminute_co2conversion_sequence(self, from_timestamp, to_timestamp):
        raise NotImplementedError(self.__class__)

    def co2_emissions_sequence(
            self, from_timestamp, to_timestamp, resolution):
        """
        The CO₂ emissions are calculated by applying the CO₂ conversion
        directly on the consumed utility.

        :return: a sequence of accumulating ranged samples of CO₂
            emissions for the given period in given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """

        fiveminute_conversion_samples = self.fiveminute_co2conversion_sequence(
            from_timestamp, to_timestamp)
        fiveminute_utility_samples = self.utility_sequence(
            from_timestamp, to_timestamp, condense.FIVE_MINUTES)

        fiveminute_emissions_samples = multiply_ranged_sample_sequences(
            fiveminute_conversion_samples, fiveminute_utility_samples)

        # 10 % performance improvement by noop optimization
        if resolution == condense.FIVE_MINUTES:
            return fiveminute_emissions_samples
        else:
            return aggregate_sum_ranged_sample_sequence(
                fiveminute_emissions_samples,
                resolution, self.customer.timezone)

    def co2_emissions_sum(self, from_timestamp, to_timestamp):
        """
        The CO₂ emissions are calculated by applying the CO₂ conversion
        directly on the consumed utility.

        :return: the total CO₂ emissions in the given period.  If
            undefined, ``None`` is returned.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        """
        return sum_or_none(
            sample.physical_quantity for sample in
            self.co2_emissions_sequence(
                from_timestamp, to_timestamp, condense.FIVE_MINUTES))


class MainConsumption(ConsumptionUnionBase):
    """
    Main consumptions are individually billed sources of utilities
    going into a company.

    :ivar utility_type: The type of utility of this
        ``MainConsumption``.  This is supposed never to change.

    :ivar tariff: The tariff according to which this
        ``MainConsumption`` is billed.  Changing this will almost
        certainly invalidate existing cost calculations.
    """

    # NOTE: do not update
    #
    # NOTE: could have been implemented via five simple subclasses.
    utility_type = models.IntegerField(
        _('utility type'),
        choices=ENERGY_UTILITY_TYPE_CHOICES)

    tariff = models.ForeignKey(
        Tariff, verbose_name=_('tariff'), blank=True, null=True)

    tracker = FieldTracker(
        fields=['utility_type', 'tariff_id', 'cost_compensation_id'])

    class Meta:
        verbose_name = _('main consumption')
        verbose_name_plural = _('main consumptions')

    def save(self, *args, **kwargs):
        previous_utility_type = self.tracker.previous('utility_type')
        if previous_utility_type is not None:
            assert previous_utility_type == self.utility_type

        if self.tariff:
            assert (PhysicalQuantity(1, self.utility_unit) *
                    PhysicalQuantity(1, self.tariff.unit)).compatible_unit(
                        self.tariff.currency_unit), \
                '%s not valid tariff unit for utility unit %s' % (
                    self.tariff.unit, self.utility_unit)

        super(MainConsumption, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name_plain

    def clean(self):
        super(MainConsumption, self).clean()

        previous_tariff_id = self.tracker.previous('tariff_id')
        if previous_tariff_id is not None:
            if self.tariff_id is None:
                raise ValidationError(
                    _('Tariff cannot be cleared once selected.'))
            if previous_tariff_id != self.tariff_id:
                raise ValidationError(
                    _('Tariff cannot be changed once selected.'))

        if self.tariff:
            utility = PhysicalQuantity(1, self.utility_unit)
            tariff = PhysicalQuantity(1, self.tariff.unit)
            if not (utility * tariff).compatible_unit(
                    self.tariff.currency_unit):
                raise ValidationError(
                    _('Tariff unit incompatible with utility unit.'))

    @property
    def utility_unit(self):
        return ENERGY_UTILITY_TYPE_TO_BASE_UNIT_MAP[self.utility_type]

    def costcompensation_amount_sequence(
            self, from_timestamp, to_timestamp, resolution):
        """
        The cost compensation amount is calculated by applying the cost
        compensation directly to the consumed energy.

        :return: a sequence of accumulating ranged samples of net
            costs for given period in given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.

        NOTE: `self.cost_compensation` only applies to consumptions without
        other cost compensations.  You cannot be compensated twice.
        """
        # Cost compensation amounts from consumption groups with their own cost
        # compensations plus cost compensation for utilities not covered by
        # consumption groups with their own cost compensations.

        energy_sequence = self.energy_sequence(
            from_timestamp, to_timestamp, condense.HOURS)

        tainted_energy_sequence = add_ranged_sample_sequences(
            [
                consumption.development_sequence(
                    from_timestamp, to_timestamp, condense.HOURS)
                for consumption in Consumption.objects.filter(
                    consumptiongroup__cost_compensation__isnull=False,
                    consumptiongroup__mainconsumption=self)
            ],
            from_timestamp, to_timestamp, condense.HOURS)

        if self.cost_compensation:
            untainted_energy_sequence = subtract_ranged_sample_sequences(
                energy_sequence, tainted_energy_sequence)

            costcompensation_sequence = \
                self.cost_compensation.period_set.value_sequence(
                    from_timestamp, to_timestamp)

            untainted_costcompensation_amount_sequence = \
                multiply_ranged_sample_sequences(
                    untainted_energy_sequence,
                    costcompensation_sequence)
        else:
            untainted_costcompensation_amount_sequence = []

        tainted_consumptiongroups = self.consumptiongroup_set.filter(
            cost_compensation__isnull=False)

        tainted_costcompensation_amount_sequence = add_ranged_sample_sequences(
            [consumptiongroup.costcompensation_amount_sequence(
                from_timestamp, to_timestamp, resolution)
             for consumptiongroup in tainted_consumptiongroups],
            from_timestamp, to_timestamp, condense.HOURS)

        hourly_costcompensation_amount_sequence = add_ranged_sample_sequences(
            [
                untainted_costcompensation_amount_sequence,
                tainted_costcompensation_amount_sequence],
            from_timestamp, to_timestamp, condense.HOURS)

        return aggregate_sum_ranged_sample_sequence(
            hourly_costcompensation_amount_sequence,
            resolution, self.customer.timezone)

    def fixed_cost_sum(self, from_timestamp, to_timestamp):
        """
        :return: the subscription costs in the given period.

        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        if self.tariff:
            return self.tariff.period_set.subscription_cost_sum(
                from_timestamp, to_timestamp)
        return None

    def total_cost_sum(self, from_timestamp, to_timestamp):
        """
        :return: the total of variable and fixed costs within the given
            period.  If neither is defined ``None`` is returned.

        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        variable_cost = self.variable_cost_sum(from_timestamp, to_timestamp)
        fixed_cost = self.fixed_cost_sum(from_timestamp, to_timestamp)
        return sum_or_none(
            x for x in [variable_cost, fixed_cost] if x is not None)

    def fiveminute_co2conversion_sequence(self, from_timestamp, to_timestamp):
        return self.co2conversion_set.value_sequence(
            from_timestamp, to_timestamp)


class ConsumptionGroup(ConsumptionUnionBase):
    """
    Defines an energy use for a ``MainConsumption``.  Most methods and
    fields are inherited from ``ConsumptionUnionBase``.

    :ivar mainconsumption: the ``MainConsumption`` for which this
        instance defines an energy use.
    """

    # NOTE: do not update
    mainconsumption = models.ForeignKey(
        MainConsumption, verbose_name=_('main consumption'))

    tracker = FieldTracker(
        fields=['mainconsumption_id', 'cost_compensation_id'])

    class Meta:
        verbose_name = _('consumption group')
        verbose_name_plural = _('consumption groups')

    def save(self, *args, **kwargs):
        previous_mainconsumption_id = self.tracker.previous(
            'mainconsumption_id')
        if previous_mainconsumption_id is not None:
            assert previous_mainconsumption_id == self.mainconsumption.id
        super(ConsumptionGroup, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name_plain

    @property
    def utility_unit(self):
        return self.mainconsumption.utility_unit

    @property
    def tariff(self):
        return self.mainconsumption.tariff

    def costcompensation_amount_sequence(
            self, from_timestamp, to_timestamp, resolution):
        """
        The cost compensation amount is calculated by applying the cost
        compensation directly to the consumed energy.

        :return: a sequence of accumulating ranged samples of net
            costs for given period in given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        if self.cost_compensation:
            costcompensation = self.cost_compensation
        elif self.mainconsumption.cost_compensation:
            costcompensation = self.mainconsumption.cost_compensation
        else:
            return []

        costcompensation_sequence = costcompensation.period_set.value_sequence(
            from_timestamp, to_timestamp)

        energy_sequence = self.energy_sequence(
            from_timestamp, to_timestamp, condense.HOURS)

        hourly_costcompensation_amount_sequence = \
            multiply_ranged_sample_sequences(
                energy_sequence, costcompensation_sequence)

        return aggregate_sum_ranged_sample_sequence(
            hourly_costcompensation_amount_sequence,
            resolution,
            self.customer.timezone)

    def fiveminute_co2conversion_sequence(self, from_timestamp, to_timestamp):
        return self.mainconsumption.fiveminute_co2conversion_sequence(
            from_timestamp, to_timestamp)


def check_utility_units(
        sender, instance, action, reverse, model, pk_set, **kwargs):
    if action == 'pre_add':
        for consumption in model.objects.filter(id__in=pk_set):
            assert PhysicalQuantity.compatible_units(
                instance.utility_unit,
                consumption.utility_unit), \
                '%s incompatible with %s' % (
                    instance.utility_unit, consumption.utility_unit)


models.signals.m2m_changed.connect(
    check_utility_units, sender=ConsumptionGroup.consumptions.through,
    dispatch_uid='ConsumptionGroup.consumptions utility unit check')
models.signals.m2m_changed.connect(
    check_utility_units, sender=MainConsumption.consumptions.through,
    dispatch_uid='MainConsumption.consumptions utility unit check')


class Period(gridplatform.datasequences.models.AccumulationPeriodBase):
    datasequence = models.ForeignKey(
        Consumption,
        verbose_name=_('data sequence'),
        editable=False)

    class Meta:
        verbose_name = _('consumption period')
        verbose_name_plural = _('consumption periods')


class NonpulsePeriod(
        gridplatform.datasequences.models.NonpulseAccumulationPeriodMixin,
        Period):
    """
    Defines :py:meth:`.Consumption.utility_sequence` of
    ``self.datasequence`` within a period in terms of a
    :py:class:`~gridplatform.datasources.models.DataSource` with a
    compatible unit.

    :ivar datasequence: A foreign key back to the owning :py:class:`Consumption`.
    :ivar datasource: A foreign key to the nonpulse :py:class:`DataSource`.
    :ivar from_timestamp: The start of the period.
    :ivar from_timestamp: The end of the period.
    """

    class Meta:
        verbose_name = _('non-pulse consumption period')
        verbose_name_plural = _('non-pulse consumption periods')


class PulsePeriod(
        gridplatform.datasequences.models.PulseAccumulationPeriodMixin,
        Period):
    """
    Defines :py:meth:`.Consumption.utility_sequence` of
    ``self.datasequence`` within a period in terms of a
    :py:class:`~gridplatform.datasources.models.DataSource` with the
    ``"impulse"`` unit.

    :ivar datasequence: A foreign key back to the owning :py:class:`Consumption`.
    :ivar datasource: A foreign key to the pulse :py:class:`DataSource`.
    :ivar from_timestamp: The start of the period.
    :ivar from_timestamp: The end of the period.
    """

    class Meta:
        verbose_name = _('pulse consumption period')
        verbose_name_plural = _('pulse consumption periods')


class SingleValuePeriod(
        gridplatform.datasequences.models.SingleValueAccumulationPeriodMixin,
        Period):
    """
    Defines :py:meth:`.Consumption.utility_sequence` of
    ``self.datasequence`` within a period in terms of a single utility
    quantity spread evenly across the period.

    :ivar datasequence: A foreign key back to the owning :py:class:`Consumption`.
    :ivar value: The value of the utility quantity.
    :ivar unit: The unit of the utility quantity.
    :ivar from_timestamp: The start of the period.
    :ivar from_timestamp: The end of the period.
    """
    class Meta:
        verbose_name = _('single value consumption period')
        verbose_name_plural = _('single value consumption periods')


class OfflineTolerance(
        gridplatform.datasequences.models.OfflineToleranceMixin):
    datasequence = models.OneToOneField(
        Consumption,
        editable=False)
