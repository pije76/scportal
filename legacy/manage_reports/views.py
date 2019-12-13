# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import base64
import contextlib
import datetime
import operator
from cStringIO import StringIO
import gzip

from django import forms
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.forms.models import BaseInlineFormSet
from django.forms.models import inlineformset_factory
from django.forms.widgets import CheckboxSelectMultiple
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http.response import HttpResponseRedirectBase
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods

import pytz
from celery.result import AsyncResult

from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.energy_use_reports.forms import GenerateEnergyUseReportForm
from legacy.energy_use_reports.models import EnergyUseArea
from legacy.energy_use_reports.models import EnergyUseReport
from legacy.enpi_reports.models import ENPIReport
from legacy.enpi_reports.forms import GenerateENPIReportForm
from gridplatform.utils import utilitytypes
from gridplatform.reports.consumption import consumption_csv
from gridplatform.reports.consumption import consumption_pdf
from gridplatform.reports.consumption import extend_consumption_data
from gridplatform.reports.models import Report
from gridplatform.reports.views import FinalizeReportView
from gridplatform.reports.views import ReportInfo
from gridplatform.reports.views import StartReportView
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_user
from gridplatform.users.decorators import auth_or_error
from gridplatform.users.decorators import auth_or_redirect
from gridplatform.users.decorators import customer_admin_or_admin_or_error
from gridplatform.utils import condense
from gridplatform.utils.iter_ext import flatten
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.views import json_response
from gridplatform.utils.views import render_to
from legacy.display_measurementpoints.views import PeriodForm
from gridplatform.utils.formsets import SurvivingFormsModelFormSetMixin
from .tasks import collect_consumption_data
from .tasks import graphdata_download_task


class HttpResponseTemporaryRedirect(HttpResponseRedirectBase):
    status_code = 307


class GenerateReportForm(forms.Form):
    from_date = forms.DateField()
    to_date = forms.DateField()

    collections = forms.ModelMultipleChoiceField(
        # choices=[],
        queryset=Collection.objects.none(),
        required=True,
        widget=CheckboxSelectMultiple)

    include_cost = forms.BooleanField(initial=False, required=False)

    VALID_ROLES = [
        Collection.CONSUMPTION_GROUP,
        Collection.CONSUMPTION_MEASUREMENT_POINT,
        Collection.GROUP,
    ]

    def __init__(self, *args, **kwargs):
        super(GenerateReportForm, self).__init__(*args, **kwargs)
        self.fields['collections'].queryset = Collection.objects.filter(
            role__in=self.VALID_ROLES, hidden_on_reports_page=False)

    def get_collections(self):
        """
        Returns a list of all the collections for a customer or the ones
        that the current user is restricted to.
        """
        root_groups = get_user().userprofile.collections.all()
        if not root_groups:
            root_groups = Collection.objects.root_nodes().filter(
                customer=get_customer())
        collection_root_list = [
            collection_root.get_descendants(include_self=True)
            .filter(role__in=self.VALID_ROLES,
                    hidden_on_reports_page=False)
            for collection_root in root_groups]
        return collection_root_list

    def clean(self):
        cleaned_data = super(GenerateReportForm, self).clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')

        if isinstance(from_date, datetime.date) and \
                isinstance(to_date, datetime.date) and \
                from_date > to_date:
            raise forms.ValidationError(
                _('From time should be before to time'))
        if not cleaned_data.get('collections'):
            raise forms.ValidationError(
                _('Select at least one measurement point'))

        return cleaned_data


@auth_or_error
@json_response
@require_POST
def request_consumption_report(request):
    """
    Start the consumption report background task.
    """
    customer = get_customer()
    tz = customer.timezone
    form = GenerateReportForm(request.POST)
    if form.is_valid():
        # start celery task, return ID
        collections = form.cleaned_data['collections']
        mp_ids = [collection.id for collection in collections]
        include_cost = form.cleaned_data['include_cost']
        from_date = form.cleaned_data['from_date']
        to_date = form.cleaned_data['to_date']
        from_timestamp = tz.localize(
            datetime.datetime.combine(from_date, datetime.time()))
        to_timestamp = tz.localize(
            datetime.datetime.combine(
                to_date + datetime.timedelta(days=1), datetime.time()))
        async = collect_consumption_data.delay(
            mp_ids, from_timestamp, to_timestamp, from_date, to_date,
            include_cost)
        return {
            'task_id': async.id,
            'status': async.status,
        }
    else:
        return {
            'form_errors': form.errors,
        }


