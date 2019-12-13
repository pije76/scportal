# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import Graph
from legacy.measurementpoints.models import Link
from legacy.measurementpoints.models import MeanTemperatureChange
from legacy.datasequence_adapters.models import ConsumptionAccumulationAdapter
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import utilitytypes

from .consumptionmeasurementpoint import ConsumptionMeasurementPoint
from .consumptionmeasurementpoint import cached_lookup_property


class DistrictHeatingMeasurementPoint(ConsumptionMeasurementPoint):
    """
    In district heating, heat energy is transported in a distribution medium,
    usually water (but oil and steam can also be used).  A
    C{DistrictHeatingMeasurementPoint} is a heat consumption measurement point
    specialized for district heating, using water as heat distribution medium.

    Since the temperature differense between the distribution medium and what
    needs to be heated is significantly lower for water than the other kinds
    distribution media, costs of circulating water between the utility provider
    and the consumer are sufficiently high to make utility providers
    interrested in minimizing the amount of water circulated pr distributed
    quantity of heat energy.  This can reliably be translated to maximizing the
    mean cool-down temperature.

    So when inspecting a district heating measurement point one will be
    presented with a heat consumption graph, water circulation graph and
    finally a mean cool-down temperature graph.

    In general, given two of the graphs, the third graph can be deducted.  In
    this implementation, the mean cool-down temperature graph is deduced from
    the heat consumption graph and water circulation graph.

    @ivar consumption_input: Inherited from L{ConsumptionMeasurementPoint}.

    @ivar volume_input: The L{ConsumptionAccumulationAdapter} that measure the
    heat distribution medium (i.e. a water consumption measurement point,
    district heating featuring steam as heat distribution medium is not
    supported).
    """

    class Meta:
        verbose_name = _('district heating measurement point')
        verbose_name_plural = _('district heating measurement points')
        proxy = True
        app_label = 'customers'

    def __init__(self, *args, **kwargs):
        super(DistrictHeatingMeasurementPoint, self).__init__(*args, **kwargs)
        if self.utility_type is None:
            self.utility_type = utilitytypes.METER_CHOICES.district_heating

    def save(self, *args, **kwargs):
        assert self.volume_input
        assert PhysicalQuantity.compatible_units(
            self.volume_input.unit, 'meter^3')
        super(DistrictHeatingMeasurementPoint, self).save(*args, **kwargs)

        volume_graph, created = Graph.objects.get_or_create(
            collection=self, role=DataRoleField.VOLUME)
        if created:
            volume = Link(
                graph=volume_graph,
                role=DataRoleField.VOLUME,
                utility_type=self.utility_type)
        else:
            volume = volume_graph.dataseries_set.get().subclass_instance
        volume.target = self.volume_input
        volume.clean()
        volume.save()

        cooldown_graph, cooldown_created = self.graph_set.get_or_create(
            role=DataRoleField.MEAN_COOLDOWN_TEMPERATURE)
        if cooldown_created:
            cooldown = MeanTemperatureChange(
                graph=cooldown_graph,
                role=DataRoleField.MEAN_COOLDOWN_TEMPERATURE,
                utility_type=self.utility_type,
                unit='millikelvin')
        else:
            cooldown = cooldown_graph.dataseries_set.get().subclass_instance
        cooldown.energy = self.consumption
        cooldown.volume = volume
        cooldown.clean()
        cooldown.save()

    @cached_lookup_property
    def volume_input(self):
        return ConsumptionAccumulationAdapter.objects.filter(
            link_derivative_set__graph__collection=self.id,
            link_derivative_set__graph__role=DataRoleField.VOLUME).\
            distinct().get().subclass_instance
