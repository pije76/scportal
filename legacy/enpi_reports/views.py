# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404

from extra_views import CreateWithInlinesView
from extra_views import UpdateWithInlinesView

from gridplatform.trackuser import get_customer
from gridplatform.reports.pdf import generate_pdf
from gridplatform.reports.views import FinalizeReportView
from gridplatform.reports.views import ReportInfo
from gridplatform.reports.views import StartReportView
from legacy.energy_use_reports.views import flotr2_to_gnuplot

from .models import ENPIReport
from .forms import ENPIUseAreaFormSet
from .forms import GenerateENPIReportForm
from .tasks import ENPIReportTask


class CreateENPIReportView(CreateWithInlinesView):
    model = ENPIReport
    fields = ['title']
    inlines = [ENPIUseAreaFormSet]

    def get_success_url(self):
        return reverse('manage_reports-index')

    def get_form(self, form_class):
        form = super(CreateENPIReportView, self).get_form(form_class)
        form.instance.energy_driver_unit = self.kwargs['energy_driver_unit']
        return form


class UpdateENPIReportView(UpdateWithInlinesView):
    model = ENPIReport
    fields = ['title']
    inlines = [ENPIUseAreaFormSet]

    def get_success_url(self):
        return reverse('manage_reports-index')

    def get_queryset(self):
        """
        A C{UpdateENPIReportView} implementation of L{UpdateWithInlinesView}
        get_queryset. Adds a filter to the queryset to ensure that the customer
        owns the object.
        """
        queryset = super(UpdateENPIReportView, self).get_queryset()
        return queryset.filter(customer=get_customer())


class FinalizeENPIReportView(FinalizeReportView):
    def generate_report(self, data, timestamp):
        """
        Implementation of L{FinalizeReportView.generate_report}.

        @param data: Output from L{ENPIReportTask} Celery task.

        @param timestamp: The time the report is being build.
        """
        enpi_report = get_object_or_404(
            ENPIReport, id=data['enpi_report'])

        # make the instance available during template rendering.
        data['enpi_report'] = enpi_report

        gnuplots = []
        for use_area_id, use_area_data in data['enpi_use_areas'].items():
            gnuplots.append(
                flotr2_to_gnuplot(
                    use_area_data['graph_data'],
                    use_area_data['graph_name'] + '.tex',
                    sample_resolution=data['sample_resolution']))
            use_area_data['name'] = enpi_report.enpiusearea_set.get(
                id=use_area_id).name_plain

        if 'total_enpi' in data:
            gnuplots.append(
                flotr2_to_gnuplot(
                    data['total_enpi']['graph_data'],
                    data['total_enpi']['graph_name'] + '.tex',
                    sample_resolution=data['sample_resolution']))

        return ReportInfo(
            '{}.pdf'.format(
                enpi_report.title_plain.encode('ascii', 'ignore')),
            'application/pdf',
            generate_pdf(
                template='enpi_reports/enpi_report.tex',
                data=data,
                title=_('Energy Performance Indicator Report'),
                report_type='enpi_report',
                customer=enpi_report.customer,
                gnuplots=gnuplots))


class StartENPIReportView(StartReportView):
    form_class = GenerateENPIReportForm
    task = ENPIReportTask

    def get_task_data(self, form):
        data = form.cleaned_data
        return {
            'enpi_report_id': data['enpi_report'].id,
            'from_date': data['from_date'],
            'to_date': data['to_date'],
            'from_timestamp': data['from_timestamp'],
            'to_timestamp': data['to_timestamp'],
            'sample_resolution': data['sample_resolution'],
        }
