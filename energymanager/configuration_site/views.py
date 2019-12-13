# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import operator

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404
from django.utils.formats import date_format

from gridplatform.utils import generic_views
from gridplatform.utils.breadcrumbs import Breadcrumb
from gridplatform.utils.breadcrumbs import Breadcrumbs
from gridplatform.utils.views import ChooseCustomerBase
from gridplatform.utils.views import CustomerInKwargsMixin
from gridplatform.utils.views import CustomerListMixin
from gridplatform.utils.views import CustomerViewBase
from gridplatform.utils.views import HomeViewBase
from gridplatform.consumptions.tasks import consumptions_weekly_utility_task  # noqa
from gridplatform.customer_datasources.models import CustomerDataSource
from gridplatform.consumptions.models import Consumption
from gridplatform.utils.forms import HalfOpenTimePeriodModelForm
from gridplatform.consumptions.models import NonpulsePeriod
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.utilitytypes import ENERGY_UTILITY_TYPE_TO_DISPLAY_UNIT_MAP  # noqa
from gridplatform.utils.views import StartTaskView
from gridplatform.utils.forms import YearWeekPeriodForm
from gridplatform.utils.forms import this_week_initial_values
from gridplatform.utils.views import FinalizeTaskView
from gridplatform.utils.preferredunits import PhysicalUnitConverter
from gridplatform.utils.views import JsonResponse
from gridplatform.tariffs.models import EnergyTariff
from legacy.devices.models import Agent, Meter, PhysicalInput

from .forms import MeterModelForm

class HomeView(HomeViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'configuration_site:customer-datasource-list',
            kwargs={'customer_id': customer_id})

    def get_choose_customer_url(self):
        return reverse(
            'configuration_site:choose-customer')


class ChooseCustomer(ChooseCustomerBase):
    template_name = 'configuration_site/choose_customer.html'


class CustomerView(CustomerViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'configuration_site:customer-datasource-list',
            kwargs={'customer_id': customer_id})


class CustomerDataSourceList(
        CustomerListMixin, generic_views.TemplateView):
    template_name = 'configuration_site/customer_datasource_list.html'

    @staticmethod
    def build_breadcrumbs(customer_id):
        return Breadcrumbs() + Breadcrumb(
            _('Customer Data Sources'),
            reverse(
                'configuration_site:customer-datasource-list',
                kwargs={'customer_id': customer_id}))

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id)


class CustomerDataSourceListContentView(
        CustomerListMixin, generic_views.ListView):
    model = CustomerDataSource
    template_name = 'configuration_site/_customer_datasource_list_content.html'
    paginate_by = 40
    sort_fields = ['name_plain', 'unit', 'hardware_id', ]
    search_fields = ['name_plain', 'unit', 'hardware_id', ]


class CustomerDataSourceCreateView(
        CustomerListMixin, generic_views.CreateView):
    model = CustomerDataSource
    template_name = 'configuration_site/customer_datasource_form.html'
    fields = ('name', 'unit', 'hardware_id')

    def form_valid(self, form):
        form.instance.customer_id = self._customer.id
        return super(CustomerDataSourceCreateView, self).form_valid(
            form)

    def get_success_url(self):
        return reverse(
            'configuration_site:customer-datasource-list',
            kwargs={'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse(
            'configuration_site:customer-datasource-list',
            kwargs={'customer_id': self._customer.id})

    def get_breadcrumbs(self):
        return CustomerDataSourceList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Create LED Light Project'))


class CustomerDataSourceUpdateView(
        CustomerListMixin, generic_views.UpdateView):
    model = CustomerDataSource
    template_name = 'configuration_site/customer_datasource_form.html'
    fields = (
        'name', 'hardware_id',
    )

    def get_success_url(self):
        return reverse(
            'configuration_site:customer-datasource-list',
            kwargs={'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse(
            'configuration_site:customer-datasource-list',
            kwargs={'customer_id': self._customer.id})

    def get_delete_url(self):
        if not self.object.rawdata_set.all():
            return reverse('configuration_site:customer-datasource-delete',
                           kwargs={'customer_id':
                                   self._customer.id,
                                   'pk':
                                   self.object.id})

    def get_breadcrumbs(self):
        return CustomerDataSourceList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(self.object)


class CustomerDataSourceDeleteView(
        CustomerListMixin, generic_views.DeleteView):
    model = CustomerDataSource

    def get_success_url(self):
        return reverse(
            'configuration_site:customer-datasource-list',
            kwargs={'customer_id': self._customer.id})


class ConsumptionList(
        CustomerListMixin, generic_views.TemplateView):
    template_name = 'configuration_site/consumption_list.html'

    @staticmethod
    def build_breadcrumbs(customer_id):
        return Breadcrumbs() + Breadcrumb(
            _('Consumptions'),
            reverse(
                'configuration_site:consumption-list',
                kwargs={'customer_id': customer_id}))

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id)


class ConsumptionListContentView(
        CustomerListMixin, generic_views.ListView):
    model = Consumption
    template_name = \
        'configuration_site/_consumption_list_content.html'
    paginate_by = 40
    search_fields = ['name', ]


class ChartFormViewMixin(object):
    def get_context_data(self, **kwargs):
        if 'chart_form' not in kwargs:
            kwargs['chart_form'] = YearWeekPeriodForm(
                this_week_initial_values())
        return super(ChartFormViewMixin, self).get_context_data(**kwargs)


class ConsumptionDetailView(
        CustomerListMixin, ChartFormViewMixin, generic_views.DetailView):
    model = Consumption
    template_name = \
        'configuration_site/consumption_detail.html'

    @staticmethod
    def build_breadcrumbs(customer_id, consumption_id):
        return ConsumptionList.build_breadcrumbs(customer_id) + \
            Breadcrumb(
            _('Consumption Detail'),
            reverse(
                'configuration_site:consumption-detail',
                kwargs={'customer_id': customer_id, 'pk': consumption_id}))

    def get_context_data(self, **kwargs):
        context = super(
            ConsumptionDetailView,
            self).get_context_data(**kwargs)
        context['panel_title'] = \
            _('Consumption: %(name)s' % {
                'name': self.object})

        if 'utility_unit' not in kwargs:
            context['utility_unit'] = 'watt*hours'

        return context

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id, self.object.id)


