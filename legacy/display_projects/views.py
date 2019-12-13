# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from decimal import Decimal

from django import forms
from django.core.urlresolvers import reverse
from django.views import generic
from django.views.generic.base import TemplateView
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect

import pytz
from braces.views import LoginRequiredMixin
from extra_views import UpdateWithInlinesView
from extra_views import CreateWithInlinesView
from extra_views import InlineFormSet

from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.energy_use_reports.views import flotr2_to_gnuplot

from legacy.projects.forms import AnnualSavingsPotentialReportGenerationForm  # noqa
from legacy.projects.models import AdditionalSaving
from legacy.projects.models import BenchmarkProject
from legacy.projects.models import Cost
from gridplatform.reports.pdf import generate_pdf
from gridplatform.reports.views import FinalizeReportView
from gridplatform.reports.views import ReportInfo
from gridplatform.reports.views import StartReportView
from gridplatform.trackuser import get_customer
from gridplatform.utils import utilitytypes

from .tasks import ProjectReportTask


class ProjectForm(forms.ModelForm):
    class Meta:
        model = BenchmarkProject
        fields = (
            'name', 'background', 'expectations', 'actions', 'result',
            'comments', 'runtime', 'estimated_yearly_consumption_costs_before',
            'estimated_yearly_consumption_before',
            'estimated_co2_emissions_before',
            'expected_savings_in_yearly_total_costs',
            'expected_savings_in_yearly_consumption_after',
            'expected_reduction_in_yearly_co2_emissions',
            'include_measured_costs', 'subsidy',
            'baseline_from_timestamp', 'baseline_to_timestamp',
            'result_from_timestamp', 'result_to_timestamp',
            'baseline_measurement_points',
            'result_measurement_points')
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        utility_type = kwargs.pop('utility_type', None)
        super(ProjectForm, self).__init__(*args, **kwargs)
        if self.instance.utility_type is None:
            assert utility_type is not None
            self.instance.utility_type = utility_type

        for field in [
                "estimated_yearly_consumption_costs_before",
                "estimated_yearly_consumption_before",
                "estimated_co2_emissions_before",
                "expected_savings_in_yearly_total_costs",
                "expected_savings_in_yearly_consumption_after",
                "expected_reduction_in_yearly_co2_emissions",
                'baseline_from_timestamp', 'baseline_to_timestamp',
                'result_from_timestamp', 'result_to_timestamp']:
            if field in self.fields:
                self.fields[field].localize = True
                self.fields[field].widget.is_localized = True

        measurement_points_qs = ConsumptionMeasurementPoint.objects.\
            subclass_only().filter(
                utility_type=self.instance.utility_type)

        self.fields[
            'baseline_measurement_points'].queryset = measurement_points_qs
        self.fields[
            'result_measurement_points'].queryset = measurement_points_qs


class WaterProjectForm(ProjectForm):
    class Meta(ProjectForm.Meta):
        fields = (
            'name', 'background', 'expectations', 'actions', 'result',
            'comments', 'runtime', 'estimated_yearly_consumption_costs_before',
            'estimated_yearly_consumption_before',
            'expected_savings_in_yearly_total_costs',
            'expected_savings_in_yearly_consumption_after',
            'include_measured_costs', 'subsidy',
            'baseline_from_timestamp', 'baseline_to_timestamp',
            'result_from_timestamp', 'result_to_timestamp',
            'baseline_measurement_points',
            'result_measurement_points')


class BenchmarkProjectOpenClosedMixin(object):
    def get_context_data(self, **kwargs):
        now = datetime.datetime.now(pytz.utc)
        context = {
            'open': BenchmarkProject.active(now),
            'closed': BenchmarkProject.done(now),
        }
        context.update(kwargs)
        return super(BenchmarkProjectOpenClosedMixin, self).get_context_data(
            **context)


class BenchmarkProjectIndexView(
        LoginRequiredMixin, BenchmarkProjectOpenClosedMixin,
        generic.TemplateView):
    template_name = 'display_projects/index.html'


