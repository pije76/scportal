# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import json

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.utils.decorators import method_decorator
from django.views.generic.edit import CreateView
from django.views.generic.edit import UpdateView
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.forms.models import BaseInlineFormSet

from extra_views import InlineFormSet
from extra_views import UpdateWithInlinesView
from extra_views import CreateWithInlinesView

from gridplatform import trackuser
from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.measurementpoints.proxies import ConsumptionMeasurementPointSummation  # noqa
from legacy.measurementpoints.proxies import ConsumptionMultiplicationPoint
from legacy.measurementpoints.proxies import CurrentMeasurementPoint
from legacy.measurementpoints.proxies import DistrictHeatingMeasurementPoint
from legacy.measurementpoints.proxies import MeasurementPoint
from legacy.measurementpoints.proxies import PowerMeasurementPoint
from legacy.measurementpoints.proxies import ReactivePowerMeasurementPoint
from legacy.measurementpoints.proxies import ReactiveEnergyMeasurementPoint
from legacy.measurementpoints.proxies import PowerFactorMeasurementPoint
from legacy.measurementpoints.proxies import ProductionMeasurementPoint
from legacy.measurementpoints.proxies import TemperatureMeasurementPoint
from legacy.measurementpoints.proxies import VoltageMeasurementPoint
from gridplatform.users.decorators import auth_or_error
from gridplatform.users.decorators import customer_admin_or_error
from gridplatform.utils import DATETIME_MIN
from gridplatform.utils import utilitytypes
from gridplatform.utils.formsets import SurvivingFormsModelFormSetMixin
from gridplatform.utils.views import json_list_options
from gridplatform.utils.views import json_response
from legacy.efficiencymeasurementpoints.models import EfficiencyMeasurementPoint  # noqa
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import Chain
from legacy.measurementpoints.models import ChainLink
from legacy.measurementpoints.models import CostCalculation
from legacy.measurementpoints.models import DataSeries
from legacy.measurementpoints.models import Graph

from .forms import ConsumptionMeasurementPointUpdateForm
from .forms import ConsumptionMeasurementPointSummationForm
from .forms import InputConsumptionMeasurementPointForm
from .forms import MultiplicationConsumptionMeasurementPointForm
from .forms import DistrictHeatingMeasurementPointCreateForm
from .forms import DistrictHeatingMeasurementPointEditForm
from .forms import TariffPeriodForm
from .forms import TemperatureMeasurementPointForm
from .forms import InputTemperatureMeasurementPointForm
from .forms import ProductionMeasurementPointForm
from .forms import InputProductionMeasurementPointForm
from .forms import InputCurrentMeasurementPointForm
from .forms import CurrentMeasurementPointForm
from .forms import InputVoltageMeasurementPointForm
from .forms import InputPowerMeasurementPointForm
from .forms import InputReactivePowerMeasurementPointForm
from .forms import InputReactiveEnergyMeasurementPointForm
from .forms import InputPowerFactorMeasurementPointForm
from .forms import VoltageMeasurementPointForm
from .forms import PowerMeasurementPointForm
from .forms import ReactivePowerMeasurementPointForm
from .forms import ReactiveEnergyMeasurementPointForm
from .forms import PowerFactorMeasurementPointForm
from .forms import EfficiencyMeasurementPointForm
from .forms import InputEfficiencyMeasurementPointForm


# for reuse in admin interface
def list_data(request, customer, template, data=None):
    options = json_list_options(request)

    if data is None:
        data = [mp.subclass_instance for mp in
                MeasurementPoint.objects.subclass_only().filter(
                    role__in=Collection.DATA_POINTS,
                    customer=customer).distinct().select_related('parent')]

    if options['search']:
        data = filter(
            lambda graph_collection: graph_collection.satisfies_search(
                options['search']), data)

    order_map = {
        'group': lambda graph_collection: unicode(
            graph_collection.parent),
        'name': lambda graph_collection: unicode(
            graph_collection.name_plain.lower()),
    }
    if options['order_by'] in order_map:
        data.sort(key=order_map[options['order_by']])
    if options['direction'].lower() == 'desc':
        data.reverse()

    data_slice = data[options['offset']:options['offset'] + options['count']]

    rendered = [
        render_to_string(
            template,
            {'graph_collection': graph_collection, },
            RequestContext(request))
        for graph_collection in data_slice
    ]
    return {
        'total': len(data),
        'data': rendered,
    }