@auth_or_error
@json_response
@require_POST
def finalize_consumption_report(request):
    task_id = request.POST['task_id']
    async = AsyncResult(task_id)
    assert async.successful()
    collected = async.result
    data = extend_consumption_data(collected)
    errors = collected['errors']
    from_date = collected['from_date']
    to_date = collected['to_date']
    include_degree_days_corrected = collected['include_degree_days_corrected']
    include_cost = collected['include_cost']
    now = datetime.datetime.now(pytz.utc)
    try:
        # we extract the customer from the first Collection
        customer = Collection.objects.get(id=collected['mp_ids'][0]).customer
    except:
        customer = None

    pdf = consumption_pdf(
        from_date, to_date, data, include_degree_days_corrected, include_cost,
        customer, errors=errors)
    csv = consumption_csv(
        from_date, to_date, data, include_degree_days_corrected, include_cost)
    pdfreport = Report(
        customer=get_customer(),
        title_plain=unicode(_('Consumption report')),
        generation_time=now,
        data_format=Report.PDF,
        data_plain=base64.encodestring(pdf),
        size=len(pdf))
    pdfreport.save()
    csvreport = Report(
        customer=get_customer(),
        title_plain=unicode(_('Consumption report')),
        generation_time=now,
        data_format=Report.CSV,
        data_plain=base64.encodestring(csv),
        size=len(csv))
    csvreport.save()
    return {
        'pdf': {
            'id': pdfreport.id,
            'title': pdfreport.title_plain,
            'size': pdfreport.size,
            'url': reverse(
                'manage_reports-serve_pdf',
                kwargs={'pdf_id': pdfreport.id, 'title': pdfreport.title_plain}
            ),
        },
        'csv': {
            'id': csvreport.id,
            'title': csvreport.title_plain,
            'size': csvreport.size,
            'url': reverse(
                'manage_reports-serve_csv',
                kwargs={'csv_id': csvreport.id, 'title': csvreport.title_plain}
            )
        }
    }


@auth_or_error
def serve_pdf(request, pdf_id, title=None):
    report = get_object_or_404(Report, id=pdf_id, data_format=Report.PDF)
    return HttpResponse(base64.decodestring(report.data_plain),
                        content_type='application/pdf')


@auth_or_error
def serve_csv(report, csv_id, title=None):
    report = get_object_or_404(Report, id=csv_id, data_format=Report.CSV)
    return HttpResponse(base64.decodestring(report.data_plain),
                        content_type='text/csv')


