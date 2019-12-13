# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.models import DegreeDayCorrection
from legacy.measurementpoints.models import Graph
from legacy.measurementpoints.models import HeatingDegreeDays
from legacy.measurementpoints.models import Link
from legacy.datasequence_adapters.models import NonaccumulationAdapter

from .measurementpoint import MeasurementPoint


class TemperatureMeasurementPoint(MeasurementPoint):
    """
    A C{TemperatureMeasurementPoint} is a L{MeasurementPoint} that measures
    absolute or relative temperatures.

    @ivar temperature: A L{DataSeries} of temperature measurements.

    @ivar temperature_graph: A graph holding the C{temperature} L{DataSeries}.
    """
    class Meta:
        proxy = True
        verbose_name = _('Temperature measurement point')
        verbose_name_plural = _('Temperature measurement points')
        app_label = 'customers'

    def __init__(self, *args, **kwargs):
        super(TemperatureMeasurementPoint, self).__init__(*args, **kwargs)
        if self.utility_type is None:
            self.utility_type = utilitytypes.OPTIONAL_METER_CHOICES.unknown

        if self.role is None:
            self.role = self.MEASUREMENT_POINT_TEMPERATURE

    def clean(self):
        """
        Check define heating degree days: If it's used by another
        measerementpoint, it shouldn't be deleted.
        """
        super(TemperatureMeasurementPoint, self).clean()
        if not self.defines_heating_degree_days:
            reason = self.get_delete_prevention_reason(
                return_dependents_only=True)
            if reason:
                # @bug: Use ngettext to handle plural forms.
                raise ValidationError(
                    _('Heating degree days of this temperature measurement '
                      'point cannot be disabled because they are used by '
                      'the measurement points {measurement_points}').
                    format(measurement_points=unicode(reason)))

        if self.relative and self.defines_heating_degree_days:
            raise ValidationError(_('Heating degree days cannot be specified '
                                    'in terms of relative temperatures.'))

    def save(self, *args, **kwargs):
        super(TemperatureMeasurementPoint, self).save(*args, **kwargs)
        assert self.input_configuration

        graph, created = Graph.objects.get_or_create(
            collection=self,
            role=DataRoleField.ABSOLUTE_TEMPERATURE)
        if created:
            Link.objects.create(
                customer=self.customer,
                graph=graph,
                role=DataRoleField.ABSOLUTE_TEMPERATURE,
                unit='millikelvin',
                utility_type=self.utility_type,
                target=self._input_configuration)

        if self.defines_heating_degree_days:
            heating_degree_days_graph, graph_created = \
                self.graph_set.get_or_create(
                    role=DataRoleField.HEATING_DEGREE_DAYS)
            heating_degree_days, created = \
                HeatingDegreeDays.objects.get_or_create(
                    graph=heating_degree_days_graph,
                    role=DataRoleField.HEATING_DEGREE_DAYS,
                    utility_type=(
                        utilitytypes.OPTIONAL_METER_CHOICES.district_heating),
                    defaults={'derived_from': self._input_configuration})
            if not created:
                assert heating_degree_days.derived_from.id == \
                    self._input_configuration.id
        else:
            self.graph_set.filter(
                role=DataRoleField.HEATING_DEGREE_DAYS).delete()

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

    def _get_relative(self):
        if not hasattr(self, '_relative'):
            self._relative = self.input_configuration and \
                self.input_configuration.role == \
                DataRoleField.RELATIVE_TEMPERATURE
        return self._relative

    def _set_relative(self, relative):
        # @bug: It seem non-intuitive that physical_input must be set before
        # relative is set.
        self._relative = relative

    relative = property(_get_relative, _set_relative)

    def _get_heating_degree_days(self):
        return self.graph_set.get(
            role=DataRoleField.HEATING_DEGREE_DAYS).dataseries_set.all()

    heating_degree_days = property(_get_heating_degree_days)

    def _get_absolute(self):
        return not self.relative

    def _set_absolute(self, absolute):
        self.relative = not absolute

    absolute = property(_get_absolute, _set_absolute)

    @cached_property
    def defines_heating_degree_days(self):
        if not self.id:
            return False
        return HeatingDegreeDays.objects.filter(
            graph__collection=self,
            role=DataRoleField.HEATING_DEGREE_DAYS,
            utility_type=utilitytypes.METER_CHOICES.district_heating).\
            exists()

    def get_delete_prevention_reason(self, return_dependents_only=False):
        """
        Returns a HTML formated string with a description of why
        this temperature measurement point cannot be deleted.
        Returning None, if no reason exist, meaning the MP can
        be deleted without breaking anything.

        @param return_dependents_only: If true, only return a string of
        the units that depends on this resource.
        """
        degree_day_corrections = DegreeDayCorrection.objects.filter(
            degreedays__in=HeatingDegreeDays.objects.filter(
                graph__collection=self,
                role=DataRoleField.HEATING_DEGREE_DAYS,
                utility_type=utilitytypes.METER_CHOICES.district_heating))

        if len(degree_day_corrections) == 0:
            return None

        mp_string = ""
        for degree_day_correction in degree_day_corrections:
            if mp_string != "":
                mp_string += ", "
            mp_string += degree_day_correction.graph.collection.name_plain

        if return_dependents_only:
            return mp_string

        # @bug: Use ngettext to handle plural forms.
        return _('This index cannot be deleted because the following \
         depends on it: <br /> ' + mp_string)

    def is_deletable(self):
        """
        Returns true or false whether
        this temperature measurement point can be deleted or not.
        """
        degree_day_corrections = DegreeDayCorrection.objects.filter(
            degreedays__in=HeatingDegreeDays.objects.filter(
                graph__collection=self,
                role=DataRoleField.HEATING_DEGREE_DAYS,
                utility_type=utilitytypes.METER_CHOICES.district_heating))

        if len(degree_day_corrections) > 0:
            return False
        return True

    def get_gauge_data_series(self):
        """
        C{TemperatureMeasurementPoint} implementation of
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
        # NOTE: We actually only support absolute temperature
        return NonaccumulationAdapter.objects.filter(
            unit='millikelvin',
            customer=trackuser.get_customer())
