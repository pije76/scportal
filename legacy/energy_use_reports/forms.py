# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from gridplatform.trackuser import get_customer
from gridplatform.reports.views import is_queue_too_long

from .models import EnergyUseReport


class GenerateEnergyUseReportForm(forms.Form):
    """
    A C{Form} for generating a particular energy use report.

    Such a report is generated from a L{EnergyUseReport} instance,
    C{energy_use_report}, a C{from_date} and a C{to_date}.
    """
    energy_use_report = forms.ModelChoiceField(
        queryset=EnergyUseReport.objects.none())
    from_date = forms.DateField()
    to_date = forms.DateField()

    previous_period_from_date = forms.DateField()
    previous_period_to_date = forms.DateField()

    include_cost = forms.BooleanField(required=False)
    include_co2 = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        """
        Expands the valid choices of L{EnergyUseReport} instances to all those
        available to current customer.
        """
        super(GenerateEnergyUseReportForm, self).__init__(*args, **kwargs)
        self.fields['energy_use_report'].queryset = \
            EnergyUseReport.objects.filter(customer=get_customer())

    def clean(self):
        """
        Checks that C{from_date} is before C{to_date} if both are set.
        """
        super(GenerateEnergyUseReportForm, self).clean()
        if 'from_date' in self.cleaned_data and \
                'to_date' in self.cleaned_data and \
                self.cleaned_data['from_date'] > self.cleaned_data['to_date']:
            raise ValidationError(
                _(u'The start date must be before the end date.'))

        if 'previous_period_from_date' in self.cleaned_data and \
                'previous_period_to_date' in self.cleaned_data and \
                (
                    self.cleaned_data['previous_period_from_date'] >
                    self.cleaned_data['previous_period_to_date']):
            raise ValidationError(
                _('The start date of the previous period must be before '
                  'the end date of the previous period.'))

        if is_queue_too_long(
                4, 'legacy.energy_use_reports.tasks.EnergyUseReportTask'):
            raise ValidationError(
                _(u'Report generation queue is to long,'
                  ' please try again later'))
        return self.cleaned_data
