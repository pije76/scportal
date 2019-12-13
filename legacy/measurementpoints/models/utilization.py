# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.forms import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property

from gridplatform.utils.unitconversion import PhysicalQuantity

from .dataseries import DataSeries
from .mixins import ENPIMixin
from .integral import PiecewiseConstantIntegral
from ..fields import DataRoleField


class Utilization(ENPIMixin, DataSeries):
    """
    A C{Utilization} is a L{DataSeries} that describe how well a C{consumption}
    is utilized according to current C{needs}.

    Formally, this is done by M{u(t) = S{integral} c'(t) / (n(t) * t) dt},
    where M{u} is the resulting utilization function, M{c'} is the first
    derivative of C{consumption}, M{n} is the C{needs} function and M{t} is the
    time.  In the event M{n(t)=0} we say that M{c'(t) / n(t) = 0} also.

    @ivar consumption: A continuous accumulation DataSeries defining the
    consumption.

    @ivar needs: A piece wise constant rate DataSeries defining needs as a
    function of time.
    """
    consumption = models.ForeignKey(DataSeries, on_delete=models.CASCADE,
                                    related_name='utilization_consumption'
                                    '_derivative_set')
    needs = models.ForeignKey(DataSeries, on_delete=models.PROTECT,
                              related_name='utilization_needs_derivative_set')

    class Meta(DataSeries.Meta):
        verbose_name = _('normalization')
        verbose_name_plural = _('normalizations')
        app_label = 'measurementpoints'

    def clean(self):
        """
        C{Utilization} specialization of C{Model.clean()}
        """
        super(Utilization, self).clean()
        if not (
                PhysicalQuantity(1, self.consumption.unit) / (
                    PhysicalQuantity(1, self.needs.unit) *
                    PhysicalQuantity(1, 'hour'))).\
                compatible_unit(self.unit):
            raise ValidationError(
                _('Consumption unit {consumption_unit} and needs unit '
                  '{needs_unit} are not compatible with target unit '
                  '{target_unit}').
                format(
                    consumption_unit=self.consumption.unit,
                    needs_unit=self.needs.unit,
                    target_unit=self.unit))

    def save(self, *args, **kwargs):
        """
        C{Utilization} specialization of C{Model.save()}
        """
        self.clean()
        super(Utilization, self).save(*args, **kwargs)

    def depends_on(self):
        """
        C{Utilization} implementation of L{DataSeries.depends_on()}.
        """
        return [
            self.consumption.subclass_instance,
            self.energy_driver] + \
            self.consumption.subclass_instance.depends_on() + \
            self.energy_driver.depends_on()

    def __energy_driver(self, sample):
        return (
            sample.physical_quantity *
            PhysicalQuantity(
                (sample.to_timestamp - sample.from_timestamp).total_seconds(),
                'second'))

    @cached_property
    def energy_driver(self):
        energy_driver = PiecewiseConstantIntegral(
            role=DataRoleField.ENERGY_DRIVER,
            data=self.needs.subclass_instance)
        energy_driver.full_clean(exclude=['role'])
        return energy_driver

    def _condense_energy_drivers(
            self, from_timestamp, sample_resolution, to_timestamp):
        """
        Implementation of L{ENPIMixin._condense_energy_drivers()}.
        """
        return self.energy_driver.get_condensed_samples(
            from_timestamp, sample_resolution, to_timestamp)

    def _condense_energy_consumption(self, from_timestamp, sample_resolution,
                                     to_timestamp):
        for sample in self.consumption.subclass_instance.get_condensed_samples(
                from_timestamp, sample_resolution, to_timestamp):
            assert from_timestamp <= sample.from_timestamp
            assert sample.to_timestamp <= to_timestamp
            yield sample

    def _calculate_energy_development(self, from_timestamp, to_timestamp):
        return self.consumption.subclass_instance.calculate_development(
            from_timestamp, to_timestamp)

    def _calculate_energy_driver_development(
            self, from_timestamp, to_timestamp):
        return self.energy_driver.calculate_development(
            from_timestamp, to_timestamp)
