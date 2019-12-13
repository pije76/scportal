# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.devices.models import Meter
from legacy.measurementpoints.proxies import TemperatureMeasurementPoint
from legacy.measurementpoints.models import Collection

from .measurementpointform import MeasurementPointForm

from gridplatform.datasequences.models import \
    NonaccumulationDataSequence


class TemperatureMeasurementPointForm(MeasurementPointForm):
    """
    A C{TemperatureMeasurementPointForm} sets properties on a
    L{TemperatureMeasurementPoint} that can be both set when creating and when
    updating.
    """
    defines_heating_degree_days = forms.BooleanField(required=False)

    class Meta:
        model = TemperatureMeasurementPoint
        fields = ('name', 'parent', 'relay',
                  'hidden_on_details_page', 'hidden_on_reports_page')
        localized_fields = '__all__'

    class ProxyMeta:
        fields = ('defines_heating_degree_days',)

    def __init__(self, *args, **kwargs):
        super(TemperatureMeasurementPointForm, self).__init__(*args, **kwargs)
        self.fields['parent'].queryset = \
            Collection.objects.filter(
                role=Collection.GROUP,
                customer=trackuser.get_customer())

        self.fields['relay'].queryset = \
            Meter.objects.filter(
                customer=trackuser.get_customer(), relay_enabled=True)

    def _get_edit_headline_display(self):
        if self.instance.relative:
            return _(u'Edit Relative Temperature Measurement Point')
        else:
            return _(u'Edit Absolute Temperature Measurement Point')


class InputTemperatureMeasurementPointForm(TemperatureMeasurementPointForm):
    """
    An C{InputTemperatureMeasurementPointForm} is a
    L{TemperatureMeasurementPointForm}, that in addition also sets properties
    that can only be set when creating a L{TemperatureMeasurementPoint}.
    """
    input_configuration = forms.ModelChoiceField(
        required=True,
        queryset=NonaccumulationDataSequence.objects.none())

    class ProxyMeta:
        fields = TemperatureMeasurementPointForm.ProxyMeta.fields + \
            ('input_configuration', )

    def __init__(self, *args, **kwargs):
        super(InputTemperatureMeasurementPointForm, self).__init__(
            *args, **kwargs)

        self.fields['input_configuration'].queryset = \
            TemperatureMeasurementPoint.get_input_configuration_choices()

    def _get_new_headline_display(self):
        return _(u'New Temperature Measurement Point')