class BenchmarkProjectDetailView(
        LoginRequiredMixin, BenchmarkProjectOpenClosedMixin,
        generic.DetailView):
    template_name = 'display_projects/project_details.html'
    model = BenchmarkProject


class AdditionalSavingsInline(InlineFormSet):
    model = AdditionalSaving
    extra = 1


class WaterAdditionalSavingsInline(AdditionalSavingsInline):
    fields = ('description', 'before_energy',
              'after_energy', 'before_cost', 'after_cost')


class CostInline(InlineFormSet):
    model = Cost
    extra = 1


class BenchmarkProjectUpdateView(
        LoginRequiredMixin, BenchmarkProjectOpenClosedMixin,
        UpdateWithInlinesView):
    template_name = 'display_projects/project_form.html'
    model = BenchmarkProject
    form_class = ProjectForm
    inlines = [AdditionalSavingsInline, CostInline]

    def get_context_data(self, **kwargs):
        inlines = kwargs['inlines']
        additional_saving, cost = inlines
        context = {
            'additional_saving': additional_saving,
            'cost': cost,
            'currency': get_customer().get_currency_unit_display(),
        }
        context.update(kwargs)
        return super(BenchmarkProjectUpdateView, self).get_context_data(
            **context)

    def get_success_url(self):
        return reverse('display_projects-index')


class BenchmarkProjectCreateView(
        LoginRequiredMixin, BenchmarkProjectOpenClosedMixin,
        CreateWithInlinesView):
    template_name = 'display_projects/project_form.html'
    model = BenchmarkProject
    form_class = ProjectForm
    inlines = [AdditionalSavingsInline, CostInline]

    def get_form_kwargs(self):
        utility_type = self.kwargs['utility_type']
        kwargs = super(BenchmarkProjectCreateView, self).get_form_kwargs()
        kwargs['utility_type'] = getattr(
            utilitytypes.METER_CHOICES, utility_type)
        return kwargs

    def get_context_data(self, **kwargs):
        inlines = kwargs['inlines']
        additional_saving, cost = inlines
        context = {
            'additional_saving': additional_saving,
            'cost': cost,
            'currency': get_customer().get_currency_unit_display(),
        }
        context.update(kwargs)
        return super(BenchmarkProjectCreateView, self).get_context_data(
            **context)

    def get_success_url(self):
        return reverse('display_projects-index')


class WaterBenchmarkProjectUpdateView(BenchmarkProjectUpdateView):
    model = BenchmarkProject
    form_class = WaterProjectForm
    inlines = [WaterAdditionalSavingsInline, CostInline]

    def get_context_data(self, **kwargs):
        context = {
            'is_water_project': True,
        }
        context.update(kwargs)
        return super(WaterBenchmarkProjectUpdateView, self).get_context_data(
            **context)


class WaterBenchmarkProjectCreateView(BenchmarkProjectCreateView):
    template_name = 'display_projects/project_form.html'
    model = BenchmarkProject
    form_class = WaterProjectForm
    inlines = [WaterAdditionalSavingsInline, CostInline]

    def get_context_data(self, **kwargs):
        context = {
            'is_water_project': True,
        }
        context.update(kwargs)
        return super(WaterBenchmarkProjectCreateView, self).get_context_data(
            **context)


class BenchmarkProjectDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = BenchmarkProject

    def get_success_url(self):
        return reverse('display_projects-index')


class ProjectReportForm(forms.Form):
    project = forms.IntegerField()


def benchmarkproject_update(request, pk):
    project = get_object_or_404(
        BenchmarkProject, id=pk)
    if project.utility_type == utilitytypes.METER_CHOICES.water:
        return redirect('display_projects-update_water', pk=pk)
    else:
        return redirect('display_projects-update_normal', pk=pk)


class StartProjectReportView(StartReportView):
    form_class = ProjectReportForm
    task = ProjectReportTask

    def get_task_data(self, form):
        data = form.cleaned_data
        return {
            'project': data['project'],
        }


