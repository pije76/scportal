# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from legacy.display_widgets.models import DashboardWidget
from gridplatform import trackuser
from legacy.devices.models import Meter

from .collection import CollectionForm


# THIS FILE IS DEPRECATED!!!

class MeasurementPointBaseForm(CollectionForm):
    """
    Abstract class
    """

    class Meta (CollectionForm.Meta):
        fields = ('name', 'parent', 'billing_meter_number',
                  'billing_installation_number', 'gauge_lower_threshold',
                  'gauge_upper_threshold', 'gauge_max', 'gauge_min',
                  'gauge_colours', 'relay', 'gauge_preferred_unit',
                  'hidden_on_details_page')

    relay = forms.ModelChoiceField(
        queryset=None, required=False)

    def __init__(self, *args, **kwargs):
        super(MeasurementPointBaseForm, self).__init__(*args, **kwargs)

        self.fields["relay"].queryset = Meter.objects.filter(
            relay_enabled=True, customer=trackuser.get_customer())

        # Localize gauge input fields
        for item in [self.fields['gauge_lower_threshold'],
                     self.fields['gauge_upper_threshold'],
                     self.fields['gauge_min'],
                     self.fields['gauge_max']]:
            item.localize = True
            item.widget.is_localized = True

    def clean(self):
        cleaned_data = super(MeasurementPointBaseForm, self).clean()

        if self.errors:
            return cleaned_data

        # Checking if gauge_min is present;
        # when creating MP, gauge setup is unavailable.
        if cleaned_data.get('gauge_min') is not None:
            gauge_min = cleaned_data['gauge_min']
            gauge_max = cleaned_data['gauge_max']
            gauge_lower_threshold = cleaned_data['gauge_lower_threshold']
            gauge_upper_threshold = cleaned_data['gauge_upper_threshold']
            gauge_colours = cleaned_data['gauge_colours']

            # If Gauge widget is present on the Dashboard, verify that
            # that values are not corrupted by the user.
            widget = DashboardWidget.objects.filter(
                collection=self.instance.id,
                widget_type=DashboardWidget.GAUGE)
            if widget and (gauge_lower_threshold is None or
                           gauge_upper_threshold is None or
                           gauge_min is None or
                           gauge_max is None or
                           gauge_colours is None):
                    raise forms.ValidationError(
                        _('Gauge widget is present on the dashboard; \
                            corrupting these values are not allowed'))
            else:
                if gauge_max is not None and \
                    gauge_min is not None and \
                        gauge_max <= gauge_min:
                    raise forms.ValidationError(
                        _('Maximum value must be above minumum value'))
                if gauge_lower_threshold is not None and \
                    gauge_lower_threshold is not None and \
                        gauge_lower_threshold < gauge_min:
                    raise forms.ValidationError(
                        _('Lower threshold must be above minumum value'))
                if gauge_upper_threshold is not None and \
                    gauge_max is not None \
                        and gauge_upper_threshold > gauge_max:
                    raise forms.ValidationError(
                        _('Upper threshold must be below maximum value'))
                if gauge_upper_threshold is not None and \
                    gauge_lower_threshold is not None \
                        and gauge_upper_threshold <= gauge_lower_threshold:
                    raise forms.ValidationError(
                        _('Upper threshold must be above lower threshold'))

        return cleaned_data

    def save(self, commit=True):
        super(MeasurementPointBaseForm, self).save(commit=False)

        self.instance.relay = self.cleaned_data["relay"]
        self.instance.hidden_on_details_page = \
            self.cleaned_data['hidden_on_details_page']

        if commit:
            self.instance.save()
        return self.instance
