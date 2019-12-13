# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core import urlresolvers
from django.db.models import Q
from django.forms import ValidationError
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from extra_views import CreateWithInlinesView
from extra_views import InlineFormSet
from extra_views import UpdateWithInlinesView

from gridplatform import trackuser
from gridplatform.consumptions.models import Consumption
from gridplatform.consumptions.models import PulsePeriod
from gridplatform.productions.models import Production
from gridplatform.productions.models import PulsePeriod as ProductionPulsePeriod  # noqa
from gridplatform.users.decorators import auth_or_error
from gridplatform.users.decorators import auth_or_redirect
from gridplatform.users.decorators import customer_admin_or_admin_or_error
from gridplatform.users.decorators import customer_admin_or_error
from gridplatform.users.views import CustomerAdminOrAdminRequiredMixin
from gridplatform.utils.views import json_list_options
from gridplatform.utils.views import json_response
from gridplatform.utils.views import render_to
from gridplatform.utils.formsets import SurvivingFormsModelFormSetMixin
from legacy.devices.models import Agent
from legacy.devices.models import Meter
from legacy.ipc import agentserver
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import DataSeries
from legacy.datasequence_adapters.models import ConsumptionAccumulationAdapter
from legacy.datasequence_adapters.models import ProductionAccumulationAdapter
from gridplatform.utils.utilitytypes import OPTIONAL_METER_CHOICES

from .forms import AgentForm
from .forms import MeterForm
from .forms import RelayForm
from .forms import ElectricityConsumptionForm
from .forms import WaterConsumptionForm
from .forms import DistrictHeatingConsumptionForm
from .forms import GasConsumptionForm
from .forms import OilConsumptionForm
from .forms import ProductionForm
from .forms import EnergyInputPeriodForm
from .forms import VolumeInputPeriodForm
from .forms import ProductionInputPeriodForm


@auth_or_redirect
@render_to('manage_devices/agent_list.html')
def agent_list(request):
    customer = trackuser.get_customer()
    agents = Agent.objects.filter(
        customer=customer,
        no_longer_in_use=False).select_related(
        'location', 'customer')
    return {
        'agent_list': agents,
    }


@auth_or_redirect
@render_to('manage_devices/meter_list.html')
def meter_list(request):
    customer = trackuser.get_customer()
    meters = Meter.objects.filter(
        customer=customer).select_related('agent', 'location')
    return {
        'meter_list': meters,
    }


@auth_or_error
@json_response
def agent_list_json(request, customer=None):
    if not customer:
        customer = trackuser.get_customer()
    assert customer

    options = json_list_options(request)
    data = list(Agent.objects.filter(
        customer=customer, no_longer_in_use=False).select_related('location'))

    if options['search']:
        data = filter(
            lambda agent: agent.satisfies_search(options['search']), data)
    order_map = {
        'location': lambda agent: unicode(agent.location),
        'mac': lambda agent: unicode(agent.mac),
    }
    if options['order_by'] in order_map:
        data.sort(key=order_map[options['order_by']])
    if options['direction'].lower() == 'desc':
        data.reverse()
    data_slice = data[options['offset']:options['offset'] + options['count']]
    rendered = [
        render_to_string(
            'manage_devices/agent_block.html',
            {'agent': agent},
            RequestContext(request))
        for agent in data_slice
    ]

    return {
        'total': len(data),
        'data': rendered,
    }


@customer_admin_or_admin_or_error
@render_to('manage_devices/agent_form.html')
def agent_form(request, pk):
    customer = trackuser.get_customer()
    if customer:
        instance = get_object_or_404(Agent, pk=pk, customer=customer)
    else:
        instance = get_object_or_404(Agent, pk=pk)

    form = AgentForm(instance=instance, auto_id=False)

    return {
        'form': form,
        'agent': instance,
    }


