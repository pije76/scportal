# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from django import forms
from django.core.urlresolvers import reverse
from rest_framework.generics import RetrieveAPIView

from energymanager.price_relay_site.tasks import price_relay_tariff_hourly_task
from gridplatform.customers.models import Customer
from gridplatform.tariffs.models import EnergyTariff
from gridplatform.tariffs.tasks import tariff_hourly_task
from gridplatform.utils import generic_views
from gridplatform.utils.breadcrumbs import Breadcrumb
from gridplatform.utils.breadcrumbs import Breadcrumbs
from gridplatform.utils.forms import YearWeekPeriodForm
from gridplatform.utils.preferredunits import PhysicalUnitConverter
from gridplatform.utils.views import ChooseCustomerBase, CustomerInKwargsMixin, StartTaskView, JsonResponse, \
    FinalizeTaskView
from gridplatform.utils.views import CustomerListMixin
from gridplatform.utils.views import CustomerViewBase
from gridplatform.utils.views import HomeViewBase

from .models import PriceRelayProject


class HomeView(HomeViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'price_relay_site:dashboard',
            kwargs={'customer_id': customer_id})

    def get_choose_customer_url(self):
        return reverse(
            'price_relay_site:choose-customer')


class ChooseCustomer(ChooseCustomerBase):
    template_name = 'price_relay_site/choose_customer.html'


class CustomerView(CustomerViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'price_relay_site:dashboard',
            kwargs={'customer_id': customer_id})


class PriceRelayProjectList(CustomerListMixin, generic_views.TemplateView):
    template_name = 'price_relay_site/price_relay_project_list.html'

    @staticmethod
    def build_breadcrumbs(customer_id):
        return Breadcrumbs() + Breadcrumb(
            _('Price Relay Projects'),
            reverse(
                'price_relay_site:price-relay-project-list',
                kwargs={'customer_id': customer_id}))

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id)


class PriceRelayProjectListContentView(
        CustomerListMixin, generic_views.ListView):
    search_fields = ['name_plain', ]
    sort_fields = ['name_plain', ]
    model = PriceRelayProject
    paginate_by = 100
    template_name = 'price_relay_site/_price_relay_project_list_content.html'


class PriceRelayProjectForm(forms.ModelForm):
    class Meta:
        model = PriceRelayProject
        fields = (
            'name', 'look_ahead', 'tariff', 'relay_one_on_at', 'relay_two_on_at', 'relay_tree_on_at',
            'relay_four_on_at', 'relay_five_on_at', 'relay_six_on_at', 'relay_seven_on_at',
            'relay_eight_on_at')


class PriceRelayProjectCreateView(CustomerListMixin,
                                  generic_views.CreateView):
    model = PriceRelayProject
    template_name = 'price_relay_site/price_relay_project_form.html'
    form_class = PriceRelayProjectForm

    def form_valid(self, form):
        form.instance.customer_id = self._customer.id
        result = super(PriceRelayProjectCreateView, self).form_valid(form)
        assert self.object.id
        self._customer.pricerelayproject_set.add(self.object)
        return result

    def get_success_url(self):
        return reverse('price_relay_site:price-relay-project-list',
                       kwargs={'customer_id':
                               self._customer.id})

    def get_cancel_url(self):
        return self.get_success_url()

    def get_breadcrumbs(self):
        return PriceRelayProjectList.build_breadcrumbs(self._customer.id) + \
               Breadcrumb(_('Create LED Light Project'))


class PriceRelayProjectUpdateView(CustomerListMixin,
                                  generic_views.UpdateView):
    model = PriceRelayProject
    template_name = 'price_relay_site/price_relay_project_form.html'
    form_class = PriceRelayProjectForm

    def get_success_url(self):
        return reverse('price_relay_site:price-relay-project-list',
                       kwargs={'customer_id':
                               self._customer.id})

    def get_cancel_url(self):
        return self.get_success_url()

    def get_breadcrumbs(self):
        return PriceRelayProjectList.build_breadcrumbs(self._customer.id) + \
               Breadcrumb(self.object)


class PriceRelayProjectDashboardCustomerDetailView(
        CustomerListMixin, generic_views.DetailView):
    model = Customer
    template_name = \
        'price_relay_site/dashboard.html'

    def get_breadcrumbs(self):
        return (
            (_('Price Relay Dashboard'), ''),
        )

    def get_object(self, queryset=None):
        projects = self.model.objects.get(pk=self.kwargs['customer_id']).pricerelayproject_set.all()

        if len(projects) > 0:
            return projects[0]

        return None

    def get_context_data(self, **kwargs):
        context = super(
            PriceRelayProjectDashboardCustomerDetailView, self).get_context_data(**kwargs)

        return context


class StartTariffHourlyLineChartView(
        CustomerInKwargsMixin, StartTaskView):
    task = price_relay_tariff_hourly_task
    finalize_url_name = 'price_relay_site:forecast-chart-finalize'
    form_class = YearWeekPeriodForm

    def get_task_kwargs(self, form):
        from_timestamp = datetime.datetime.now().replace(tzinfo=self._customer.timezone) - datetime.timedelta(hours=3)
        to_timestamp = from_timestamp + datetime.timedelta(hours=24)

        project = PriceRelayProject.objects.get(pk=self.kwargs['project_id'])


        result = {}
        result['tariff_id'] = project.tariff_id
        result['project_id'] = project.id
        result['from_timestamp'] = from_timestamp
        result['to_timestamp'] = to_timestamp
        return result

    def get_finalize_url(self):
        return reverse(
            self.finalize_url_name,
            kwargs={'customer_id': self._customer.id})


class FinalizeTariffHourlyLineChartView(CustomerInKwargsMixin, FinalizeTaskView):
    def finalize_task(self, task_result):
        tariff = EnergyTariff.objects.get(pk=task_result['tariff_id'])

        self.unit_converter = PhysicalUnitConverter(tariff.unit)

        def format_label(timestamp):
            return timestamp.astimezone(self._customer.timezone).isoformat()

        result = {
            'labels': [],
            'data': [],
        }

        selected_sequence = iter(task_result['data'])

        selected = next(selected_sequence, None)

        while selected is not None:

            result['labels'].append(format_label(selected.from_timestamp))
            result['labels'].append(format_label(selected.to_timestamp))
            result['data'].append(
                float(self.unit_converter.extract_value(
                    selected.physical_quantity)))
            result['data'].append(
                float(self.unit_converter.extract_value(
                    selected.physical_quantity)))
            selected = next(selected_sequence, None)

        project = PriceRelayProject.objects.get(pk=task_result['project_id'])

        result['set_points'] = {
            '1': project.relay_one_on_at,
            '2': project.relay_two_on_at,
            '3': project.relay_tree_on_at,
            '4': project.relay_four_on_at,
            '5': project.relay_five_on_at,
            '6': project.relay_six_on_at,
            '7': project.relay_seven_on_at,
            '8': project.relay_eight_on_at
        }


        return JsonResponse(result)