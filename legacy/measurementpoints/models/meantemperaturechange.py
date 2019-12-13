# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from gridplatform.utils.unitconversion import PhysicalQuantity

from .dataseries import DataSeries
from .mixins import ENPIMixin


VOLUMETRIC_THERMAL_CAPACITY_WATER = PhysicalQuantity(
    860, 'kelvin*meter^3*megawatt^-1*hour^-1')


class MeanTemperatureChange(ENPIMixin, DataSeries):
    """
    Calculate the mean temperature change (cool-down or heat-up) using the
    volumetric thermal capacity, energy and volume.

    Relevant for district heating using water as heat distribution medium.

    @note: Using the volumetric thermal capacity of water, we can view the
    volume as energy pr degree kelvin, which in turn makes the volume an energy
    driver and the resulting ENPI a temperature.  This is the idea behind using
    the C{ENPIMixin}.

    @ivar energy: The energy L{DataSeries}

    @ivar volume: The volume L{DataSeries}

    @invariant: The C{energy} L{DataSeries} has an energy unit (e.g joule).

    @invariant: The C{volume} L{DataSeries} has a volume unit (e.g. m^3).
    """
    energy = models.ForeignKey(
        DataSeries, on_delete=models.CASCADE,
        related_name='mean_temperature_change_energy_derivative_set')
    volume = models.ForeignKey(
        DataSeries, on_delete=models.CASCADE,
        related_name='mean_temperature_change_volume_derivative_set')

    class Meta(DataSeries.Meta):
        verbose_name = _('mean temperature change')
        verbose_name_plural = _('mean temperature change')
        app_label = 'measurementpoints'

    def save(self, *args, **kwargs):
        self._assert_invariants()
        super(MeanTemperatureChange, self).save(*args, **kwargs)

    def _assert_invariants(self):
        assert PhysicalQuantity.compatible_units(self.energy.unit, 'joule')
        assert PhysicalQuantity.compatible_units(self.volume.unit, 'meter^3')

    def depends_on(self):
        return [self.energy.subclass_instance,
                self.volume.subclass_instance] + \
            self.energy.subclass_instance.depends_on() + \
            self.volume.subclass_instance.depends_on()

    def _condense_energy_drivers(
            self, from_timestamp, sample_resolution, to_timestamp):
        for volume in self.volume.subclass_instance.get_condensed_samples(
                from_timestamp, sample_resolution, to_timestamp):
            yield volume._replace(
                physical_quantity=volume.physical_quantity /
                VOLUMETRIC_THERMAL_CAPACITY_WATER)

    def _condense_energy_consumption(self, from_timestamp, sample_resolution,
                                     to_timestamp):
        return self.energy.subclass_instance.get_condensed_samples(
            from_timestamp, sample_resolution, to_timestamp)

    def calculate_cost(self, from_timestamp, to_timestamp, consumption=None):
        # load shifting according to measured data doesn't make sense anyway.
        raise NotImplementedError()

    def aggregated_samples(self, from_timestamp, to_timestamp):
        # aggregations of condensed mean are not defined without a resolution.
        raise NotImplementedError()

    def _calculate_energy_development(self, from_timestamp, to_timestamp):
        return self.energy.calculate_development(from_timestamp, to_timestamp)

    def _calculate_energy_driver_development(
            self, from_timestamp, to_timestamp):
        volume = self.volume.calculate_development(
            from_timestamp, to_timestamp)
        return volume._replace(
            physical_quantity=volume.physical_quantity /
            VOLUMETRIC_THERMAL_CAPACITY_WATER)
