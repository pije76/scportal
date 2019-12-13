# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.models import Graph
from legacy.measurementpoints.models import Link
from legacy.datasequence_adapters.models import NonaccumulationAdapter

from .measurementpoint import MeasurementPoint


class VoltageMeasurementPoint(MeasurementPoint):
    """
    A C{VoltageMeasurementPoint} is a L{MeasurementPoint} that measures
    voltage.
    """
    class Meta:
        proxy = True
        verbose_name = _('Voltage measurement point')
        verbose_name_plural = _('Voltage measurement points')
        app_label = 'customers'

    def __init__(self, *args, **kwargs):
        super(VoltageMeasurementPoint, self).__init__(*args, **kwargs)
        if self.utility_type is None:
            self.utility_type = utilitytypes.OPTIONAL_METER_CHOICES.electricity

        if self.role is None:
            self.role = self.MEASUREMENT_POINT_VOLTAGE

    def save(self, *args, **kwargs):
        super(VoltageMeasurementPoint, self).save(*args, **kwargs)
        assert self.input_configuration

        graph, created = Graph.objects.get_or_create(
            collection=self,
            role=DataRoleField.VOLTAGE)
        if created:
            Link.objects.create(
                customer=self.customer,
                graph=graph,
                role=DataRoleField.VOLTAGE,
                unit='millivolt',
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
        """
        C{VoltageMeasurementPoint} implementation of
        L{MeasurementPoint.get_gauge_data_series()}
        """
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
        """
        Get L{NonaccumulationAdapter} choices.
        """
        return NonaccumulationAdapter.objects.filter(
            unit='millivolt',
            customer=trackuser.get_customer())