class PeriodForm(HalfOpenTimePeriodModelForm):
    class Meta:
        fields = ('datasequence',)
        localized_fields = '__all__'


class PeriodViewMixin(object):
    @cached_property
    def _datasequence(self):
        datasequence_model = self.model._meta.get_field('datasequence').rel.to
        return get_object_or_404(
            datasequence_model, id=self.kwargs['datasequence_id'])

    def get_form(self, form_class):
        form = super(PeriodViewMixin, self).get_form(form_class)
        form.instance.datasequence = self._datasequence
        datasource_choices = [
            (ds.id, unicode(ds)) for ds in
            form.fields['datasource'].queryset.all()
            if PhysicalQuantity.compatible_units(
                ds.unit, self._datasequence.unit)
        ]
        datasource_choices.sort(key=operator.itemgetter(1))
        form.fields['datasource'].choices = ((None, '---------'),) + tuple(
            datasource_choices)
        return form


class StartWeekConsumptionUtilityBarChartView(
        CustomerInKwargsMixin, StartTaskView):
    task = consumptions_weekly_utility_task
    finalize_url_name = 'configuration_site:utility-bar-chart-finalize'
    form_class = YearWeekPeriodForm

    def get_task_kwargs(self, form):
        from_timestamp, to_timestamp = form.get_timestamps()
        result = {}
        result['consumption_ids'] = [self.kwargs['consumption_id']]
        result['from_timestamp'] = from_timestamp
        result['to_timestamp'] = to_timestamp
        return result

    def get_finalize_url(self):
        return reverse(
            self.finalize_url_name,
            kwargs={'customer_id': self._customer.id})


class FinalizeWeekUtilityBarChartView(CustomerInKwargsMixin, FinalizeTaskView):
    def finalize_task(self, task_result):
        unit = ENERGY_UTILITY_TYPE_TO_DISPLAY_UNIT_MAP[
            2000]
        print unit
        self.unit_converter = PhysicalUnitConverter('watt*hour')

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


class ConsumptionNonpulsePeriodForm(PeriodForm):
    class Meta(PeriodForm.Meta):
        model = NonpulsePeriod
        fields = ('datasource',)


