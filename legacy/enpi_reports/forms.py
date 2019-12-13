# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from datetime import datetime
from datetime import time
from datetime import timedelta

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.utils.translation import ugettext_lazy as _

from extra_views import InlineFormSet

from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.models import DataSeries
from legacy.measurementpoints.models import Link
from gridplatform.trackuser import get_customer
from gridplatform.utils import condense
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.formsets import SurvivingFormsModelFormSetMixin

from .models import ENPIUseArea
from .models import ENPIReport


class BaseENPIUseAreaFormSet(SurvivingFormsModelFormSetMixin,
                             BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.measurement_point_queryset = ConsumptionMeasurementPoint.\
            objects.subclass_only().filter(
                utility_type__in=[
                    utilitytypes.OPTIONAL_METER_CHOICES.electricity,
                    utilitytypes.OPTIONAL_METER_CHOICES.district_heating
                ],
                hidden_on_reports_page=False).decrypting_order_by(
                'name')

        self.energy_driver_queryset = DataSeries.objects.exclude(
            subclass=ContentType.objects.get_for_model(
                Link, for_concrete_model=False)
        ).filter(
            unit=kwargs.pop('energy_driver_unit'),
            role__in=[
                DataRoleField.EMPLOYEES,
                DataRoleField.AREA,
                DataRoleField.PRODUCTION,
                DataRoleField.HEATING_DEGREE_DAYS]).decrypting_order_by(
            'name')

        super(BaseENPIUseAreaFormSet, self).__init__(*args, **kwargs)

    def add_fields(self, form, index):
        """
        Override of C{BaseInlineFormSet.add_fields()}.

        The parent method is used to add all fields to all forms created by
        C{BaseInlineFormSet}, including the C{empty_form}.

        This override is used as a hook to make sure these fields are
        configured correctly.  In particular formset specific querysets and
        choices are set on relevant fields.
        """
        super(BaseENPIUseAreaFormSet, self).add_fields(form, index)

        form.fields['measurement_points'].queryset = \
            self.measurement_point_queryset
        form.fields['energy_driver'].queryset = \
            self.energy_driver_queryset

    def clean(self):
        super(BaseENPIUseAreaFormSet, self).clean()
        if any(self.errors):
            return

        # An enpi report has to include at least one form
        if not self.surviving_forms():
            raise forms.ValidationError(
                _('Include at least one area of energy use'))


class ENPIUseAreaFormSet(InlineFormSet):
    model = ENPIUseArea
    formset_class = BaseENPIUseAreaFormSet
    extra = 1

    def get_formset_kwargs(self):
        kwargs = super(ENPIUseAreaFormSet, self).get_formset_kwargs()
        if self.object:
            kwargs['energy_driver_unit'] = self.object.energy_driver_unit
        else:
            kwargs['energy_driver_unit'] = self.kwargs['energy_driver_unit']
        return kwargs


class GenerateENPIReportForm(forms.Form):
    """
    A C{Form} for generating a particular EnPI report.

    Such a report is generated from a L{ENPIReport} instance,
    C{enpi_report}, a C{from_date} and a C{to_date}.
    """
    enpi_report = forms.ModelChoiceField(
        queryset=ENPIReport.objects.none())
    from_date = forms.DateField()
    to_date = forms.DateField()

    def __init__(self, *args, **kwargs):
        """
        Expands the valid choices of L{ENPIReport} instances to all those
        available to current customer.
        """
        super(GenerateENPIReportForm, self).__init__(*args, **kwargs)
        self.fields['enpi_report'].queryset = \
            ENPIReport.objects.filter(customer=get_customer())

    def clean(self):
        """
        Checks that C{from_date} is before C{to_date} if both are set.

        @return: The usual C{cleaned_data} dictionary, but with a few extra key
        value pairs.  Notably C{'from_timestamp'}, C{'to_timestamp'} and
        C{'sample_resolution'}.
        """
        super(GenerateENPIReportForm, self).clean()
        if self.cleaned_data['from_date'] > self.cleaned_data['to_date']:
            raise ValidationError(
                _(u'The start date must be before the end date.'))

        from_date = self.cleaned_data['from_date']
        to_date = self.cleaned_data['to_date']
        timezone = get_customer().timezone
        time_span = to_date - from_date + timedelta(days=1)

        if time_span.days > 365 * 2:
            if from_date.day != 1 or from_date.month != 1:
                raise ValidationError(
                    _(u'From date must be the first day of the year when '
                      u'selecting more than two years'))
            if to_date.day != 31 or to_date.month != 12:
                raise ValidationError(
                    _(u'To date must be the last day of the year when '
                      u'selecting more than two years'))
            self.cleaned_data['sample_resolution'] = condense.YEARS
        elif time_span.days > 365:
            if from_date.day != 1 or from_date.month not in [1, 4, 7, 10]:
                raise ValidationError(
                    _(u'From date must be the first day in a quarter when '
                      u'selecting more than one year'))

            check_month = to_date + timedelta(days=1)
            if to_date.month == check_month.month or to_date.month not in (
                    3, 6, 9, 12):
                raise ValidationError(
                    _(u'To date must be the last day in a quarter when '
                      u'selecting more than one year'))
            self.cleaned_data['sample_resolution'] = condense.QUARTERS
        else:
            if from_date.day != 1:
                raise ValidationError(
                    _(u'From date must be the first day in a month'))

            check_month = to_date + timedelta(days=1)
            if to_date.month == check_month.month:
                raise ValidationError(
                    _(u'To date must be the last day in a month'))
            self.cleaned_data['sample_resolution'] = condense.MONTHS

        if not self.cleaned_data['enpi_report'].enpiusearea_set.exists():
            raise ValidationError(
                _('This EnPI report does not cover any area of energy use.'))

        assert 'sample_resolution' in self.cleaned_data
        self.cleaned_data['from_timestamp'] = timezone.localize(
            datetime.combine(from_date, time()))
        self.cleaned_data['to_timestamp'] = timezone.localize(
            datetime.combine(to_date, time())) + RelativeTimeDelta(days=1)

        return self.cleaned_data
