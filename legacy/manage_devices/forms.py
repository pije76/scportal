# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from legacy.measurementpoints.models import Collection
from gridplatform.utils import units
from gridplatform.consumptions.models import Consumption
from gridplatform.consumptions.models import PulsePeriod as ConsumptionPulsePeriod  # noqa
from gridplatform.productions.models import Production
from gridplatform.productions.models import PulsePeriod as ProductionPulsePeriod  # noqa
from legacy.devices.models import Agent
from legacy.devices.models import Meter


class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ('location', 'no_longer_in_use')
        localized_fields = '__all__'


class MeterForm(forms.ModelForm):
    class Meta:
        model = Meter
        fields = ('name', 'location', 'relay_enabled')
        localized_fields = '__all__'

    def clean(self):
        # If relay is disabled, make sure that no one uses it.
        if not self.cleaned_data.get('relay_enabled'):
            mps = Collection.objects.filter(relay=self.instance)
            reason = ""
            for mp in mps:
                if reason == "":
                    reason = mp.name_plain
                else:
                    reason += ", " + mp.name_plain
            if reason:
                raise ValidationError(
                    _('Relay cannot be disabled because it is used by '
                        + unicode(reason)))
        return self.cleaned_data


RELAY_CHOICES = (
    ('on', _('On')),
    ('off', _('Off')),
)


class RelayForm(forms.Form):
    relay_state = forms.ChoiceField(required=True, choices=RELAY_CHOICES)


class ElectricityConsumptionForm(forms.ModelForm):
    class Meta:
        model = Consumption
        fields = ('name', )
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ElectricityConsumptionForm, self).__init__(
            *args, **kwargs)
        self.instance.unit = 'milliwatt*hour'


class WaterConsumptionForm(forms.ModelForm):
    class Meta:
        model = Consumption
        fields = ('name', )
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(WaterConsumptionForm, self).__init__(
            *args, **kwargs)
        self.instance.unit = 'milliliter'


class DistrictHeatingConsumptionForm(forms.ModelForm):
    class Meta:
        model = Consumption
        fields = ('name', )
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(DistrictHeatingConsumptionForm, self).__init__(
            *args, **kwargs)
        self.instance.unit = 'milliwatt*hour'


class GasConsumptionForm(forms.ModelForm):
    class Meta:
        model = Consumption
        fields = ('name', )
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(GasConsumptionForm, self).__init__(
            *args, **kwargs)
        self.instance.unit = 'milliliter'


class OilConsumptionForm(forms.ModelForm):
    class Meta:
        model = Consumption
        fields = ('name', )
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(OilConsumptionForm, self).__init__(
            *args, **kwargs)
        self.instance.unit = 'milliliter'


class ProductionForm(forms.ModelForm):
    class Meta:
        model = Production
        fields = ('name', )
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        unit = kwargs.pop('unit', None)
        super(ProductionForm, self).__init__(
            *args, **kwargs)
        if unit:
            self.instance.unit = unit


class InputPeriodFormBase(forms.ModelForm):
    class Meta:
        model = ConsumptionPulsePeriod
        fields = ('from_timestamp', 'to_timestamp', 'pulse_quantity',
                  'output_quantity', 'output_unit')
        localized_fields = '__all__'

    def clean(self):
        self.instance._clean_overlapping_periods = False
        return super(InputPeriodFormBase, self).clean()


class EnergyInputPeriodForm(InputPeriodFormBase):
    output_unit = forms.ChoiceField(
        choices=BLANK_CHOICE_DASH + list(units.ENERGY_CHOICES))


class VolumeInputPeriodForm(InputPeriodFormBase):
    output_unit = forms.ChoiceField(
        choices=BLANK_CHOICE_DASH + list(units.VOLUME_CHOICES))


class ProductionInputPeriodForm(InputPeriodFormBase):
    class Meta(InputPeriodFormBase.Meta):
        model = ProductionPulsePeriod
        fields = ('from_timestamp', 'to_timestamp', 'pulse_quantity',
                  'output_quantity')
