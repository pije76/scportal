# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.proxies import ConsumptionMultiplicationPoint
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint

from .consumption import ConsumptionMeasurementPointForm


class MultiplicationConsumptionMeasurementPointForm(
        ConsumptionMeasurementPointForm):
    """
    MultipliedConsumptionForm
    """
    source_consumption_point = forms.ModelChoiceField(
        queryset=ConsumptionMeasurementPoint.objects.none(), required=True)
    multiplier = forms.DecimalField(localize=True)

    class Meta(ConsumptionMeasurementPointForm.Meta):
        model = ConsumptionMultiplicationPoint

    class ProxyMeta(ConsumptionMeasurementPointForm.ProxyMeta):
        fields = ConsumptionMeasurementPointForm.ProxyMeta.fields + (
            'source_consumption_point', 'multiplier')

    def __init__(self, *args, **kwargs):
        super(MultiplicationConsumptionMeasurementPointForm,
              self).__init__(*args, **kwargs)

        self.fields['source_consumption_point'].queryset = \
            ConsumptionMeasurementPoint.objects.subclass_only().filter(
                customer=trackuser.get_customer(),
                utility_type=self.instance.utility_type).exclude(
                id=self.instance.id)

    def _get_new_electricity_headline_display(self):
        return _(u'New Electricity Multiplication Point')

    def _get_new_water_headline_display(self):
        return _(u'New Water Multiplication Point')

    def _get_new_gas_headline_display(self):
        return _(u'New Gas Multiplication Point')

    def _get_new_heat_headline_display(self):
        return _(u'New Heat Multiplication Point')

    def _get_new_oil_headline_display(self):
        return _(u'New Oil Multiplication Point')

    def _get_edit_electricity_headline_display(self):
        return _(u'Edit Electricity Multiplication Point')

    def _get_edit_water_headline_display(self):
        return _(u'Edit Water Multiplication Point')

    def _get_edit_gas_headline_display(self):
        return _(u'Edit Gas Multiplication Point')

    def _get_edit_heat_headline_display(self):
        return _(u'Edit Heat Multiplication Point')

    def _get_edit_oil_headline_display(self):
        return _(u'Edit Oil Multiplication Point')