@auth_or_redirect
@render_to('manage_reports/index.html')
def index(request):
    customer = get_customer()
    month = RelativeTimeDelta(months=1)

    now = customer.now()
    from_date = (
        condense.floor(now, month, customer.timezone) -
        month).date()
    to_date = condense.floor(
        now, month, customer.timezone).date() - \
        datetime.timedelta(days=1)

    previous_from_date = (
        condense.floor(now, month, customer.timezone) -
        2 * month).date()
    previous_to_date = from_date - datetime.timedelta(days=1)

    energy_use_reports = EnergyUseReport.objects.filter(
        customer=customer).prefetch_related(
        'energyusearea_set', 'main_measurement_points')

    user_groups = get_user().userprofile.collections.all()

    if user_groups:
        mp_ids = [group.get_descendants(include_self=True)
                  .filter(role__in=Collection.DATA_POINTS)
                  .exclude(hidden_on_details_page=True)
                  .values_list('id', flat=True)
                  for group in user_groups]

        mp_ids_flattened = set(flatten(mp_ids))

        energy_use_reports = [report for report in energy_use_reports
                              if set(report.get_all_measurementpoint_ids())
                              .issubset(mp_ids_flattened)]
    energy_use_reports = sorted(
        energy_use_reports, key=operator.attrgetter('title_plain'))

    for r in energy_use_reports:
        r.form = GenerateEnergyUseReportForm(
            initial={
                'energy_use_report': r.id,
                'from_date': from_date,
                'to_date': to_date,
                'previous_period_from_date': previous_from_date,
                'previous_period_to_date': previous_to_date},
            auto_id=False)

    enpi_reports = ENPIReport.objects.filter(
        customer=customer).prefetch_related(
        'enpiusearea_set')
    for r in enpi_reports:
        r.form = GenerateENPIReportForm(
            initial={
                'enpi_report': r.id,
                'from_date': from_date,
                'to_date': to_date},
            auto_id=False)
    return {
        'reports': list(energy_use_reports) + list(enpi_reports),
        'energy_driver_choices': ENPIReport.get_energy_driver_choices(),
    }


@auth_or_redirect
@render_to('manage_reports/generate_report.html')
def create_consumption_report(request):
    form = GenerateReportForm()
    return {
        'form': form,
        'collections': form.get_collections(),
        'selected_collections': form['collections'].value,
    }


class EnergyUseReportForm(forms.ModelForm):
    class Meta:
        model = EnergyUseReport
        fields = ('title', 'currency_unit', 'main_measurement_points')
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        """
        @keyword utility_type: If instance is not given, this keyword argument
        must be given.  It should be one of the integer values defined in
        L{utilitytypes.METER_CHOICES}.
        """
        utility_type = kwargs.pop('utility_type', None)
        super(EnergyUseReportForm, self).__init__(*args, **kwargs)
        if utility_type is not None and self.instance.utility_type is None:
            self.instance.utility_type = utility_type

        self.fields['currency_unit'].initial = get_customer().currency_unit
        self.fields['main_measurement_points'].queryset = \
            ConsumptionMeasurementPoint.objects.subclass_only().filter(
                customer=get_customer(),
                utility_type=self.instance.utility_type,
                hidden_on_reports_page=False).decrypting_order_by('name')


class EnergyUseAreaForm(forms.ModelForm):
    measurement_points = forms.ModelMultipleChoiceField(
        queryset=ConsumptionMeasurementPoint.objects.none())

    class Meta:
        model = EnergyUseArea
        fields = ('name', 'measurement_points')
        localized_fields = '__all__'


def make_base_energy_areay_formset(utility_type):
    class BaseEnergyUseAreaFormSet(SurvivingFormsModelFormSetMixin,
                                   BaseInlineFormSet):
        def __init__(self, *args, **kwargs):
            self.measurement_point_queryset = ConsumptionMeasurementPoint.\
                objects.subclass_only().filter(
                    customer=get_customer(),
                    utility_type=utility_type,
                    hidden_on_reports_page=False).decrypting_order_by('name')
            super(BaseEnergyUseAreaFormSet, self).__init__(*args, **kwargs)

        def add_fields(self, form, index):
            """
            Set sorted options and queryset on all forms, also any
            C{empty_form} created.
            """
            super(BaseEnergyUseAreaFormSet, self).add_fields(form, index)
            form.fields['measurement_points'].queryset = \
                self.measurement_point_queryset

        def clean(self):
            super(BaseEnergyUseAreaFormSet, self).clean()
            if any(self.errors):
                return

            if not self.surviving_forms():
                raise forms.ValidationError(
                    _('Include at least one area of energy use'))

            mps = []
            faulty_stuff = []
            for form in self.forms:
                if form.cleaned_data:
                    for mp in form.cleaned_data['measurement_points']:
                        if mp in mps and unicode(mp) not in faulty_stuff:
                            faulty_stuff.append(unicode(mp))
                        mps.append(mp)
            if faulty_stuff:
                raise forms.ValidationError(
                    _('The following measurement points can '
                      'only be included once: {measurement_points}').
                    format(measurement_points=', '.join(faulty_stuff)))
    return BaseEnergyUseAreaFormSet


