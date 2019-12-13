from django import forms

from gridplatform.utils import units
from gridplatform.utils.forms import TimePeriodModelForm

from . import models


class CostCompensationForm(forms.ModelForm):
    unit = forms.ChoiceField(choices=units.COST_COMPENSATION_CHOICES)

    class Meta:
        model = models.CostCompensation
        fields = ('name', 'unit')


class FixedCompensationPeriodForm(TimePeriodModelForm):
    class Meta:
        model = models.FixedCompensationPeriod
        fields = (
            'from_date', 'from_hour', 'to_date', 'to_hour', 'value', 'unit')
