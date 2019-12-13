# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from django import forms
from django.core.urlresolvers import reverse

from gridplatform.consumptions.models import Consumption
from gridplatform.consumptions.tasks import consumptions_weekly_utility_task, consumptions_weekly_time_task
from gridplatform.utils.forms import YearWeekPeriodForm
from gridplatform.utils.preferredunits import PhysicalUnitConverter
from gridplatform.utils.utilitytypes import ENERGY_UTILITY_TYPE_TO_DISPLAY_UNIT_MAP
from gridplatform.utils.views import CustomerInKwargsMixin, FinalizeTaskView, JsonResponse
from gridplatform.utils.views import StartTaskView
from gridplatform.utils import generic_views, PhysicalQuantity
from gridplatform.utils.breadcrumbs import Breadcrumb
from gridplatform.utils.breadcrumbs import Breadcrumbs
from gridplatform.utils.views import ChooseCustomerBase
from gridplatform.utils.views import CustomerListMixin
from gridplatform.utils.views import CustomerViewBase
from gridplatform.utils.views import HomeViewBase

from energymanager.energy_projects.models import EnergyProject, ENERGY_PROJECT_PHASES


class HomeView(HomeViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'project_site:project-list',
            kwargs={'customer_id': customer_id})

    def get_choose_customer_url(self):
        return reverse(
            'project_site:choose-customer')


class ChooseCustomer(ChooseCustomerBase):
    template_name = 'project_site/choose_customer.html'


class CustomerView(CustomerViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'project_site:project-list',
            kwargs={'customer_id': customer_id})


class EnergyProjectList(CustomerListMixin, generic_views.TemplateView):
    template_name = 'project_site/project_list.html'

    @staticmethod
    def build_breadcrumbs(customer_id):
        return Breadcrumbs() + Breadcrumb(
            _('Projects'),
            reverse(
                'project_site:project-list',
                kwargs={'customer_id': customer_id}))

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id)


class EnergyProjectListContentView(
        CustomerListMixin,
        generic_views.ListView):
    search_fields = ['name_plain', ]
    sort_fields = ['name_plain', ]
    model = EnergyProject
    paginate_by = 100
    template_name = 'project_site/_project_list_content.html'


class EnergyProjectForm(forms.ModelForm):

    class Meta:
        model = EnergyProject
        fields = (
            'name', 'baseline_from_date', 'baseline_to_date',
            'datasource', 'time_datasource',
            'result_from_date', 'result_to_date'
        )


class EnergyProjectCreateView(CustomerListMixin,
                                generic_views.CreateView):
    model = EnergyProject
    template_name = 'project_site/project_form.html'
    form_class = EnergyProjectForm

    def form_valid(self, form):
        form.instance.customer_id = self._customer.id
        result = super(EnergyProjectCreateView, self).form_valid(form)
        assert self.object.id
        self._customer.energyproject_set.add(self.object)
        return result

    def get_success_url(self):
        return reverse('project_site:project-list',
                       kwargs={'customer_id':
                               self._customer.id})

    def get_cancel_url(self):
        return self.get_success_url()

    def get_breadcrumbs(self):
        return EnergyProjectList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Create Project'))


class EnergyProjectUpdateView(CustomerListMixin,
                                generic_views.UpdateView):
    model = EnergyProject
    template_name = 'project_site/project_form.html'
    form_class = EnergyProjectForm

    def get_success_url(self):
        return reverse('project_site:project-list',
                       kwargs={'customer_id':
                               self._customer.id})

    def get_cancel_url(self):
        return self.get_success_url()

    def get_delete_url(self):
        return reverse('project_site:project-delete',
                       kwargs={'customer_id':
                               self._customer.id,
                               'pk':
                               self.object.id})

    def get_breadcrumbs(self):
        return EnergyProjectList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(self.object)


class EnergyProjectDeleteView(
        CustomerListMixin, generic_views.DeleteView):
    model = EnergyProject

    def get_success_url(self):
        return reverse('project_site:project-list',
                       kwargs={'customer_id':
                               self._customer.id})


class EnergyProjectDetailView(
        CustomerListMixin, generic_views.DetailView):
    model = EnergyProject
    template_name = \
        'project_site/overview.html'

    def get_breadcrumbs(self):
        return EnergyProjectList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(self.object)

    def get_context_data(self, **kwargs):
        context = super(EnergyProjectDetailView, self).get_context_data(**kwargs)

        context['phase'] = ENERGY_PROJECT_PHASES[self.object.project_phase()]
        context['baseline_sum'] = self.object.total_baseline_consumption()
        context['baseline_time_sum'] = self.object.total_baseline_time_consumption()
        return context


class StartHourConsumptionUtilityBarChartViewBase(
        CustomerInKwargsMixin, StartTaskView):
    task = consumptions_weekly_time_task
    finalize_url_name = 'project_site:utility-bar-chart-finalize'
    form_class = YearWeekPeriodForm

    def get_consumption_id(self, project):
        raise NotImplementedError()

    def get_task_kwargs(self, form):
        project = EnergyProject.objects.get(pk=self.kwargs['project_id'])
        from_timestamp, to_timestamp = project.baseline_timestamps()
        result = {}
        result['consumption_ids'] = [self.get_consumption_id(project)]
        result['from_timestamp'] = from_timestamp
        result['to_timestamp'] = to_timestamp
        return result

    def get_finalize_url(self):
        return reverse(
            self.finalize_url_name,
            kwargs={'customer_id': self._customer.id})


class StartBaselineHourConsumptionUtilityBarChartView(
        StartHourConsumptionUtilityBarChartViewBase):
    task = consumptions_weekly_utility_task

    def get_consumption_id(self, project):
        return project.datasource_id


class StartBaselineDayliConsumptionUtilityBarChartView(
        StartHourConsumptionUtilityBarChartViewBase):

    def get_consumption_id(self, project):
        return project.time_datasource_id


class FinalizeWeekUtilityBarChartView(CustomerInKwargsMixin, FinalizeTaskView):
    def finalize_task(self, task_result):
        consumption = Consumption.objects.get(pk=task_result['consumption_id'])

        unit = 'watt*hour'
        if PhysicalQuantity.compatible_units(
                    consumption.unit, 'second'):
            unit = 'hour'

        self.unit_converter = PhysicalUnitConverter(unit)

        def format_label(timestamp):
            return date_format(
                timestamp.astimezone(self._customer.timezone),
                'SHORT_DATETIME_FORMAT')

        result = {
            'labels': [],
            'week_selected': [],
        }

        selected_sequence = iter(task_result['week_selected'])

        selected = next(selected_sequence, None)

        while selected is not None:

            result['labels'].append(format_label(selected.from_timestamp))
            result['week_selected'].append(
                float(self.unit_converter.extract_value(
                    selected.physical_quantity)))
            selected = next(selected_sequence, None)

        return JsonResponse(result)