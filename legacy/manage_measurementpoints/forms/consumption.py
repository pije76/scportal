# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from gridplatform.consumptions.models import Consumption
from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from gridplatform.trackuser import get_customer
from gridplatform.utils import utilitytypes
from legacy.datasequence_adapters.models import ConsumptionAccumulationAdapter
from legacy.devices.models import Meter
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import DataSeries

from .measurementpointform import MeasurementPointForm


class ConsumptionMeasurementPointForm(MeasurementPointForm):
    """
    Abstract base class for consumption measurement point forms.

    The abstract protected methods
    L{MeasurementPointForm._get_new_headline_display()} and
    L{MeasurementPointForm._get_edit_headline_display()} methods are
    implemented by fanned out to the abstract protected methods
    C{_get_new_UTILITY_TYPE_headline_display()} and
    C{_get_edit_UTILITY_TYPE_headline_display()} for each utility type.

    @invariant: C{self.instance.utility_type is not None}.

    @invariant: C{self.instance.utility_type} is in
    C{utilitytypes.METER_CHOICES}.
    """

    heating_degree_days = forms.ModelChoiceField(
        queryset=DataSeries.objects.none(),
        required=False)

    standard_heating_degree_days = forms.ModelChoiceField(
        queryset=DataSeries.objects.none(),
        required=False)

    employees = forms.ModelChoiceField(
        queryset=DataSeries.objects.none(),
        required=False)

    area = forms.ModelChoiceField(
        queryset=DataSeries.objects.none(),
        required=False)

    co2 = forms.ModelChoiceField(
        queryset=DataSeries.objects.none(),
        required=False)

    show_rate = forms.BooleanField(
        initial=False, required=False)

    class Meta:
        model = ConsumptionMeasurementPoint
        fields = ('name', 'parent', 'billing_meter_number',
                  'billing_installation_number', 'gauge_lower_threshold',
                  'gauge_upper_threshold', 'gauge_max', 'gauge_min',
                  'gauge_colours', 'relay', 'gauge_preferred_unit',
                  'hidden_on_details_page', 'hidden_on_reports_page',
                  'comment', 'image')
        localized_fields = '__all__'

    class ProxyMeta(MeasurementPointForm.ProxyMeta):
        fields = ('heating_degree_days', 'standard_heating_degree_days',
                  'employees', 'area', 'co2')

    def __init__(self, *args, **kwargs):
        """
        @keyword utility_type: If instance is not given, this keyword argument
        must be given.  It should be one of the integer values defined in
        L{utilitytypes.METER_CHOICES}.
        """
        utility_type = kwargs.pop(
            'utility_type', None)
        super(ConsumptionMeasurementPointForm, self).__init__(*args, **kwargs)
        if utility_type is not None and self.instance.utility_type is None:
            self.instance.utility_type = utility_type

        self.fields['parent'].queryset = \
            Collection.objects.filter(
                role=Collection.GROUP,
                customer=trackuser.get_customer())

        self.fields['relay'].queryset = \
            Meter.objects.filter(
                customer=trackuser.get_customer(), relay_enabled=True)

        self.fields["heating_degree_days"].queryset = \
            DataSeries.objects.filter(
                role=DataRoleField.HEATING_DEGREE_DAYS,
                customer=trackuser.get_customer())

        self.fields["standard_heating_degree_days"].queryset = \
            DataSeries.objects.filter(
                role=DataRoleField.STANDARD_HEATING_DEGREE_DAYS).filter(
                Q(customer=trackuser.get_customer()) |
                Q(customer__isnull=True))

        self.fields["employees"].queryset = \
            DataSeries.objects.filter(
                role=DataRoleField.EMPLOYEES,
                customer=trackuser.get_customer())

        self.fields["area"].queryset = \
            DataSeries.objects.filter(
                role=DataRoleField.AREA,
                customer=trackuser.get_customer())

        self.fields['co2'].queryset = DataSeries.objects.filter(
            role=DataRoleField.CO2_QUOTIENT,
            utility_type=self.instance.utility_type)

        # populate form fields from instance, which cannot
        # be handled by ProxyMeta.fields
        if self.instance.id:
            self.initial['show_rate'] = self.instance.rate is not None

        # Set the initial value of co2 to the first co2 index found
        elif self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.electricity:
            co2 = DataSeries.objects.filter(
                role=DataRoleField.CO2_QUOTIENT,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
            if co2:
                self.initial['co2'] = co2[0]

        self.__assert_invariants()

    def clean(self):
        """
        Forward proxy properties to instance.
        """
        self.instance.enable_rate = \
            self.cleaned_data['show_rate']

        self.cleaned_data['gauge_min'] = 0

        super(ConsumptionMeasurementPointForm, self).clean()

        return self.cleaned_data

    def __assert_invariants(self):
        assert self.instance.utility_type in [
            db_value for db_value, dummy in
            utilitytypes.OPTIONAL_METER_CHOICES]

    def _get_new_headline_display(self):
        """
        Implementation of L{MeasurementPointForm._get_new_headline_display()}.
        """
        self.__assert_invariants()

        if self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.electricity:
            return self._get_new_electricity_headline_display()
        elif self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.water:
            return self._get_new_water_headline_display()
        elif self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.gas:
            return self._get_new_gas_headline_display()
        elif self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.district_heating:
            return self._get_new_heat_headline_display()
        elif self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.oil:
            return self._get_new_oil_headline_display()
        assert False, 'unreachable'

    def _get_new_electricity_headline_display(self):
        raise NotImplementedError()

    def _get_new_water_headline_display(self):
        raise NotImplementedError()

    def _get_new_gas_headline_display(self):
        raise NotImplementedError()

    def _get_new_heat_headline_display(self):
        raise NotImplementedError()

    def _get_new_oil_headline_display(self):
        raise NotImplementedError()

    def _get_edit_headline_display(self):
        """
        Implementation of L{MeasurementPointForm._get_edit_headline_display()}
        """
        self.__assert_invariants()

        if self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.electricity:
            return self._get_edit_electricity_headline_display()
        elif self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.water:
            return self._get_edit_water_headline_display()
        elif self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.gas:
            return self._get_edit_gas_headline_display()
        elif self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.district_heating:
            return self._get_edit_heat_headline_display()
        elif self.instance.utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.oil:
            return self._get_edit_oil_headline_display()
        assert False, 'unreachable'

    def _get_edit_electricity_headline_display(self):
        raise NotImplementedError()

    def _get_edit_water_headline_display(self):
        raise NotImplementedError()

    def _get_edit_gas_headline_display(self):
        raise NotImplementedError()

    def _get_edit_heat_headline_display(self):
        raise NotImplementedError()

    def _get_edit_oil_headline_display(self):
        raise NotImplementedError()


class ConsumptionMeasurementPointUpdateForm(ConsumptionMeasurementPointForm):
    def _get_edit_electricity_headline_display(self):
        return _(u'Edit Electricity Measurement Point')

    def _get_edit_water_headline_display(self):
        return _(u'Edit Water Measurement Point')

    def _get_edit_gas_headline_display(self):
        return _(u'Edit Gas Measurement Point')

    def _get_edit_heat_headline_display(self):
        return _(u'Edit Heat Measurement Point')

    def _get_edit_oil_headline_display(self):
        return _(u'Edit Oil Measurement Point')


class InputConsumptionMeasurementPointForm(ConsumptionMeasurementPointForm):

    consumption_input = forms.ModelChoiceField(
        queryset=Consumption.objects.none(), required=True)

    class Meta(ConsumptionMeasurementPointForm.Meta):
        exclude = ('gauge_lower_threshold', 'gauge_upper_threshold',
                   'gauge_max', 'gauge_min', 'gauge_colours',
                   'gauge_preferred_unit')

    class ProxyMeta(ConsumptionMeasurementPointForm.ProxyMeta):
        fields = ConsumptionMeasurementPointForm.ProxyMeta.fields + \
            ('consumption_input',)

    def __init__(self, *args, **kwargs):
        super(InputConsumptionMeasurementPointForm, self).__init__(
            *args, **kwargs)

        self.fields['consumption_input'].queryset = \
            ConsumptionAccumulationAdapter.objects.filter(
                utility_type=self.instance.utility_type,
                customer=get_customer())

    def _get_new_electricity_headline_display(self):
        return _(u'New Electricity Measurement Point')

    def _get_new_water_headline_display(self):
        return _(u'New Water Measurement Point')

    def _get_new_gas_headline_display(self):
        return _(u'New Gas Measurement Point')

    def _get_new_heat_headline_display(self):
        return _(u'New Heat Measurement Point')

    def _get_new_oil_headline_display(self):
        return _(u'New Oil Measurement Point')