@customer_admin_or_admin_or_error
@json_response
def agent_update(request, pk):
    customer = trackuser.get_customer()
    if customer:
        instance = get_object_or_404(Agent, pk=pk, customer=customer)
    else:
        instance = get_object_or_404(Agent, pk=pk)

    form = AgentForm(request.POST, instance=instance, auto_id=False)
    if form.is_valid():
        agent = form.save()
        return {
            'success': True,
            'statusText': _('The agent has been saved'),
            'html': render_to_string(
                'manage_devices/agent_block.html',
                {'agent': agent},
                RequestContext(request)
            ),
        }
    else:
        # Form contains only location, which may legally be blank, i.e. this
        # error should not be possible...
        assert False


@auth_or_error
@json_response
def meter_list_json(request, customer=None):
    if not customer:
        customer = trackuser.get_customer()
    assert customer

    options = json_list_options(request)
    data = list(Meter.objects.filter(customer=customer).select_related(
        'agent', 'location'))

    if options['search']:
        data = filter(
            lambda meter: meter.satisfies_search(options['search']), data)
    order_map = {
        'name': lambda meter: meter.name_plain.lower(),
        'location': lambda meter: unicode(meter.location),
        'agent': lambda meter: unicode(meter.agent),
    }
    if options['order_by'] in order_map:
        data.sort(key=order_map[options['order_by']])
    if options['direction'].lower() == 'desc':
        data.reverse()

    data_slice = data[options['offset']:options['offset'] + options['count']]
    rendered = [
        render_to_string(
            'manage_devices/meter_block.html',
            {'meter': meter}, RequestContext(request))
        for meter in data_slice
    ]
    return {
        'total': len(data),
        'data': rendered,
    }


class MeterUpdateView(
        CustomerAdminOrAdminRequiredMixin, UpdateWithInlinesView):
    template_name = 'manage_devices/meter_form.html'
    model = Meter
    form_class = MeterForm

    def get_success_url(self):
        return urlresolvers.reverse('manage_devices-meter-list')

    def _get_pulse_conversions(self):
        pulse_conversion_filter = Q(
            datasequence__period__pulseperiod__datasource__customerdatasource__physicalinput__meter=self.object)  # noqa
        consumptions = ConsumptionAccumulationAdapter.objects.filter(
            pulse_conversion_filter)
        productions = ProductionAccumulationAdapter.objects.filter(
            pulse_conversion_filter)
        return list(consumptions) + list(productions)

    def get_context_data(self, **context):
        if 'pulse_conversions' not in context:
            context['pulse_conversions'] = self._get_pulse_conversions()
        return super(MeterUpdateView, self).get_context_data(**context)


@customer_admin_or_error
@json_response
def meter_relay(request, pk):
    customer = trackuser.get_customer()
    meter = get_object_or_404(Meter, pk=pk)
    if meter.agent.customer != customer:
        return HttpResponseForbidden()
    relay_form = RelayForm(request.POST)
    if not relay_form.is_valid():
        return {
            'success': False,
            'statusText': _('Invalid relay state choice')
        }
    agent = meter.agent
    if not agent.online:
        return {
            'success': False,
            'statusText': _('Agent currently offline'),
        }
    relay_on = relay_form.cleaned_data['relay_state'] == 'on'
    agentserver.relay_state(
        agent.mac, [(meter.connection_type, meter.manufactoring_id)], relay_on)
    return {
        'success': True,
        'statusText': _('Sending relay state change request')
    }


@customer_admin_or_error
@json_response
def meter_relay_toggle(request, pk, action):
    customer = trackuser.get_customer()
    meter = get_object_or_404(Meter, pk=pk)
    if meter.agent.customer != customer:
        return HttpResponseForbidden()

    agent = meter.agent
    if not agent.online:
        return {
            'success': False,
            'statusText': _('Agent currently offline'),
        }
    relay_on = action == 'on'
    agentserver.relay_state(
        agent.mac, [(meter.connection_type, meter.manufactoring_id)], relay_on)
    return {
        'success': True,
        'statusText': _('Sending relay state change request')
    }


