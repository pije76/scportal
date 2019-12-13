# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import itertools

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from legacy.measurementpoints import default_unit_for_data_series
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import Summation
from legacy.measurementpoints.models import SummationTerm

from .consumptionmeasurementpoint import ConsumptionMeasurementPoint


class ConsumptionMeasurementPointSummation(ConsumptionMeasurementPoint):
    """
    A C{ConsumptionMeasurementPointSummation} is a
    L{ConsumptionMeasurementPoint} whose consumption L{DataSeries} is defined
    as the sum of other L{ConsumptionMeasurementPoint}s consumption data
    series.  This is only well-defined if all the involved
    L{ConsumptionMeasurementPoint}s have the same resource type.

    @ivar consumption: A L{DataSeries} defined as the interpolated sum of the
    consumption data series of the related consumption measurement points.
    This property overrides that of L{ConsumptionMeasurementPoint}.

    @ivar plus_consumption_measurement_points: A list of consumption
    measurement points to be added in this summation.

    @ivar minus_consumption_measurement_points: A list of consumption
    measurement points to be subtracted in this summation.
    """

    class Meta(ConsumptionMeasurementPoint.Meta):
        proxy = True
        verbose_name = _('Summation measurement point')
        verbose_name_plural = _('Summation measurement points')
        app_label = 'customers'

    def clean(self):
        super(ConsumptionMeasurementPointSummation, self).clean()
        if list(self.plus_consumption_measurement_points) == [] and \
                list(self.minus_consumption_measurement_points) == []:
            raise ValidationError(
                _(u'At least one measurement point must be selected.'))

        for ds in [mp.consumption for mp in itertools.chain(
                self.plus_consumption_measurement_points,
                self.minus_consumption_measurement_points)]:
            if self.consumption == ds or self.consumption in ds.depends_on():
                raise ValidationError(
                    _(u'{measurement_point} cannot be included in the '
                      'summation, as it would form circular dependencies.').
                    format(measurement_point=ds.graph.
                           collection.subclass_instance))

    def save(self, *args, **kwargs):
        """
        Saves this C{ConsumptionMeasurementPointSummation}, by creating and/or
        updating the underlying relations.
        """
        super(ConsumptionMeasurementPointSummation, self).save(*args, **kwargs)

        self.consumption.plus_data_series = [
            mp.consumption for mp in self.plus_consumption_measurement_points]
        self.consumption.minus_data_series = [
            mp.consumption for mp in self.minus_consumption_measurement_points]
        self.consumption.save()

    def _get_consumption(self):
        """
        C{ConsumptionMeasurementPointSummation} specialziation of
        L{ConsumptionMeasurementPoint}.

        @return: Returns the current consumption DataSeries. If no such
        DataSeries is defined, a new consumption DataSeries is returned.
        """
        if super(ConsumptionMeasurementPointSummation, self).\
                _get_consumption() is None:
            self.consumption = Summation(
                role=DataRoleField.CONSUMPTION,
                customer=self.customer,
                utility_type=self.utility_type,
                unit=default_unit_for_data_series(
                    DataRoleField.CONSUMPTION,
                    self.utility_type))
        return super(ConsumptionMeasurementPointSummation, self).\
            _get_consumption()

    consumption = property(
        _get_consumption,
        ConsumptionMeasurementPoint._set_consumption)

    def _set_plus_consumption_measurement_points(self, mp_list):
        self._positive_mp_terms = mp_list

    def _get_plus_consumption_measurement_points(self):
        if not hasattr(self, '_positive_mp_terms'):
            self._positive_mp_terms = list(
                ConsumptionMeasurementPoint.objects.filter(
                    graph__dataseries__summationterm__sign=SummationTerm.PLUS,
                    graph__dataseries__summationterm__summation=self.
                    consumption))
        return self._positive_mp_terms

    plus_consumption_measurement_points = property(
        _get_plus_consumption_measurement_points,
        _set_plus_consumption_measurement_points)

    def _set_minus_consumption_measurement_points(self, mp_list):
        self._negative_mp_terms = mp_list

    def _get_minus_consumption_measurement_points(self):
        if not hasattr(self, '_negative_mp_terms'):
            self._negative_mp_terms = list(
                ConsumptionMeasurementPoint.objects.filter(
                    graph__dataseries__summationterm__sign=SummationTerm.MINUS,
                    graph__dataseries__summationterm__summation=self.
                    consumption))
        return self._negative_mp_terms

    minus_consumption_measurement_points = property(
        _get_minus_consumption_measurement_points,
        _set_minus_consumption_measurement_points)