@customer_admin_or_error
def measurementpoint_form(request, pk):
    instance = get_object_or_404(
        MeasurementPoint.objects.subclass_only(),
        customer=request.customer, id=pk).subclass_instance

    if isinstance(instance, ConsumptionMeasurementPointSummation):
        return ConsumptionMeasurementPointSummationUpdateView.as_view()(
            request, pk=pk)
    elif isinstance(instance, ConsumptionMultiplicationPoint):
        return ConsumptionMultiplicationPointUpdateView.as_view()(
            request, pk=pk)
    elif isinstance(instance, DistrictHeatingMeasurementPoint):
        return DistrictHeatingMeasurementPointUpdateView.as_view()(
            request, pk=pk)
    elif isinstance(instance, ConsumptionMeasurementPoint):
        return ConsumptionMeasurementPointUpdateView.as_view(
            form_class=ConsumptionMeasurementPointUpdateForm)(request, pk=pk)
    elif isinstance(instance, TemperatureMeasurementPoint):
        return temperature_measurement_point_update_form(request, instance)
    elif isinstance(instance, ProductionMeasurementPoint):
        return ProductionMeasurementPointUpdate.as_view()(request, pk=pk)
    elif isinstance(instance, CurrentMeasurementPoint):
        return CurrentMeasurementPointUpdate.as_view()(request, pk=pk)
    elif isinstance(instance, EfficiencyMeasurementPoint):
        return EfficiencyMeasurementPointUpdate.as_view()(request, pk=pk)
    elif isinstance(instance, VoltageMeasurementPoint):
        return VoltageMeasurementPointUpdate.as_view()(request, pk=pk)
    elif isinstance(instance, PowerMeasurementPoint):
        return PowerMeasurementPointUpdate.as_view()(request, pk=pk)
    elif isinstance(instance, ReactivePowerMeasurementPoint):
        return ReactivePowerMeasurementPointUpdate.as_view()(request, pk=pk)
    elif isinstance(instance, ReactiveEnergyMeasurementPoint):
        return ReactiveEnergyMeasurementPointUpdate.as_view()(request, pk=pk)
    elif isinstance(instance, PowerFactorMeasurementPoint):
        return PowerFactorMeasurementPointUpdate.as_view()(request, pk=pk)


@customer_admin_or_error
@json_response
def measurementpoint_delete(request):
    instance = get_object_or_404(Collection, pk=request.GET['pk'])
    customer = trackuser.get_customer()
    if instance.customer != customer or \
            not instance.subclass_instance.is_deletable():
        return HttpResponseForbidden()
    instance.delete()
    return {
        'success': True,
        'statusText': _('The measurement point has been deleted'),
    }


@auth_or_error
@json_response
def list_json(request):
    customer = trackuser.get_customer()
    return list_data(
        request, customer, 'manage_measurementpoints/block.html')


class BaseMeasurementPointSlideIn(object):
    """
    Mixin for measurement point slide-in views.

    Provides means to render normal respones aswell as json responses.  The
    former is useful for slide-in form rendering, and the later is useful for
    slide-in form validation.
    """

    @method_decorator(customer_admin_or_error)
    def dispatch(self, request, *args, **kwargs):
        return super(BaseMeasurementPointSlideIn, self).dispatch(
            request, *args, **kwargs)

    def render_valid_to_json_response(self, context):
        data = {
            'success': True,
            'statusText': self.status_text,
            'html': render_to_string(
                'manage_measurementpoints/block.html',
                context,
                RequestContext(self.request)),
            'parent': self.object.parent_id or None,
        }
        json_data = json.dumps(data, cls=DjangoJSONEncoder)
        return HttpResponse(json_data, content_type='application/json')

    def render_invalid_to_json_response(self, context):
        data = {
            'success': False,
            'html': render_to_string(
                self.template_name,
                context,
                RequestContext(self.request))
        }
        json_data = json.dumps(data, cls=DjangoJSONEncoder)
        return HttpResponse(json_data, content_type='application/json')

    def get_context_data(self, **kwargs):
        if self.object:
            kwargs['delete_prevention_reason'] = \
                self.object.get_delete_prevention_reason()
        return super(
            BaseMeasurementPointSlideIn,
            self).get_context_data(**kwargs)


