# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from gridplatform.consumptions.models import ConsumptionGroup
from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.fields import EncryptedTextField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.productions.models import ProductionGroup
from gridplatform.trackuser.managers import StoredSubclassCustomerBoundManager
from gridplatform.utils.decorators import virtual
from gridplatform.utils.models import StoreSubclass
from gridplatform.utils.preferredunits import PhysicalUnitConverter
from gridplatform.utils.preferredunits import ProductionAENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionBENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionCENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionDENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionEENPIUnitConverter
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.units import CONSUMPTION_PER_TIME_CHOICES
from gridplatform.utils.fields import BuckinghamField


class EnergyPerformance(
        EncryptionCustomerFieldMixin, EncryptedModel, StoreSubclass):
    """
    Base model for energy performances.

    :ivar name: The name of the energy performance.
    :ivar description: The description of the energy performance.
    """
    name = EncryptedCharField(_('name'), max_length=255)
    description = EncryptedTextField(_('description'))

    objects = StoredSubclassCustomerBoundManager()

    class Meta:
        verbose_name = _('energy performance')
        verbose_name_plural = _('energy performances')

    def __unicode__(self):
        return self.name_plain

    @virtual
    def compute_performance(self, from_timestamp, to_timestamp):
        """
        Pure virtual method for computing the energy performance across the
        given period.

        :param from_timestamp: The start of the given period.
        :param to_time: The end of the given period.
        :rtype:  A `PhysicalQuantity` or `None`
        """
        raise NotImplementedError(self.__class__)

    @cached_property
    def unit_converter(self):
        return self._get_unit_converter()

    @virtual
    def _get_unit_converter(self):
        raise NotImplementedError(self.__class__)


class ProductionEnergyPerformance(EnergyPerformance):
    """
    Production based energy performance defined from given energy consumptions
    and given productions.

    :ivar production_unit: The production unit must be shared among all
        participating productions.  Choices depend on associated customer and
        should be defined on runtime in terms of
        :py:meth:`~gridplatform.customers.models.Customer
        .get_production_unit_choices`.
    :ivar consumptiongroups: The
        :py:class:`~gridplatform.consumptions.models.ConsumptionGroup` that
        define the given energy consumptions.
    :ivar productiongroups: The
        :py:class:`~gridplatform.productions.models.ProductionGroup` that
        define the given productions.
    """

    # NOTE: Use get_production_unit_choices() from get_customer() or
    # instance.customer as choices for the `production_unit` field.
    production_unit = BuckinghamField(_('production unit'))
    consumptiongroups = models.ManyToManyField(
        ConsumptionGroup, verbose_name=_('consumption groups'), blank=True)
    productiongroups = models.ManyToManyField(
        ProductionGroup,
        verbose_name=_('production groups'),
        blank=True)

    class Meta:
        verbose_name = _('production energy performance')
        verbose_name_plural = _('production energy performances')

    def clean_fields(self, exclude=None):
        """
        :raises ValidationError: if ``self.production_unit`` is not among the
            units returned by ``self.customer.get_production_unit_choices()``
        """
        if exclude is None or 'production_unit' not in exclude:
            if self.production_unit not in \
                    self.customer.get_production_unit_choices():
                raise ValidationError(
                    {'production_unit': [_('Illegal choice')]})

    def compute_performance(self, from_timestamp, to_timestamp):
        """
        Implementation of :py:meth:`.EnergyPerformance.compute_performance`.

        :return: the total energy consumption across the given period divided
            by the total production across the given period.  Division-by-zero
            is handled by returning ``None``.
        """
        total_energy = sum(
            (
                energy for energy in (
                    consumptiongroup.energy_sum(
                        from_timestamp, to_timestamp)
                    for consumptiongroup in self.consumptiongroups.all())
                if energy is not None),
            PhysicalQuantity(0, 'watt*hour'))

        total_production = sum(
            (
                production for production in (
                    productiongroup.development_sum(
                        from_timestamp, to_timestamp)
                    for productiongroup in self.productiongroups.all())
                if production is not None),
            PhysicalQuantity(0, self.production_unit))
        if total_production:
            return total_energy / total_production
        else:
            return None

    def _get_unit_converter(self):
        energy_unit = 'kilowatt*hour'
        if self.production_unit == 'production_a':
            return ProductionAENPIUnitConverter(energy_unit, self.customer)
        elif self.production_unit == 'production_b':
            return ProductionBENPIUnitConverter(energy_unit, self.customer)
        elif self.production_unit == 'production_c':
            return ProductionCENPIUnitConverter(energy_unit, self.customer)
        elif self.production_unit == 'production_d':
            return ProductionDENPIUnitConverter(energy_unit, self.customer)
        elif self.production_unit == 'production_e':
            return ProductionEENPIUnitConverter(energy_unit, self.customer)

    @property
    def unit(self):
        return self.production_unit


class TimeEnergyPerformance(EnergyPerformance):
    """
    Time adjustment based energy performance (mean power) for given energy
    consumptions.

    :ivar consumptiongroups: The
        :py:class:`~gridplatform.consumptions.models.ConsumptionGroup` that
        define the given energy consumptions.
    :ivar unit: The mean-power unit.  Must be one of
        :py:data:`~gridplatform.utils.units.CONSUMPTION_PER_TIME_CHOICES`.
    """
    consumptiongroups = models.ManyToManyField(
        ConsumptionGroup, verbose_name=_('consumption groups'), blank=True)
    unit = BuckinghamField(_('unit'), choices=CONSUMPTION_PER_TIME_CHOICES)

    class Meta:
        verbose_name = _('consumption performance')
        verbose_name_plural = _('consumption performances')

    def compute_performance(self, from_timestamp, to_timestamp):
        """
        Implementation of :py:meth:`.EnergyPerformance.compute_performance`.

        :return: the mean-power calculated from the total energy consumption
            across the given period.
        """
        assert from_timestamp < to_timestamp
        total_energy = sum(
            (
                energy for energy in (
                    consumptiongroup.energy_sum(
                        from_timestamp, to_timestamp)
                    for consumptiongroup in self.consumptiongroups.all())
                if energy is not None),
            PhysicalQuantity(0, 'watt*hour'))
        return total_energy / \
            PhysicalQuantity(
                (to_timestamp - from_timestamp).total_seconds(), 'second')

    @virtual
    def _get_unit_converter(self):
        return PhysicalUnitConverter(self.unit)
