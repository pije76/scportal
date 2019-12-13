# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytz

from django import forms
from django.utils.translation import ugettext_lazy as _

from legacy.measurementpoints.proxies import ImportedMeasurementPoint
from gridplatform.utils import units
from gridplatform.utils import utilitytypes

from .consumption import ConsumptionMeasurementPointForm


class ImportedMeasurementPointForm(ConsumptionMeasurementPointForm):
    upload_file = forms.FileField(required=True)
    consumption_column = forms.IntegerField()
    timezone = forms.TypedChoiceField(
        choices=[(x, x) for x in pytz.common_timezones],
        coerce=pytz.timezone)
    unit = forms.ChoiceField()

    class Meta:
        model = ImportedMeasurementPoint
        fields = ('name', 'parent', 'billing_meter_number',
                  'billing_installation_number', 'relay',
                  'hidden_on_details_page', 'hidden_on_reports_page',
                  'comment', 'image')
        localized_fields = '__all__'

    class ProxyMeta(ConsumptionMeasurementPointForm.ProxyMeta):
        fields = ConsumptionMeasurementPointForm.ProxyMeta.fields + \
            ('upload_file', 'consumption_column', 'timezone', 'unit')

    def __init__(self, *args, **kwargs):
        super(ImportedMeasurementPointForm, self).__init__(
            *args, **kwargs)

        utility_type = self.instance.utility_type

        if utility_type == utilitytypes.METER_CHOICES.electricity:
            self.fields['unit'].choices = units.WATT_HOUR_ENERGY_CHOICES
        elif utility_type == utilitytypes.METER_CHOICES.district_heating:
            self.fields['unit'].choices = units.ENERGY_CHOICES
        elif utility_type in [utilitytypes.METER_CHOICES.gas,
                              utilitytypes.METER_CHOICES.water,
                              utilitytypes.METER_CHOICES.oil]:
            self.fields['unit'].choices = units.VOLUME_CHOICES
        else:
            raise ValueError('Unsupported utility type %r' % utility_type)

    def _get_new_electricity_headline_display(self):
        return _(u'New Imported Electricity Measurement Point')

    def _get_new_heat_headline_display(self):
        return _(u'New Imported Heat Measurement Point')

    def _get_new_water_headline_display(self):
        return _(u'New Imported Water Measurement Point')

    def _get_new_gas_headline_display(self):
        return _(u'New Imported Gas Measurement Point')

    def _get_new_oil_headline_display(self):
        return _(u'New Imported Oil Measurement Point')


class ImportedMeasurementPointUpdateForm(ConsumptionMeasurementPointForm):
    def _get_new_electricity_headline_display(self):
        return _(u'Edit Imported Electricity Measurement Point')
