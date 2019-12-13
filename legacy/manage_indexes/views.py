# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module defines the views of the manage_indexes Django app.
"""

from django import forms
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from extra_views import CreateWithInlinesView
from extra_views import UpdateWithInlinesView
from extra_views import InlineFormSet

from gridplatform.trackuser import get_customer
from gridplatform.users.decorators import auth_or_error
from gridplatform.users.decorators import customer_admin_or_error
from gridplatform.utils import units
from gridplatform.utils import utilitytypes
from gridplatform.utils.formsets import SurvivingFormsModelFormSetMixin
from gridplatform.utils.generic_views import LocalizedInlineFormSetMixin
from gridplatform.utils.views import json_list_options
from gridplatform.utils.views import json_list_response
from gridplatform.utils.views import render_to
from legacy.indexes.models import DerivedIndexPeriod
from legacy.indexes.models import Index
from legacy.indexes.models import SeasonIndexPeriod
from legacy.measurementpoints.fields import DataRoleField


@auth_or_error
def listing(request):
    """
    The view function for listing indexes visible to the current user.
    """
    return TemplateView.as_view(
        template_name="manage_indexes/indexes_list.html")(request)


class DerivedPeriodForm(forms.ModelForm):
    class Meta:
        model = DerivedIndexPeriod
        fields = [
            'from_date', 'other_index', 'coefficient', 'constant', 'roof']

    def __init__(self, *args, **kwargs):
        inline_instance = kwargs.pop('inline_instance')
        super(DerivedPeriodForm, self).__init__(*args, **kwargs)
        assert inline_instance.view.utility_type is not None
        assert inline_instance.view.role is not None
        self.fields['other_index'].queryset = Index.objects.filter(
            utility_type=inline_instance.view.utility_type,
            role=inline_instance.view.role)
        if self.instance.id:
            self.fields['other_index'].queryset = self.fields['other_index'].\
                queryset.exclude(
                    id__in=[
                        i.id for i in self.instance.index.get_derivatives()])


class PeriodFormSet(SurvivingFormsModelFormSetMixin, BaseInlineFormSet):
    def clean(self):
        super(PeriodFormSet, self).clean()

        surviving_forms = self.surviving_forms()
        if len(surviving_forms) < 1:
            raise ValidationError(_('At least one period must be defined'))

        from_dates = []
        for form in surviving_forms:
            if 'from_date' not in form.cleaned_data:
                continue
            if form.cleaned_data['from_date'] in from_dates:
                raise ValidationError(
                    _('No two periods can have the same from date'))
            from_dates.append(form.cleaned_data['from_date'])


@auth_or_error
@json_list_response
def list_json(request):
    """
    View function for listing rendered indexes in JSON container.

    Returns a dictionary with two keys, C{"total"} and C{"data"},
    where C{["totoal"]} is the total number of indexes matching a
    filter, and C{["data"]} is a list of HTML strings reprecenting
    indexes to be displayed.
    """
    options = json_list_options(request)

    indexes = list(
        Index.objects.all())

    order_map = {
        'name': lambda index: unicode(index.name_plain.lower()),
        'unit': lambda index: unicode(index.unit)}

    if options['order_by'] in order_map:
        indexes.sort(key=order_map[options['order_by']])

    return (order_map, indexes, "manage_indexes/index_block.html")


class DerivedPeriodInline(LocalizedInlineFormSetMixin, InlineFormSet):
    model = DerivedIndexPeriod
    form_class = DerivedPeriodForm
    fk_name = 'index'
    extra = 1
    formset_class = PeriodFormSet

    def get_extra_form_kwargs(self):
        kwargs = super(DerivedPeriodInline, self).get_extra_form_kwargs()
        kwargs['inline_instance'] = self
        return kwargs


class SeasonsPeriodInline(LocalizedInlineFormSetMixin, InlineFormSet):
    model = SeasonIndexPeriod
    extra = 1
    fields = ['from_date'] + ['value_at_hour_%d' % i for i in range(24)]
    formset_class = PeriodFormSet


class TariffForm(forms.ModelForm):
    unit = forms.ChoiceField()

    class Meta:
        model = Index
        fields = ['name', 'collection', 'unit', 'timezone']


class IndexCreateView(CreateWithInlinesView):
    model = Index

    def get_success_url(self):
        return reverse('manage_indexes-listing')

    # Set in subclass:
    role = None
    data_format = None
    utility_type = None

    def get_form(self, form_class):
        form = super(IndexCreateView, self).get_form(form_class)
        assert self.role is not None
        form.instance.role = self.role
        assert self.data_format is not None
        form.instance.data_format = self.data_format
        assert self.utility_type is not None
        form.instance.utility_type = self.utility_type
        return form


class DerivedIndexCreateView(IndexCreateView):
    inlines = [DerivedPeriodInline]
    data_format = Index.DERIVED


class SeasonsIndexCreateView(IndexCreateView):
    inlines = [SeasonsPeriodInline]
    data_format = Index.SEASONS


class TariffCreateViewMixin(object):
    form_class = TariffForm

    # Set in subclass:
    unit_choices = None

    def get_form(self, form_class):
        form = super(TariffCreateViewMixin, self).get_form(form_class)
        assert self.unit_choices is not None
        form.fields['unit'].choices = self.unit_choices
        form.fields['unit'].initial = self.get_initial_unit()
        return form

    def get_initial_unit(self):
        customer_currency_unit = get_customer().currency_unit
        for unit, unit_display in self.unit_choices:
            if customer_currency_unit in unit:
                return unit
        return None


class NontariffCreateViewMixin(object):
    fields = ['name', 'collection', 'timezone']
    template_name = 'manage_indexes/seasons_index_form.html'
    utility_type = utilitytypes.OPTIONAL_METER_CHOICES.unknown

    # Set in sublcass:
    unit = None

    def get_form(self, form_class):
        form = super(NontariffCreateViewMixin, self).get_form(form_class)
        assert self.unit is not None
        form.instance.unit = self.unit
        return form


class DerivedTariffCreateView(TariffCreateViewMixin, DerivedIndexCreateView):
    template_name = 'manage_indexes/derived_tariff_form.html'


class ElectricityTariffMixin(object):
    utility_type = utilitytypes.OPTIONAL_METER_CHOICES.electricity
    role = DataRoleField.ELECTRICITY_TARIFF
    unit_choices = units.ENERGY_TARIFF_CHOICES


class GasTariffMixin(object):
    utility_type = utilitytypes.OPTIONAL_METER_CHOICES.gas
    role = DataRoleField.GAS_TARIFF
    unit_choices = units.VOLUME_TARIFF_CHOICES


class WaterTariffMixin(object):
    utility_type = utilitytypes.OPTIONAL_METER_CHOICES.water
    role = DataRoleField.WATER_TARIFF
    unit_choices = units.VOLUME_TARIFF_CHOICES


class DistrictHeatingTariffMixin(object):
    utility_type = utilitytypes.OPTIONAL_METER_CHOICES.district_heating
    role = DataRoleField.HEAT_TARIFF
    unit_choices = units.ENERGY_TARIFF_CHOICES


class OilTariffMixin(object):
    utility_type = utilitytypes.OPTIONAL_METER_CHOICES.oil
    role = DataRoleField.OIL_TARIFF
    unit_choices = units.VOLUME_TARIFF_CHOICES


class DerivedElectricityTariffCreateView(ElectricityTariffMixin,
                                         DerivedTariffCreateView):
    headline = _('Create New Derived Electricity Tariff')


class DerivedGasTariffCreateView(GasTariffMixin,
                                 DerivedTariffCreateView):
    headline = _('Create New Derived Gas Tariff')


class DerivedWaterTariffCreateView(WaterTariffMixin,
                                   DerivedTariffCreateView):
    headline = _('Create New Derived Water Tariff')


class DerivedDistrictHeatingTariffCreateView(DistrictHeatingTariffMixin,
                                             DerivedTariffCreateView):
    headline = _('Create New Derived District Heating Tariff')


class DerivedOilTariffCreateView(OilTariffMixin,
                                 DerivedTariffCreateView):
    headline = _('Create New Derived Oil Tariff')


class SeasonsTariffCreateView(TariffCreateViewMixin, SeasonsIndexCreateView):
    template_name = 'manage_indexes/seasons_tariff_form.html'


class SeasonsElectricityTariffCreateView(ElectricityTariffMixin,
                                         SeasonsTariffCreateView):
    headline = _('Create New Seasons Electricity Tariff')


class SeasonsGasTariffCreateView(GasTariffMixin,
                                 SeasonsTariffCreateView):
    headline = _('Create New Seasons Gas Tariff')


class SeasonsWaterTariffCreateView(WaterTariffMixin,
                                   SeasonsTariffCreateView):
    headline = _('Create New Seasons Water Tariff')


class SeasonsDistrictHeatingTariffCreateView(DistrictHeatingTariffMixin,
                                             SeasonsTariffCreateView):
    headline = _('Create New Seasons District Heating Tariff')


class SeasonsOilTariffCreateView(OilTariffMixin,
                                 SeasonsTariffCreateView):
    headline = _('Create New Seasons Oil Tariff')


class SeasonsEmployeesIndexCreateView(NontariffCreateViewMixin,
                                      SeasonsIndexCreateView):
    headline = _('Create New Seasons Employees Index')
    role = DataRoleField.EMPLOYEES
    unit = 'person'


class SeasonsAreaIndexCreateView(NontariffCreateViewMixin,
                                 SeasonsIndexCreateView):
    headline = _('Create New Seasons Area Index')
    role = DataRoleField.AREA
    unit = 'meter^2'


class IndexUpdateView(UpdateWithInlinesView):
    fields = ['name', 'collection']
    model = Index

    def get_success_url(self):
        return reverse('manage_indexes-listing')

    @property
    def utility_type(self):
        return self.object.utility_type

    @property
    def role(self):
        return self.object.role


class DerivedIndexUpdateView(IndexUpdateView):
    inlines = [DerivedPeriodInline]
    template_name = 'manage_indexes/derived_index_form.html'

    @property
    def headline(self):
        return _('Update Derived {index_role}').format(
            index_role=self.object.get_role_display())


class SeasonsIndexUpdateView(IndexUpdateView):
    inlines = [SeasonsPeriodInline]
    template_name = 'manage_indexes/seasons_index_form.html'

    @property
    def headline(self):
        return _('Update Seasons {index_role}').format(
            index_role=self.object.get_role_display())


@auth_or_error
@render_to("manage_indexes/indexes_display.html")
def display(request, index_id):
    """
    The view function for listing indexes visible to the current user.
    """
    return {"index_id": index_id}


@require_http_methods(["POST"])
@customer_admin_or_error
def delete(request):
    pk = request.POST.get('pk', None)
    customer = request.customer
    instance = get_object_or_404(Index, pk=pk)
    if instance.customer != customer or not instance.is_deletable():
        return HttpResponseForbidden()
    instance.delete()
    messages.success(request, _('The index has been deleted'))
    return redirect("manage_indexes-listing")
