# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.proxies import DistrictHeatingMeasurementPoint
from gridplatform.utils import utilitytypes
from gridplatform.consumptions.models import Consumption

from .consumption import ConsumptionMeasurementPointForm
from .consumption import InputConsumptionMeasurementPointForm


class DistrictHeatingMeasurementPointCreateForm(
        InputConsumptionMeasurementPointForm):
    volume_input = forms.ModelChoiceField(
        queryset=Consumption.objects.none())

    class Meta(InputConsumptionMeasurementPointForm.Meta):
        model = DistrictHeatingMeasurementPoint

    class ProxyMeta(InputConsumptionMeasurementPointForm.ProxyMeta):
        fields = InputConsumptionMeasurementPointForm.ProxyMeta.fields + (
            'volume_input', )

    def __init__(self, *args, **kwargs):
        super(DistrictHeatingMeasurementPointCreateForm,
              self).__init__(*args, **kwargs)

        self.fields['consumption_input'].queryset = \
            Consumption.objects.subclass_only().filter(
                customer=trackuser.get_customer(),
                utility_type=utilitytypes.METER_CHOICES.district_heating)

        self.fields['volume_input'].queryset = \
            Consumption.objects.subclass_only().filter(
                customer=trackuser.get_customer(),
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water)

    def _get_new_headline_display(self):
        return _(u'New District Heating Measurement Point')

    def _get_edit_headline_display(self):
        return _(u'Edit District Heating Measurement Point')


class DistrictHeatingMeasurementPointEditForm(
        ConsumptionMeasurementPointForm):

    class Meta(InputConsumptionMeasurementPointForm.Meta):
        model = DistrictHeatingMeasurementPoint
        exclude = ('consumption_input', 'volume_input')

    def _get_new_headline_display(self):
        return _(u'New District Heating Measurement Point')

    def _get_edit_headline_display(self):
        return _(u'Edit District Heating Measurement Point')
