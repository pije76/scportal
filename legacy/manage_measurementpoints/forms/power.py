# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.proxies import PowerMeasurementPoint
from legacy.measurementpoints.models import Collection

from .measurementpointform import MeasurementPointForm

from gridplatform.datasequences.models import NonaccumulationDataSequence  # noqa


class PowerMeasurementPointForm(MeasurementPointForm):
    class Meta:
        model = PowerMeasurementPoint
        fields = ('name', 'parent',
                  'hidden_on_details_page', 'hidden_on_reports_page',
                  'comment', 'image')
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(PowerMeasurementPointForm, self).__init__(*args, **kwargs)
        self.fields['parent'].queryset = \
            Collection.objects.filter(
                role=Collection.GROUP,
                customer=trackuser.get_customer())

    def _get_edit_headline_display(self):
        return _(u'Edit Power Measurement Point')


class InputPowerMeasurementPointForm(PowerMeasurementPointForm):
    input_configuration = forms.ModelChoiceField(
        required=True,
        queryset=NonaccumulationDataSequence.objects.none())

    class ProxyMeta:
        fields = ('input_configuration', )

    def __init__(self, *args, **kwargs):
        super(InputPowerMeasurementPointForm, self).__init__(
            *args, **kwargs)

        self.fields['input_configuration'].queryset = \
            PowerMeasurementPoint.get_input_configuration_choices()

    def _get_new_headline_display(self):
        return _(u'New Power Measurement Point')
