# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.proxies import ReactiveEnergyMeasurementPoint
from legacy.measurementpoints.models import Collection

from .measurementpointform import MeasurementPointForm

from gridplatform.datasequences.models import NonaccumulationDataSequence  # noqa


class ReactiveEnergyMeasurementPointForm(MeasurementPointForm):
    class Meta:
        model = ReactiveEnergyMeasurementPoint
        fields = ('name', 'parent',
                  'hidden_on_details_page', 'hidden_on_reports_page',
                  'comment', 'image')
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ReactiveEnergyMeasurementPointForm, self).__init__(
            *args, **kwargs)
        self.fields['parent'].queryset = \
            Collection.objects.filter(
                role=Collection.GROUP,
                customer=trackuser.get_customer())

    def _get_edit_headline_display(self):
        return _(u'Edit Reactive Energy Measurement Point')


class InputReactiveEnergyMeasurementPointForm(ReactiveEnergyMeasurementPointForm):
    input_configuration = forms.ModelChoiceField(
        required=True,
        queryset=NonaccumulationDataSequence.objects.none())

    class ProxyMeta:
        fields = ('input_configuration', )

    def __init__(self, *args, **kwargs):
        super(InputReactiveEnergyMeasurementPointForm, self).__init__(
            *args, **kwargs)

        self.fields['input_configuration'].queryset = \
            ReactiveEnergyMeasurementPoint.get_input_configuration_choices()

    def _get_new_headline_display(self):
        return _(u'New Reactive Energy Measurement Point')
