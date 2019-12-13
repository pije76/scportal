# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.utils import condense

from .dataseries import DataSeries


class Multiplication(DataSeries):
    """
    A C{Multiplication} is a data series, where the data samples are defined in
    terms of a C{source_data_series} multiplied with a C{multiplier}.
    """
    multiplier = models.DecimalField(decimal_places=3, max_digits=10)
    source_data_series = models.ForeignKey(
        DataSeries, on_delete=models.PROTECT,
        related_name='multiplied_data_series_derivative_set')

    class Meta(DataSeries.Meta):
        verbose_name = _('mulitplication')
        verbose_name_plural = _('multiplications')
        app_label = 'measurementpoints'

    def _get_samples(self, from_timestamp, to_timestamp):
        """
        C{Multiplication} implementation of
        L{DataSeries.get_raw_data_samples()}.
        """
        for sample in self.source_data_series.subclass_instance.\
                get_samples(from_timestamp, to_timestamp):
            yield sample._replace(
                physical_quantity=(sample.physical_quantity * self.multiplier))

    def _condense_data_samples_recursive(
            self, from_timestamp, sample_resolution, to_timestamp):
        for sample in self.source_data_series.subclass_instance.\
                get_condensed_samples(
                    from_timestamp, sample_resolution, to_timestamp):
            yield sample._replace(
                physical_quantity=(sample.physical_quantity * self.multiplier))

    def depends_on(self):
        """
        C{Multiplication} implementation of L{DataSeries.depends_on()}.
        """
        result = list(self.source_data_series.subclass_instance.depends_on())
        result.append(self.source_data_series.subclass_instance)
        return result

    def get_recursive_condense_resolution(self, resolution):
        if condense.is_finer_resolution(resolution, condense.HOURS):
            return None
        else:
            return condense.next_resolution(resolution)
