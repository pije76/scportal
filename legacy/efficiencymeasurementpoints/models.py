# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.proxies.measurementpoint import MeasurementPoint
from gridplatform.utils.preferredunits import EfficiencyUnitConverter
from gridplatform.utils import utilitytypes
from legacy.datasequence_adapters.models import NonaccumulationAdapter
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import Graph
from legacy.measurementpoints.models import Link


class EfficiencyLink(Link):
    class Meta:
        proxy = True
        verbose_name = _('efficiency link')
        verbose_name_plural = _('efficiency links')

    def get_preferred_unit_converter(self):
        return EfficiencyUnitConverter()


class EfficiencyMeasurementPoint(MeasurementPoint):
    class Meta:
        proxy = True
        verbose_name = _('efficiency measurement point')
        verbose_name_plural = _('efficiency measurement points')

    def __init__(self, *args, **kwargs):
        super(EfficiencyMeasurementPoint, self).__init__(*args, **kwargs)
        if self.role is None:
            self.role = self.MEASUREMENT_POINT_EFFICIENCY
        if self.utility_type is None:
            self.utility_type = utilitytypes.OPTIONAL_METER_CHOICES.unknown

    def save(self, *args, **kwargs):
        super(EfficiencyMeasurementPoint, self).save(*args, **kwargs)
        assert self.input_configuration

        graph, created = Graph.objects.get_or_create(
            collection=self,
            role=DataRoleField.EFFICIENCY)
        if created:
            EfficiencyLink.objects.create(
                customer=self.customer,
                graph=graph,
                role=DataRoleField.EFFICIENCY,
                unit='millibar',
                utility_type=self.utility_type,
                target=self._input_configuration)

    def _get_input_configuration(self):
        self._input_configuration = getattr(self, '_input_configuration', None)
        if self.id and not self._input_configuration:
            self._input_configuration = \
                NonaccumulationAdapter.objects.get(
                    link_derivative_set__graph__collection=self.id)
        return self._input_configuration

    def _set_input_configuration(self, input_configuration):
        self._input_configuration = input_configuration

    input_configuration = property(
        _get_input_configuration, _set_input_configuration)

    def get_delete_prevention_reason(self, return_dependents_only=False):
        """
        Returns a HTML formated string with a description of why
        this current measurement point cannot be deleted.
        Returning None, if no reason exist, meaning the MP can
        be deleted without breaking anything.

        @param return_dependents_only: If true, only return a string of
        the units that depends on this resource.
        """
        return None

    def is_deletable(self):
        """
        Returns true or false whether
        this current measurement point can be deleted or not.
        """
        return True

    def get_gauge_data_series(self):
        return self.input_configuration

    @property
    def has_consumption(self):
        return False

    @property
    def has_gauge(self):
        return False

    @property
    def has_rate(self):
        return True

    @staticmethod
    def get_input_configuration_choices():
        return NonaccumulationAdapter.objects.filter(
            unit='millibar',
            customer=trackuser.get_customer())