@customer_admin_or_error
@json_response
def meter_relay_state(request, pk):
    customer = trackuser.get_customer()
    meter = get_object_or_404(Meter, pk=pk)
    if meter.agent.customer != customer:
        return HttpResponseForbidden()

    agent = meter.agent
    if not agent.online:
        return {
            'success': False,
            'statusText': _('Agent currently offline'),
        }
    state = 'off'
    if meter.relay_on:
        state = 'on'

    return {
        'success': True,
        'state': state,
    }


class InputPeriodFormSetFormSet(
        SurvivingFormsModelFormSetMixin, BaseInlineFormSet):
    def clean(self):
        super(InputPeriodFormSetFormSet, self).clean()

        if any(self.errors):
            return

        surviving_forms = self.surviving_forms()

        if not surviving_forms:
            raise ValidationError(
                _('Must define at least one period'))

        periods = [form.instance for form in surviving_forms]
        self.model.clean_overlapping_periods(periods)


class InputPeriodFormSetBase(InlineFormSet):
    formset_class = InputPeriodFormSetFormSet


class EnergyInputPeriodInline(InputPeriodFormSetBase):
    model = PulsePeriod
    form_class = EnergyInputPeriodForm
    extra = 1


class VolumeInputPeriodInline(InputPeriodFormSetBase):
    model = PulsePeriod
    form_class = VolumeInputPeriodForm
    extra = 1


class ProductionInputPeriodInline(InputPeriodFormSetBase):
    model = ProductionPulsePeriod
    form_class = ProductionInputPeriodForm
    extra = 1


class MeterPulseConversionViewMixin(object):
    def forms_valid(self, form, inlines):
        physicalinput_id = self.kwargs.get('physicalinput', None)
        if physicalinput_id is None:
            # NOTE: Ugly hack; but this code is doomed anyway; DataSequences
            # are supposed to work with different inputs, possibly from
            # different meters; meaning that input IDs should become explicit
            # in the form...  (... this was less of a hack than putting it in
            # the URL, as the same hack would then have to be used to obtain
            # the URL...)
            physicalinput_id = inlines[0].forms[0].instance.datasource_id
        for inlineform in inlines[0].forms:
            inlineform.instance.datasource_id = physicalinput_id
        return super(MeterPulseConversionViewMixin, self).forms_valid(
            form, inlines)

    def get_success_url(self):
        return urlresolvers.reverse('manage_devices-meter-update',
                                    kwargs={'pk': self.kwargs['meter']})


class CreateConsumptionAccumulationAdapterMixin(object):
    def forms_valid(self, form, inlines):
        """
        requires `self.utility_type` to be set.
        """
        response = super(
            CreateConsumptionAccumulationAdapterMixin, self).forms_valid(
                form, inlines)
        ConsumptionAccumulationAdapter.objects.get_or_create(
            datasequence=self.object,
            role=DataRoleField.CONSUMPTION,
            utility_type=self.utility_type,
            unit=self.object.unit)
        return response


