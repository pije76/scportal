# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.utils.unitconversion import PhysicalQuantity

from .dataseries import DataSeries
from .mixins import DevelopmentRateComputation
from .mixins import CacheOptimizedCalculateDevelopmentMixin


class IndexCalculation(CacheOptimizedCalculateDevelopmentMixin,
                       DevelopmentRateComputation,
                       DataSeries):
    """
    A C{Indexcalculation} is a L{DataSeries} derived from a consumption
    L{DataSeries} and a index L{DataSeries}.

    @ivar index: The index L{DataSeries} used in the index calculation.

    @ivar consumption: The consumption L{DataSeries} used in the consumption
    calculation.
    """
    index = models.ForeignKey(DataSeries, on_delete=models.PROTECT,
                              related_name='indexcalculation_derivative_set')
    consumption = models.ForeignKey(
        DataSeries, on_delete=models.CASCADE,
        related_name='indexcalculation_consumption_derivative_set')

    class Meta(DataSeries.Meta):
        verbose_name = _('index calculation')
        verbose_name_plural = _('index calculations')
        app_label = 'measurementpoints'

    def clean_fields(self, exclude=None):
        super(IndexCalculation, self).clean_fields(exclude=exclude)

        if exclude and 'unit' in exclude:
            # unit not given by user, and should be inferred if possible and
            # not previously set.
            if not self.unit and self.index and self.consumption:
                self.unit = (
                    PhysicalQuantity(1, self.index.unit) *
                    PhysicalQuantity(1, self.consumption.unit)).units

    def save(self, *args, **kwargs):
        """
        Save various components of this C{IndexCalculation}.
        """
        # Will raise an exception if units are not compatible.
        (
            PhysicalQuantity(1, self.index.unit) *
            PhysicalQuantity(1, self.consumption.unit)).convert(self.unit)

        return super(IndexCalculation, self).save(*args, **kwargs)

    def _compute_sample(self, development, rate):
        """
        C{IndexCalculation} implementation of
        L{DevelopmentRateComputation._compute_sample()}.
        """
        return rate * development

    def _get_accumulation(self):
        """
        C{IndexCalculation} implementation of
        L{DevelopmentRateComputation._get_accumulation()}.
        """
        return self.consumption.subclass_instance

    def _get_rate(self):
        """
        C{IndexCalculation} implementation of
        L{DevelopmentRateComputation._get_rate()}.
        """
        return self.index.subclass_instance

    def depends_on(self):
        """
        C{IndexCalculation} implementation of L{DataSeries.depends_on()}.
        """
        return self.consumption.subclass_instance.depends_on() + \
            self.index.subclass_instance.depends_on()
