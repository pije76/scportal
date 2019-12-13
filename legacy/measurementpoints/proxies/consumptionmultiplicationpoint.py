# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import Multiplication

from .consumptionmeasurementpoint import ConsumptionMeasurementPoint


class ConsumptionMultiplicationPoint(ConsumptionMeasurementPoint):
    """
    A C{ConsumptionMultiplicationPoint} is a L{ConsumptionMeasurementPoint}
    whose consumption is the consumption of another C{source_consumption_point}
    multiplied by a C{multiplier}.

    @ivar source_consumption_point: The source L{ConsumptionMeasurementPoint}.

    @ivar multiplier: The multiplier.
    """
    class Meta:
        proxy = True
        verbose_name = _('Multiplication measurement point')
        verbose_name_plural = _('Multiplication measurement points')
        app_label = 'customers'

    def save(self, *args, **kwargs):
        """
        C{ConsumptionMultiplicationPoint} specialization of
        L{ConsumptionMeasurementPoint.save()}.

        Construct C{consumption} from C{source_consumption_point} and
        C{multiplier}.
        """
        if self.consumption is None:
            self.consumption = Multiplication(role=DataRoleField.CONSUMPTION)
        assert self.multiplier is not None
        assert self.source_consumption_point is not None
        assert self.consumption not in \
            self.source_consumption_point.consumption.depends_on()
        self.consumption.multiplier = self.multiplier
        self.consumption.source_data_series = \
            self.source_consumption_point.consumption
        for attr in ['customer', 'unit', 'utility_type']:
            setattr(
                self.consumption, attr,
                getattr(self.consumption.source_data_series, attr))
        if self.utility_type is None:
            self.utility_type = self.source_consumption_point.utility_type
        if self.role is None:
            self.role = self.source_consumption_point.role
        super(ConsumptionMultiplicationPoint, self).save(*args, **kwargs)

    def clean(self):
        """
        C{ConsumptionMultiplicationPoint} specialization of
        L{ConsumptionMeasurementPoint.clean()}.

        Validate that a circular dependency is not about to be formed.
        """
        super(ConsumptionMultiplicationPoint, self).clean()
        if self.consumption is not None and \
                self.source_consumption_point and self.consumption in \
                self.source_consumption_point.consumption.depends_on():
            raise ValidationError(
                _(u'{measurement_point} cannot be used in the '
                  'multiplication, as it would form a circular dependency.').
                format(measurement_point=self.source_consumption_point))

    def _get_source_consumption_point(self):
        if not hasattr(self, '_source_consumption_point'):
            self._source_consumption_point = None
            if self.consumption is not None and \
                    self.consumption.id is not None:
                self._source_consumption_point = \
                    ConsumptionMeasurementPoint.objects.get(
                        graph__dataseries=self.consumption.
                        source_data_series).subclass_instance
        return self._source_consumption_point

    def _set_source_consumption_point(self, source_consumption_point):
        self._source_consumption_point = source_consumption_point

    source_consumption_point = property(_get_source_consumption_point,
                                        _set_source_consumption_point)

    def _get_multiplier(self):
        if not hasattr(self, '_multiplier'):
            self._multiplier = None
            if self.consumption is not None:
                self._multiplier = \
                    self.consumption.subclass_instance.multiplier
        return self._multiplier

    def _set_multiplier(self, multiplier):
        self._multiplier = multiplier

    multiplier = property(_get_multiplier, _set_multiplier)
