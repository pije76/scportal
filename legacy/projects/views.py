# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from gridplatform.reports.views import StartReportView
from gridplatform.reports.views import FinalizeReportView
from gridplatform.reports.views import ReportInfo
from gridplatform.reports.pdf import generate_pdf
from gridplatform.trackuser import get_customer

from .forms import AnnualSavingsPotentialReportGenerationForm
from .tasks import AnnualSavingsPotentialReportTask
from .models import BenchmarkProject


class StartAnnualSavingsPotentialReportView(StartReportView):
    task = AnnualSavingsPotentialReportTask
    form_class = AnnualSavingsPotentialReportGenerationForm

    def get_task_data(self, form):
        result = {
            "projects": dict()
        }

        for project_id in form.cleaned_data['projects'].values_list(
                'id', flat=True):
            result['projects'][project_id] = dict()

        return result


class FinalizeAnnualSavingsPotentialReportView(FinalizeReportView):
    def generate_report(self, data, timestamp):
        for project in BenchmarkProject.objects.filter(
                id__in=data['projects'].keys()):
            data['projects'][project.id]['name'] = unicode(project)
            data['projects'][project.id]['get_consumption_unit_display'] = \
                project.get_preferred_consumption_unit_converter().\
                get_display_unit()

        data['currency'] = get_customer().get_currency_unit_display()

        return ReportInfo(
            'annual_savings_potential.pdf',
            'application/pdf',
            generate_pdf(
                template='projects/annual_savings_potential_report.tex',
                data=data,
                title=_('Annual Savings Potential'),
                report_type='annual_savings_potential',
                customer=get_customer()))