class ConsumptionNonpulsePeriodCreateView(
        CustomerListMixin, PeriodViewMixin, generic_views.CreateView):
    model = NonpulsePeriod
    template_name = \
        'configuration_site/nonpulseperiod_form.html'
    form_class = ConsumptionNonpulsePeriodForm

    def get_success_url(self):
        return reverse(
            'configuration_site:consumption-detail',
            kwargs={'pk': self.kwargs['datasequence_id'],
                    'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse('configuration_site:consumption-detail',
                       kwargs={'pk': self.kwargs['datasequence_id'],
                               'customer_id': self._customer.id})

    def get_breadcrumbs(self):
        return ConsumptionDetailView.build_breadcrumbs(
            self._customer.id, self.kwargs['datasequence_id']) + \
            Breadcrumb(_('Create input period'))


class ConsumptionNonpulsePeriodUpdateView(
        CustomerListMixin, PeriodViewMixin, generic_views.UpdateView):
    model = NonpulsePeriod
    template_name = \
        'configuration_site/nonpulseperiod_form.html'
    form_class = ConsumptionNonpulsePeriodForm

    def get_success_url(self):
        return reverse(
            'configuration_site:consumption-detail',
            kwargs={'pk': self.object.datasequence_id,
                    'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse('configuration_site:consumption-detail',
                       kwargs={'pk': self.object.datasequence_id,
                               'customer_id': self._customer.id})

    def get_delete_url(self):
        return reverse('configuration_site:consumptionnonpulseperiod-delete',
                       kwargs={'pk': self.object.id,
                               'customer_id': self._customer.id})

    def get_breadcrumbs(self):
        return ConsumptionDetailView.build_breadcrumbs(
            self._customer.id, self.kwargs['datasequence_id']) + \
            Breadcrumb(_('Edit input period'))


class ConsumptionNonpulsePeriodDeleteView(
        CustomerListMixin, generic_views.DeleteView):
    model = NonpulsePeriod

    def get_success_url(self):
        return reverse(
            'configuration_site:consumption-detail',
            kwargs={'pk': self.object.datasequence_id,
                    'customer_id': self._customer.id})


class ConsumptionCreateView(
        CustomerListMixin, generic_views.CreateView):
    model = Consumption
    template_name = \
        'configuration_site/consumption_form.html'
    fields = ('name', 'unit',)

    def get_success_url(self):
        return reverse(
            'configuration_site:consumption-detail',
            kwargs={'pk': self.object.id, 'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse('configuration_site:consumption-list',
                       kwargs={'customer_id': self._customer.id})

    def get_breadcrumbs(self):
        return ConsumptionList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Create Consumption Datasequence'))


class ConsumptionUpdateView(
        CustomerListMixin, generic_views.UpdateView):
    model = Consumption
    template_name = \
        'configuration_site/consumption_form.html'
    fields = ('name', )

    def get_success_url(self):
        return reverse(
            'configuration_site:consumption-detail',
            kwargs={'pk': self.object.id, 'customer_id': self._customer.id})

    def get_breadcrumbs(self):
        return (
            (_('Data Sequences'),
             reverse(
                 'configuration_site:consumption-list',
                 kwargs={'customer_id': self._customer.id})),
            (self.object,
             reverse(
                 'configuration_site:consumption-detail',
                 kwargs={'pk': self.object.id,
                         'customer_id': self._customer.id})),
            (_('Edit consumption data sequence'), ''),
        )

    def get_cancel_url(self):
        return reverse('configuration_site:consumption-detail',
                       kwargs={'pk': self.object.id,
                               'customer_id': self._customer.id})

    def get_delete_url(self):
        return reverse('configuration_site:consumption-delete',
                       kwargs={'pk': self.object.id,
                               'customer_id': self._customer.id})


class ConsumptionDeleteView(
        CustomerListMixin, generic_views.DeleteView):
    model = Consumption

    def get_success_url(self):
        return reverse(
            'configuration_site:consumption-list',
            kwargs={'customer_id': self._customer.id})


class TariffList(
        CustomerListMixin, generic_views.TemplateView):
    template_name = 'configuration_site/tariff_list.html'

    @staticmethod
    def build_breadcrumbs(customer_id):
        return Breadcrumbs() + Breadcrumb(
            _('Tariffs'),
            reverse(
                'configuration_site:tariff-list',
                kwargs={'customer_id': customer_id}))

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id)


class TariffListContentView(
        CustomerListMixin, generic_views.ListView):
    model = EnergyTariff
    template_name = \
        'configuration_site/_tariff_list_content.html'
    paginate_by = 40
    search_fields = ['name', ]


class TariffCreateView(
        CustomerListMixin, generic_views.CreateView):
    model = EnergyTariff
    template_name = \
        'configuration_site/tariff_form.html'
    fields = ('name',)

    def get_success_url(self):
        return reverse(
            'configuration_site:tariff-list',
            kwargs={'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse('configuration_site:tariff-list',
                       kwargs={'customer_id': self._customer.id})

    def get_breadcrumbs(self):
        return TariffList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Create Energy Tariff'))


class TariffUpdateView(
        CustomerListMixin, generic_views.UpdateView):
    model = EnergyTariff
    template_name = \
        'configuration_site/tariff_form.html'
    fields = ('name', )

    def get_breadcrumbs(self):
        return TariffList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Update Energy Tariff'))

    def get_success_url(self):
        return reverse(
            'configuration_site:tariff-list',
            kwargs={'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse('configuration_site:tariff-list',
                       kwargs={'customer_id': self._customer.id})


class AgentList(
        CustomerListMixin, generic_views.TemplateView):
    template_name = 'configuration_site/agent_list.html'

    @staticmethod
    def build_breadcrumbs(customer_id):
        return Breadcrumbs() + Breadcrumb(
            _('Agents'),
            reverse(
                'configuration_site:agent-list',
                kwargs={'customer_id': customer_id}))

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id)


class AgentListContentView(
        CustomerListMixin, generic_views.ListView):
    model = Agent
    template_name = 'configuration_site/_agent_list_content.html'
    paginate_by = 40
    sort_fields = ['mac', 'location', ]
    search_fields = ['mac', 'location', ]


class AgentCreateView(
        CustomerListMixin, generic_views.CreateView):
    model = Agent
    template_name = \
        'configuration_site/agent_form.html'
    fields = ('mac', 'location')

    def form_valid(self, form):
        form.instance.customer_id = self._customer.id
        return super(AgentCreateView, self).form_valid(
            form)

    def get_success_url(self):
        return reverse(
            'configuration_site:agent-list',
            kwargs={'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse('configuration_site:agent-list',
                       kwargs={'customer_id': self._customer.id})

    def get_breadcrumbs(self):
        return AgentList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Create Agent'))


class AgentUpdateView(
        CustomerListMixin, generic_views.UpdateView):
    model = Agent
    template_name = \
        'configuration_site/agent_form.html'
    fields = ('location', )

    def get_breadcrumbs(self):
        return AgentList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Update Agent'))

    def get_success_url(self):
        return reverse(
            'configuration_site:agent-list',
            kwargs={'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse('configuration_site:agent-list',
                       kwargs={'customer_id': self._customer.id})


class MeterList(
        CustomerListMixin, generic_views.TemplateView):
    template_name = 'configuration_site/meter_list.html'

    @staticmethod
    def build_breadcrumbs(customer_id):
        return Breadcrumbs() + Breadcrumb(
            _('Meters'),
            reverse(
                'configuration_site:meter-list',
                kwargs={'customer_id': customer_id}))

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id)


class MeterListContentView(
        CustomerListMixin, generic_views.ListView):
    model = Meter
    template_name = 'configuration_site/_meter_list_content.html'
    paginate_by = 40
    sort_fields = ['name', 'connection_type', "hardware_id", "location"]
    search_fields = ['name', 'connection_type', "hardware_id", "location"]


class MeterCreateView(
        CustomerListMixin, generic_views.CreateView):
    model = Meter
    template_name = \
        'configuration_site/meter_form.html'
    fields = ('name', 'agent', 'connection_type', 'location', 'hardware_id')
    form_class = MeterModelForm

    def form_valid(self, form):
        form.instance.customer_id = self._customer.id
        form.instance.agent_id = self.request.POST.get('agent')
        form.instance.connection_type = Meter.WIBEEE
        form.instance.manufactoring_id = 0

        response = super(MeterCreateView, self).form_valid(form)
        meter = form.instance
        meter_type = int(self.request.POST.get('meter_type'))
        if meter_type == MeterModelForm.WIBEEE:
            PhysicalInput.objects.create(
                meter=meter,
                order=0,
                hardware_id="e1",
                name_plain="Energy Phase 1",
                unit="milliwatt*hour",
                type=PhysicalInput.ELECTRICITY
            )
            PhysicalInput.objects.create(
                meter=meter,
                order=1,
                hardware_id="e2",
                name_plain="Energy Phase 2",
                unit="milliwatt*hour",
                type=PhysicalInput.ELECTRICITY
            )
            PhysicalInput.objects.create(
                meter=meter,
                order=2,
                hardware_id="e3",
                name_plain="Energy Phase 3",
                unit="milliwatt*hour",
                type=PhysicalInput.ELECTRICITY
            )
            PhysicalInput.objects.create(
                meter=meter,
                order=3,
                hardware_id="et",
                name_plain="Energy Total",
                unit="milliwatt*hour",
                type=PhysicalInput.ELECTRICITY
            )
        elif meter_type == MeterModelForm.DATAHUB:
            PhysicalInput.objects.create(
                meter=meter,
                order=0,
                name_plain="Datahub",
                unit="milliwatt*hour",
                type=PhysicalInput.ELECTRICITY
            )

        return response

    def get_form_kwargs(self):
        kwargs = super(MeterCreateView, self).get_form_kwargs()
        kwargs.update({'customer_id': self._customer.id})
        return kwargs

    def get_success_url(self):
        return reverse(
            'configuration_site:meter-list',
            kwargs={'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse('configuration_site:meter-list',
                       kwargs={'customer_id': self._customer.id})

    def get_breadcrumbs(self):
        return MeterList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Create Meter'))


class MeterUpdateView(
        CustomerListMixin, generic_views.UpdateView):
    model = Meter
    template_name = \
        'configuration_site/meter_form.html'
    fields = ('name', 'location', 'hardware_id')

    def get_breadcrumbs(self):
        return MeterList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Update Meter'))

    def get_success_url(self):
        return reverse(
            'configuration_site:meter-list',
            kwargs={'customer_id': self._customer.id})

    def get_cancel_url(self):
        return reverse('configuration_site:meter-list',
                       kwargs={'customer_id': self._customer.id})
