# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.proxies import ProductionMeasurementPoint
from legacy.measurementpoints.models import Collection

from .measurementpointform import MeasurementPointForm

from gridplatform.productions.models import Production


class ProductionMeasurementPointForm(MeasurementPointForm):
    """
    A C{ProductionMeasurementPointForm} sets properties on a
    L{ProductionMeasurementPoint} that can be both set when creating and when
    updating.
    """
    class Meta:
        model = ProductionMeasurementPoint
        fields = ('name', 'parent',
                  'hidden_on_details_page', 'hidden_on_reports_page',
                  'comment', 'image')
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ProductionMeasurementPointForm, self).__init__(*args, **kwargs)
        self.fields['parent'].queryset = \
            Collection.objects.filter(
                role=Collection.GROUP,
                customer=trackuser.get_customer())

    def _get_edit_headline_display(self):
        return _(u'Edit Production Measurement Point')


class InputProductionMeasurementPointForm(ProductionMeasurementPointForm):
    """
    An C{InputProductionMeasurementPointForm} is a
    L{TemperatureMeasurementPointForm}, that in addition also sets properties
    that can only be set when creating a L{TemperatureMeasurementPoint}.
    """
    input_configuration = forms.ModelChoiceField(
        required=True,
        queryset=Production.objects.none())

    class ProxyMeta:
        fields = ('input_configuration', )

    def __init__(self, *args, **kwargs):
        super(InputProductionMeasurementPointForm, self).__init__(
            *args, **kwargs)

        self.fields['input_configuration'].queryset = \
            ProductionMeasurementPoint.get_input_configuration_choices()

    def _get_new_headline_display(self):
        return _(u'New Production Measurement Point')