@customer_admin_or_admin_or_error
@render_to('manage_reports/energy_use_report_form.html')
def create_energy_use_report(request, utility_type):
    utility_type_key = getattr(
        utilitytypes.OPTIONAL_METER_CHOICES, utility_type)
    report_form = EnergyUseReportForm(
        request.POST or None, utility_type=utility_type_key)
    AreaFormset = inlineformset_factory(
        EnergyUseReport, EnergyUseArea, form=EnergyUseAreaForm,
        formset=make_base_energy_areay_formset(utility_type_key), extra=1)
    area_formset = AreaFormset(request.POST or None)

    if all((report_form.is_valid(), area_formset.is_valid())):
        report_form.instance.utility_type = utility_type_key
        report_instance = report_form.save()
        area_formset = AreaFormset(request.POST, instance=report_instance)
        area_formset.is_valid()
        area_formset.save()
        return redirect('manage_reports-index')
    return {
        'form': report_form,
        'area_formset': area_formset,
    }


@customer_admin_or_admin_or_error
@render_to('manage_reports/energy_use_report_form.html')
def update_energy_use_report(request, pk):
    instance = get_object_or_404(
        EnergyUseReport, customer=get_customer(), pk=pk)
    report_form = EnergyUseReportForm(request.POST or None, instance=instance)

    AreaFormset = inlineformset_factory(
        EnergyUseReport, EnergyUseArea, form=EnergyUseAreaForm,
        formset=make_base_energy_areay_formset(instance.utility_type), extra=1)
    area_formset = AreaFormset(request.POST or None, instance=instance)

    if request.method == 'POST':
        if all((report_form.is_valid(), area_formset.is_valid())):
            report_instance = report_form.save()
            area_formset = AreaFormset(request.POST, instance=report_instance)
            area_formset.is_valid()
            area_formset.save()
            return redirect('manage_reports-index')
    return {
        'form': report_form,
        'area_formset': area_formset,
    }


@require_http_methods(["POST"])
@auth_or_redirect
def delete(request):
    """
    This method is called from legacy.website.synchroneousDelete.
    The synchroneousDelete function is handling the redirection
    to the appropirate index page.
    """
    pk = request.POST.get('pk', None)
    customer = get_customer()
    instance = get_object_or_404(EnergyUseReport, pk=pk)
    if instance.customer != customer:
        return HttpResponseForbidden()
    instance.delete()
    messages.success(request, _('The report has been deleted'))
    return HttpResponse()


@require_http_methods(["POST"])
@auth_or_redirect
def enpi_delete(request):
    """
    This method is called from legacy.website.synchroneousDelete.
    The synchroneousDelete function is handling the redirection
    to the appropirate index page.
    """
    pk = request.POST.get('pk', None)
    customer = get_customer()
    print 'here'
    instance = get_object_or_404(ENPIReport, pk=pk)
    if instance.customer != customer:
        return HttpResponseForbidden()
    instance.delete()
    messages.success(request, _('The report has been deleted'))
    return HttpResponse()


class GraphdataDownloadForm(PeriodForm):
    graph = forms.IntegerField()


class StartGraphdataDownloadView(StartReportView):
    form_class = GraphdataDownloadForm
    task = graphdata_download_task

    def get_task_data(self, form):
        from_timestamp, to_timestamp = form.get_period()
        return {
            'graph': form.cleaned_data['graph'],
            'from_timestamp': from_timestamp,
            'to_timestamp': to_timestamp,
        }


class FinalizeGraphdataDownloadView(FinalizeReportView):
    def generate_report(self, data, timestamp):
        with contextlib.closing(StringIO(data['gzippedfile'])) as f:
            csvfilename = data['csvfilename']
            gz = gzip.GzipFile(mode='rb', fileobj=f)
            csv = gz.read()
            gz.close()
            return ReportInfo(csvfilename, 'text/csv', csv)