class ElectricityConsumptionCreateView(
        CreateConsumptionAccumulationAdapterMixin,
        MeterPulseConversionViewMixin,
        CreateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = ElectricityConsumptionForm
    inlines = [EnergyInputPeriodInline]
    utility_type = OPTIONAL_METER_CHOICES.electricity


class ElectricityConsumptionUpdateView(
        MeterPulseConversionViewMixin, UpdateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = ElectricityConsumptionForm
    inlines = [EnergyInputPeriodInline]


class WaterConsumptionCreateView(
        CreateConsumptionAccumulationAdapterMixin,
        MeterPulseConversionViewMixin,
        CreateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = WaterConsumptionForm
    inlines = [VolumeInputPeriodInline]
    utility_type = OPTIONAL_METER_CHOICES.water


class WaterConsumptionUpdateView(
        MeterPulseConversionViewMixin, UpdateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = WaterConsumptionForm
    inlines = [VolumeInputPeriodInline]


class DistrictHeatingConsumptionCreateView(
        CreateConsumptionAccumulationAdapterMixin,
        MeterPulseConversionViewMixin,
        CreateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = DistrictHeatingConsumptionForm
    inlines = [EnergyInputPeriodInline]
    utility_type = OPTIONAL_METER_CHOICES.district_heating


class DistrictHeatingConsumptionUpdateView(
        MeterPulseConversionViewMixin, UpdateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = DistrictHeatingConsumptionForm
    inlines = [EnergyInputPeriodInline]


class GasConsumptionCreateView(
        CreateConsumptionAccumulationAdapterMixin,
        MeterPulseConversionViewMixin,
        CreateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = GasConsumptionForm
    inlines = [VolumeInputPeriodInline]
    utility_type = OPTIONAL_METER_CHOICES.gas


class GasConsumptionUpdateView(
        MeterPulseConversionViewMixin, UpdateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = GasConsumptionForm
    inlines = [VolumeInputPeriodInline]


class OilConsumptionCreateView(
        CreateConsumptionAccumulationAdapterMixin,
        MeterPulseConversionViewMixin,
        CreateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = OilConsumptionForm
    inlines = [VolumeInputPeriodInline]
    utility_type = OPTIONAL_METER_CHOICES.oil


class OilConsumptionUpdateView(
        MeterPulseConversionViewMixin, UpdateWithInlinesView):
    template_name = 'manage_devices/consumption_form.html'
    model = Consumption
    form_class = OilConsumptionForm
    inlines = [VolumeInputPeriodInline]


class ProductionCreateView(
        MeterPulseConversionViewMixin, CreateWithInlinesView):
    template_name = 'manage_devices/production_form.html'
    model = Production
    form_class = ProductionForm
    inlines = [ProductionInputPeriodInline]

    def get_form_kwargs(self, **kwargs):
        kwargs = super(
            ProductionCreateView, self).get_form_kwargs(
            **kwargs)
        kwargs['unit'] = self.kwargs['production_unit']
        return kwargs

    def construct_inlines(self):
        inlines = super(
            ProductionCreateView, self).construct_inlines()
        for inlineform in inlines[0].forms:
            inlineform.instance.output_unit = self.kwargs['production_unit']
        return inlines

    def forms_valid(self, form, inlines):
        response = super(
            ProductionCreateView, self).forms_valid(
                form, inlines)
        ProductionAccumulationAdapter.objects.get_or_create(
            datasequence=self.object,
            role=DataRoleField.PRODUCTION,
            utility_type=OPTIONAL_METER_CHOICES.unknown,
            unit=self.object.unit)
        return response


class ProductionUpdateView(
        MeterPulseConversionViewMixin, UpdateWithInlinesView):
    template_name = 'manage_devices/production_form.html'
    model = Production
    form_class = ProductionForm
    inlines = [ProductionInputPeriodInline]


def pulseconversion_update(request, meter, pk):
    ds = get_object_or_404(DataSeries, id=pk)
    adapter = ds.subclass_instance
    if adapter.utility_type == OPTIONAL_METER_CHOICES.electricity:
        return redirect('manage_devices-pulseconversion-electricity-update',
                        meter=meter, pk=adapter.datasequence_id)
    elif adapter.utility_type == OPTIONAL_METER_CHOICES.water:
        return redirect('manage_devices-pulseconversion-water-update',
                        meter=meter, pk=adapter.datasequence_id)
    elif adapter.utility_type == \
            OPTIONAL_METER_CHOICES.district_heating:
        return redirect(
            'manage_devices-pulseconversion-district_heating-update',
            meter=meter, pk=adapter.datasequence_id)
    elif adapter.utility_type == OPTIONAL_METER_CHOICES.gas:
        return redirect('manage_devices-pulseconversion-gas-update',
                        meter=meter, pk=adapter.datasequence_id)
    elif adapter.utility_type == OPTIONAL_METER_CHOICES.oil:
        return redirect('manage_devices-pulseconversion-oil-update',
                        meter=meter, pk=adapter.datasequence_id)
    elif adapter.role == DataRoleField.PRODUCTION:
        return redirect('manage_devices-pulseconversion-production-update',
                        meter=meter, pk=adapter.datasequence_id)