class FinalizeProjectReportView(FinalizeReportView):
    def generate_report(self, data, timestamp):
        project = BenchmarkProject.objects.get(id=data['project_id'])
        file_title = '{}.pdf'.format(project.name_plain.encode(
            'ascii', 'ignore'))
        template = 'display_projects/report.tex'
        additional_savings = list(project.additionalsaving_set.all())
        additional_savings_sum = {
            'before_energy': sum(
                [a.before_energy or 0 for a in additional_savings],
                Decimal(0)),
            'after_energy': sum(
                [a.after_energy or 0 for a in additional_savings], Decimal(0)),
            'diff_energy': sum(
                [a.diff_energy() for a in additional_savings], Decimal(0)),
            'before_cost': sum(
                [a.before_cost or 0 for a in additional_savings], Decimal(0)),
            'after_cost': sum(
                [a.after_cost or 0 for a in additional_savings], Decimal(0)),
            'diff_cost': sum(
                [a.diff_cost() for a in additional_savings], Decimal(0)),
            'before_co2': sum(
                [a.before_co2 or 0 for a in additional_savings], Decimal(0)),
            'after_co2': sum(
                [a.after_co2 or 0 for a in additional_savings], Decimal(0)),
            'diff_co2': sum(
                [a.diff_co2() for a in additional_savings], Decimal(0)),
        }
        project_costs = list(project.cost_set.all())
        data.update(
            {
                'name': project.name_plain,
                'background': project.background_plain,
                'expectations': project.expectations_plain,
                'actions': project.actions_plain,
                'result': project.result_plain,
                'comments': project.comments_plain,
                'months': project.runtime,
                'additional_savings': additional_savings,
                'additional_savings_sum': additional_savings_sum,
                'project_costs': project_costs,
                'customer_name': unicode(project.customer),
                'project_runtime': project.runtime,
                'include_measured_costs': project.include_measured_costs,
                'activity_duration': {
                    'from_timestamp': project.from_timestamp,
                    'to_timestamp': project.to_timestamp,
                },
                'stage_1_start': project.baseline_from_timestamp,
                'stage_1_end': project.baseline_to_timestamp,
                'stage_1_tariff_domain_warning': (
                    project.baseline_stage.tariff_domain_warning(
                        data['baseline_tariff_domain_warning_measurement_point_ids'])),  # noqa
                'stage_2_start': project.result_from_timestamp,
                'stage_2_end': project.result_to_timestamp,
                'stage_2_tariff_domain_warning': (
                    project.result_stage.tariff_domain_warning(
                        data['result_tariff_domain_warning_measurement_point_ids'])),  # noqa
                'project': project,
            })

        has_rate_graphs = False
        for mp_dict in data['measurement_points']:
            mp_dict['instance'] = ConsumptionMeasurementPoint.objects.\
                subclass_only().get(id=mp_dict['id']).subclass_instance
            if mp_dict['graph_data']:
                has_rate_graphs = True

        data.update({
            'has_rate_graphs': has_rate_graphs,
        })

        content = generate_pdf(
            template, data, project.name_plain, 'project',
            project.customer,
            gnuplots=[
                flotr2_to_gnuplot(
                    mp['graph_data'],
                    'rate-graph-%d.tex' % mp['id'],
                    terminal='epslatex color solid size 26cm,11.5cm') for
                mp in data['measurement_points'] if mp['graph_data']] +
            [
                flotr2_to_gnuplot(
                    mp['consumption_graph_data'],
                    'consumption-graph-%d.tex' % mp['id'],
                    terminal='epslatex color solid size 26cm,11.5cm',
                    sample_resolution=project.get_sample_resolution()) for
                mp in data['measurement_points']])

        return ReportInfo(file_title, 'application/pdf', content)


class AnnualSavingsPotentialReportGenerationFormView(TemplateView):
    template_name = 'display_projects/annual_savings_potential_form.html'

    def get_context_data(self, **kwargs):
        context = super(
            AnnualSavingsPotentialReportGenerationFormView, self).\
            get_context_data(**kwargs)
        context['form'] = AnnualSavingsPotentialReportGenerationForm()
        return context