class MeasurementPointSlideInFormMixin(BaseMeasurementPointSlideIn):
    """
    Mixin for measurement point slide-in form views.

    Works by:

      - displaying initial form if method is GET
      - displaying validated form if method is POST and form is invalid (JSON)
      - displaying success message and MP block if method is POST and form is
        valid (JSON)
    """
    def form_invalid(self, form):
        return self.render_invalid_to_json_response(
            self.get_context_data(form=form))

    def form_valid(self, form):
        self.object = form.save()
        return self.render_valid_to_json_response(
            self.get_context_data(graph_collection=self.object))


class MeasurementPointSlideInFormWithInlinesMixin(BaseMeasurementPointSlideIn):
    """
    Mixin for measurement point slide-in form views that also has inlines.

    Works by:

      - displaying initial form if method is GET
      - displaying validated form if method is POST and form is invalid (JSON)
      - displaying success message and MP block if method is POST and form is
        valid (JSON)
    """

    def forms_invalid(self, form, inlines):
        return self.render_invalid_to_json_response(
            self.get_context_data(form=form, inlines=inlines))

    def forms_valid(self, form, inlines):
        self.object = form.save()
        for formset in inlines:
            formset.save()
        return self.render_valid_to_json_response(
            self.get_context_data(graph_collection=self.object))


class CurrentMeasurementPointCreate(
        MeasurementPointSlideInFormMixin, CreateView):
    model = CurrentMeasurementPoint
    form_class = InputCurrentMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_create_form.html"
    status_text = _('The measurement point has been created')


class CurrentMeasurementPointUpdate(
        MeasurementPointSlideInFormMixin, UpdateView):
    model = CurrentMeasurementPoint
    form_class = CurrentMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_update_form.html"
    status_text = _('The measurement point has been updated')


class EfficiencyMeasurementPointCreate(
        MeasurementPointSlideInFormMixin, CreateView):
    model = EfficiencyMeasurementPoint
    form_class = InputEfficiencyMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_create_form.html"
    status_text = _('The measurement point has been created')


class EfficiencyMeasurementPointUpdate(
        MeasurementPointSlideInFormMixin, UpdateView):
    model = EfficiencyMeasurementPoint
    form_class = EfficiencyMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_update_form.html"
    status_text = _('The measurement point has been updated')


class VoltageMeasurementPointCreate(
        MeasurementPointSlideInFormMixin, CreateView):
    model = VoltageMeasurementPoint
    form_class = InputVoltageMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_create_form.html"
    status_text = _('The measurement point has been created')


class VoltageMeasurementPointUpdate(
        MeasurementPointSlideInFormMixin, UpdateView):
    model = VoltageMeasurementPoint
    form_class = VoltageMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_update_form.html"
    status_text = _('The measurement point has been updated')


class PowerMeasurementPointCreate(
        MeasurementPointSlideInFormMixin, CreateView):
    model = PowerMeasurementPoint
    form_class = InputPowerMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_create_form.html"
    status_text = _('The measurement point has been created')


class PowerMeasurementPointUpdate(
        MeasurementPointSlideInFormMixin, UpdateView):
    model = PowerMeasurementPoint
    form_class = PowerMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_update_form.html"
    status_text = _('The measurement point has been updated')


class ReactivePowerMeasurementPointCreate(
        MeasurementPointSlideInFormMixin, CreateView):
    model = ReactivePowerMeasurementPoint
    form_class = InputReactivePowerMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_create_form.html"
    status_text = _('The measurement point has been created')


class ReactivePowerMeasurementPointUpdate(
        MeasurementPointSlideInFormMixin, UpdateView):
    model = ReactivePowerMeasurementPoint
    form_class = ReactivePowerMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_update_form.html"
    status_text = _('The measurement point has been updated')


