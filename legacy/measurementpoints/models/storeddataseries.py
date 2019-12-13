# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from .dataseries import DataSeries


class StoredDataSeries(DataSeries):
    """
    A non-abstract proxy model of DataSeries that is intended for working with
    StoredData.

    @see L{ImportedMeasurementPoint}.
    """

    class Meta(DataSeries.Meta):
        proxy = True
        verbose_name = _('stored data series')
        verbose_name = _('stored data series')
        app_label = 'measurementpoints'

    def get_recursive_condense_resolution(self, resolution):
        """
        Data is stored directly, and recursive condensation is hardly ever
        bennificial.
        """
        return None
