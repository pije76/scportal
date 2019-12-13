# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.models import Graph
from legacy.measurementpoints.models import Link
from legacy.datasequence_adapters.models import ProductionAccumulationAdapter

from .measurementpoint import MeasurementPoint


class ProductionMeasurementPoint(MeasurementPoint):
    """
    A C{ProductionMeasurementPoint} is a L{MeasurementPoint} that measures
    units produced.

    @ivar production: A L{DataSeries} of production measurements.

    @ivar production_graph: A graph holding the C{production} L{DataSeries}.
    """
    class Meta:
        proxy = True
        verbose_name = _('Production measurement point')
        verbose_name_plural = _('Production measurement points')
        app_label = 'customers'

    def __init__(self, *args, **kwargs):
        super(ProductionMeasurementPoint, self).__init__(*args, **kwargs)
        if self.utility_type is None:
            self.utility_type = utilitytypes.OPTIONAL_METER_CHOICES.unknown

        if self.role is None:
            self.role = self.MEASUREMENT_POINT_PRODUCTION

    def save(self, *args, **kwargs):
        super(ProductionMeasurementPoint, self).save(*args, **kwargs)
        assert self.input_configuration

        graph, created = Graph.objects.get_or_create(
            collection=self,
            role=DataRoleField.PRODUCTION)
        if created:
            Link.objects.create(
                graph=graph,
                role=DataRoleField.PRODUCTION,
                unit=self._input_configuration.unit,
                utility_type=self.utility_type,
                target=self._input_configuration)

    def _get_input_configuration(self):
        self._input_configuration = getattr(self, '_input_configuration', None)
        if self.id and not self._input_configuration:
            self._input_configuration = \
                ProductionAccumulationAdapter.objects.get(
                    link_derivative_set__graph__collection=self.id)
        return self._input_configuration

    def _set_input_configuration(self, input_configuration):
        self._input_configuration = input_configuration

    input_configuration = property(
        _get_input_configuration, _set_input_configuration)

    def get_delete_prevention_reason(self, return_dependents_only=False):
        """
        Returns a HTML formated string with a description of why
        this temperature measurement point cannot be deleted.
        Returning None, if no reason exist, meaning the MP can
        be deleted without breaking anything.

        @param return_dependents_only: If true, only return a string of
        the units that depends on this resource.
        """
        return None

    def is_deletable(self):
        """
        Returns true or false whether
        this temperature measurement point can be deleted or not.
        """
        return True

    @property
    def has_consumption(self):
        return False

    @property
    def has_gauge(self):
        return False

    @property
    def has_rate(self):
        return False

    @property
    def has_production(self):
        return True

    @staticmethod
    def get_input_configuration_choices():
        """
        Get L{ProductionAccumulationAdapter} choices.
        """
        return ProductionAccumulationAdapter.objects.filter(
            role=DataRoleField.PRODUCTION,
            customer=trackuser.get_customer())