class ReactiveEnergyMeasurementPointCreate(
        MeasurementPointSlideInFormMixin, CreateView):
    model = ReactiveEnergyMeasurementPoint
    form_class = InputReactiveEnergyMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_create_form.html"
    status_text = _('The measurement point has been created')


class ReactiveEnergyMeasurementPointUpdate(
        MeasurementPointSlideInFormMixin, UpdateView):
    model = ReactiveEnergyMeasurementPoint
    form_class = ReactiveEnergyMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_update_form.html"
    status_text = _('The measurement point has been updated')


class PowerFactorMeasurementPointCreate(
        MeasurementPointSlideInFormMixin, CreateView):
    model = PowerFactorMeasurementPoint
    form_class = InputPowerFactorMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_create_form.html"
    status_text = _('The measurement point has been created')


class PowerFactorMeasurementPointUpdate(
        MeasurementPointSlideInFormMixin, UpdateView):
    model = PowerFactorMeasurementPoint
    form_class = PowerFactorMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_update_form.html"
    status_text = _('The measurement point has been updated')


class ProductionMeasurementPointCreate(
        MeasurementPointSlideInFormMixin, CreateView):
    model = ProductionMeasurementPoint
    form_class = InputProductionMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_create_form.html"
    status_text = _('The measurement point has been created')


class ProductionMeasurementPointUpdate(
        MeasurementPointSlideInFormMixin, UpdateView):
    model = ProductionMeasurementPoint
    form_class = ProductionMeasurementPointForm
    template_name = \
        "manage_measurementpoints/measurementpoint_update_form.html"
    status_text = _('The measurement point has been updated')


class TariffPeriodFormSet(SurvivingFormsModelFormSetMixin, BaseInlineFormSet):
    """
    Tariffs attached to a consumption measurement point are stored in a
    horrible complicated relation, namely in terms of number of intermediate
    data series, all needing to be kept up to date.
    """
    def _construct_form(self, i, **kwargs):
        form = super(TariffPeriodFormSet, self)._construct_form(i, **kwargs)
        if i == 0:
            form.fields.pop('valid_from')
            form.instance.valid_from = DATETIME_MIN
        return form

    def clean(self):
        surviving_forms = self.surviving_forms()

        # ChainLinks can validate themselves given a Chain instance.  However,
        # that chain instance is part of the intermediate data series frawned
        # upon in the docstring of this class, and may therefore need to be
        # created on the fly.
        if not self.instance.id and len(surviving_forms) > 0 and \
                surviving_forms[0].is_valid():
            tariff_role = surviving_forms[0].cleaned_data['data_series'].role
            tariff_unit = surviving_forms[0].cleaned_data['data_series'].unit

            self.instance = Chain(
                role=DataRoleField.hidden_tariff_for_role(tariff_role),
                unit=tariff_unit,
                utility_type=self.measurement_point.utility_type)

            for form in surviving_forms:
                form.instance.chain = self.instance

        dates_seen = []
        for form in surviving_forms:
            if 'valid_from' in form.cleaned_data:
                if form.cleaned_data['valid_from'] in dates_seen:
                    raise ValidationError(_('Valid-from dates must be unique'))
                dates_seen.append(form.cleaned_data['valid_from'])

        super(TariffPeriodFormSet, self).clean()

    def save_intermediate_data_series(self):
        surviving_forms = self.surviving_forms()

        if len(surviving_forms) > 0:
            # intermediate data series are needed
            if not self.instance.graph_id:
                # all intermediate data series are missing
                self.instance.graph = Graph.objects.get_or_create(
                    collection=self.measurement_point,
                    role=DataRoleField.HIDDEN,
                    hidden=True)[0]
                self.instance.save()

                cost_graph = Graph.objects.create(
                    collection=self.measurement_point,
                    role=DataRoleField.COST)

                cost = CostCalculation(
                    role=DataRoleField.COST,
                    utility_type=self.measurement_point.utility_type,
                    consumption=self.measurement_point.consumption,
                    index=self.instance,
                    graph=cost_graph)
                cost.full_clean(exclude=['unit'])  # sets the right unit
                cost.save()

        elif len(surviving_forms) == 0 and self.instance.id:
            # intermediate data series are no longer needed
            CostCalculation.objects.filter(
                graph__collection=self.measurement_point,
                utility_type=self.measurement_point.utility_type,
                consumption=self.measurement_point.consumption,
                index=self.instance).delete()
            Graph.objects.filter(
                collection=self.measurement_point,
                role=DataRoleField.COST).delete()

    def save(self, commit=True):
        surviving_forms = self.surviving_forms()

        if commit:
            self.save_intermediate_data_series()
            result = super(TariffPeriodFormSet, self).save(commit=True)
            if len(surviving_forms) == 0 and self.instance.id:
                self.instance.delete()
        else:
            result = super(TariffPeriodFormSet, self).save(commit=False)
            super_save_m2m = self.save_m2m

            def save_m2m():
                self.save_intermediate_data_series()
                super_save_m2m()
                if len(surviving_forms) == 0 and self.instance.id:
                    self.instance.delete()

            self.save_m2m = save_m2m

            return result


