# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.proxies import ConsumptionMeasurementPointSummation  # noqa
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint

from .consumption import ConsumptionMeasurementPointForm


class ConsumptionMeasurementPointSummationForm(
        ConsumptionMeasurementPointForm):
    class Meta(ConsumptionMeasurementPointForm.Meta):
        model = ConsumptionMeasurementPointSummation

    plus_consumption_measurement_points = forms.ModelMultipleChoiceField(
        queryset=ConsumptionMeasurementPoint.objects.none(), required=False)
    minus_consumption_measurement_points = forms.ModelMultipleChoiceField(
        queryset=ConsumptionMeasurementPoint.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super(ConsumptionMeasurementPointSummationForm,
              self).__init__(*args, **kwargs)

        self.fields['plus_consumption_measurement_points'].queryset = \
            ConsumptionMeasurementPoint.objects.filter(
                customer=trackuser.get_customer(),
                utility_type=self.instance.utility_type).exclude(
                id=self.instance.id)
        self.fields['minus_consumption_measurement_points'].queryset = \
            ConsumptionMeasurementPoint.objects.filter(
                customer=trackuser.get_customer(),
                utility_type=self.instance.utility_type).exclude(
                id=self.instance.id)

        if kwargs.get('instance'):
            # initialise from existing instance when provided
            self.fields['plus_consumption_measurement_points'].initial = \
                [mp.id for mp in
                 kwargs['instance'].plus_consumption_measurement_points]
            self.fields['minus_consumption_measurement_points'].initial = \
                [mp.id for mp in
                 kwargs['instance'].minus_consumption_measurement_points]

    def clean(self):
        self.instance.role = ConsumptionMeasurementPointSummation.\
            CONSUMPTION_MEASUREMENT_POINT
        self.instance.plus_consumption_measurement_points = \
            self.cleaned_data['plus_consumption_measurement_points']
        self.instance.minus_consumption_measurement_points = \
            self.cleaned_data['minus_consumption_measurement_points']
        self.instance.utility_type
        super(ConsumptionMeasurementPointSummationForm, self).clean()
        return self.cleaned_data

    def save(self, commit=True):
        """
        C{ConsumptionMeasurementPointSummationForm} implementation
        of C{ModelForm.save()}.
        """
        super(ConsumptionMeasurementPointSummationForm,
              self).save(commit=False)

        if commit:
            self.instance.save()

        return self.instance

    def _get_new_electricity_headline_display(self):
        return _(u'New Electricity Summation Point')

    def _get_new_water_headline_display(self):
        return _(u'New Water Summation Point')

    def _get_new_gas_headline_display(self):
        return _(u'New Gas Summation Point')

    def _get_new_heat_headline_display(self):
        return _(u'New Heat Summation Point')

    def _get_new_oil_headline_display(self):
        return _(u'New Oil Summation Point')

    def _get_edit_electricity_headline_display(self):
        return _(u'Edit Electricity Summation Point')

    def _get_edit_water_headline_display(self):
        return _(u'Edit Water Summation Point')

    def _get_edit_gas_headline_display(self):
        return _(u'Edit Gas Summation Point')

    def _get_edit_heat_headline_display(self):
        return _(u'Edit Heat Summation Point')

    def _get_edit_oil_headline_display(self):
        return _(u'Edit Oil Summation Point')