class TariffChainLinkInline(InlineFormSet):
    model = ChainLink
    form_class = TariffPeriodForm
    fk_name = 'chain'
    formset_class = TariffPeriodFormSet
    extra = 1

    def construct_formset(self):
        result = super(TariffChainLinkInline, self).construct_formset()
        result.measurement_point = self.view.object
        return result

    def formfield_callback(self, f, **kwargs):
        """
        @precondition: C{self.view.utility_type} is set.
        """
        if f.name == 'data_series':
            kwargs['queryset'] = DataSeries.objects.filter(
                utility_type=self.view.utility_type,
                role__in=DataRoleField.TARIFFS)
            kwargs['initial'] = trackuser.get_customer().\
                get_preffered_tariff(self.view.utility_type)

        return f.formfield(**kwargs)


class TariffPeriodInlineMixin(object):
    def construct_inlines(self):
        inline_formsets = super(
            TariffPeriodInlineMixin, self).construct_inlines()

        # Note: This particular inline instance needs to be instantiated on top
        # of self.object.cost.tariff.subclass_instance rather than self.object.
        if self.object and self.object.cost:
            chain = self.object.cost.tariff.subclass_instance
        else:
            chain = None
        inline_instance = TariffChainLinkInline(
            Chain, self.request, chain, self.kwargs, self)
        inline_formset = inline_instance.construct_formset()
        inline_formsets.append(inline_formset)

        return inline_formsets


class ConsumptionMeasurementPointCreateView(
        MeasurementPointSlideInFormWithInlinesMixin,
        TariffPeriodInlineMixin,
        CreateWithInlinesView):
    form_class = InputConsumptionMeasurementPointForm
    model = ConsumptionMeasurementPoint
    template_name = \
        "manage_measurementpoints/measurementpoint_create_form.html"
    status_text = _('The measurement point has been created')
    utility_type = None

    def get_form_kwargs(self):
        kwargs = super(
            ConsumptionMeasurementPointCreateView, self).get_form_kwargs()
        kwargs['utility_type'] = self.utility_type
        return kwargs


class ConsumptionMeasurementPointUpdateView(
        MeasurementPointSlideInFormWithInlinesMixin,
        TariffPeriodInlineMixin,
        UpdateWithInlinesView):
    form_class = ConsumptionMeasurementPointUpdateForm
    model = ConsumptionMeasurementPoint
    template_name = \
        "manage_measurementpoints/measurementpoint_update_form.html"
    status_text = _('The measurement point has been updated')

    @property
    def utility_type(self):
        """
        Needed by TariffChainLinkInline.formfield_callback
        """
        return self.object.utility_type


class ConsumptionMultiplicationPointCreateView(
        ConsumptionMeasurementPointCreateView):
    form_class = MultiplicationConsumptionMeasurementPointForm
    model = ConsumptionMultiplicationPoint
    template_name = \
        'manage_measurementpoints/multiplication_measurement_point_form.html'


class ConsumptionMultiplicationPointUpdateView(
        ConsumptionMeasurementPointUpdateView):
    form_class = MultiplicationConsumptionMeasurementPointForm
    model = ConsumptionMultiplicationPoint
    template_name = \
        'manage_measurementpoints/multiplication_measurement_point_form.html'


class DistrictHeatingMeasurementPointCreateView(
        ConsumptionMeasurementPointCreateView):
    form_class = DistrictHeatingMeasurementPointCreateForm
    model = DistrictHeatingMeasurementPoint
    template_name = \
        'manage_measurementpoints/district_heating_measurement_point_form.html'
    utility_type = utilitytypes.OPTIONAL_METER_CHOICES.district_heating


class DistrictHeatingMeasurementPointUpdateView(
        ConsumptionMeasurementPointUpdateView):
    form_class = DistrictHeatingMeasurementPointEditForm
    model = DistrictHeatingMeasurementPoint
    template_name = \
        'manage_measurementpoints/district_heating_measurement_point_form.html'
    utility_type = utilitytypes.OPTIONAL_METER_CHOICES.district_heating


@customer_admin_or_error
@json_response
def temperaturepoint_create_form(request):
    """
    Render form for creating TemperatureMeasurementPoint by:

      - display initial form if method is GET
      - display validated form if method is POST and form is invalid (JSON)
      - display success message and MP block if method is POST and form is
        valid (JSON)
    """
    # display initial form if method is GET
    if request.method == 'GET':
        form = InputTemperatureMeasurementPointForm()
        # override json_response by manually returning a HttpResponse.
        return render(
            request, 'manage_measurementpoints/temperature_create_form.html',
            {'form': form})
    else:
        assert request.method == 'POST'
        form = InputTemperatureMeasurementPointForm(request.POST)
        if form.is_valid():
            # display success message and MP block if method is POST and form
            # is valid (JSON)
            measurementpoint = form.save()
            return {
                'success': True,
                'statusText': _('The measurement point has been saved'),
                'html': render_to_string(
                    'manage_measurementpoints/block.html',
                    {'graph_collection': measurementpoint, },
                    RequestContext(request))}
        else:
            # display validated form if method is POST and form is invalid
            # (JSON)
            return {
                'success': False,
                'html': render_to_string(
                    'manage_measurementpoints/temperature_create_form.html',
                    {'form': form},
                    RequestContext(request))}


@customer_admin_or_error
@json_response
def temperature_measurement_point_update_form(request, instance):
    """
    Render form for updating TemperatureMeasurementPoint by:

      - display initial form if method is GET
      - display validated form if method is POST and form is invalid (JSON)
      - display success message and MP block if method is POST and form is
        valid (JSON)
    """

    # display initial form if method is GET
    if request.method == 'GET':
        form = TemperatureMeasurementPointForm(instance=instance)
        # override json_response by manually returning a HttpResponse.
        return render(
            request, 'manage_measurementpoints/temperature_update_form.html',
            {'form': form,
             'delete_prevention_reason':
             instance.get_delete_prevention_reason()})
    else:
        assert request.method == 'POST'
        form = TemperatureMeasurementPointForm(request.POST, instance=instance)
        if form.is_valid():
            # display success message and MP block if method is POST and form
            # is valid (JSON)
            measurementpoint = form.save()
            return {
                'success': True,
                'statusText': _('The measurement point has been saved'),
                'html': render_to_string(
                    'manage_measurementpoints/block.html', {
                        'graph_collection': measurementpoint, },
                    RequestContext(request))}
        else:
            # display validated form if method is POST and form is invalid
            # (JSON)
            return {
                'success': False,
                'html': render_to_string(
                    'manage_measurementpoints/temperature_update_form.html',
                    {'form': form,
                     'delete_prevention_reason':
                     instance.get_delete_prevention_reason()},
                    RequestContext(request))}


class ConsumptionMeasurementPointSummationCreateView(
        ConsumptionMeasurementPointCreateView):
    form_class = ConsumptionMeasurementPointSummationForm
    model = ConsumptionMeasurementPointSummation
    template_name = 'manage_measurementpoints/' \
        'consumption_measurement_point_summation_form.html'


class ConsumptionMeasurementPointSummationUpdateView(
        ConsumptionMeasurementPointUpdateView):
    form_class = ConsumptionMeasurementPointSummationForm
    model = ConsumptionMeasurementPointSummation
    template_name = 'manage_measurementpoints/' \
        'consumption_measurement_point_summation_form.html'
