# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy
from django.utils.translation import ugettext as _
from django import forms

from legacy.devices.models import Meter, Agent


class MeterModelForm(forms.ModelForm):
    WIBEEE = 0
    WIBEEE_MAX = 1
    DATAHUB = 2
    TYPE_CHOICES = (
        (WIBEEE, _('Wibeee Box')),
        # (WIBEEE_MAX, _('Wibeee Max')),
        (DATAHUB, _('Datahub')),
    )

    meter_type = forms.ChoiceField(
        label=ugettext_lazy('Type'),
        choices=TYPE_CHOICES
    )

    agent = forms.ModelChoiceField(
        label=ugettext_lazy('Agent'),
        queryset=Agent.objects.none, empty_label=None
    )

    class Meta:
        model = Meter
        fields = ['name', 'location', 'hardware_id']

    def __init__(self, *args, **kwargs):
        customer_id = kwargs.pop('customer_id', '')
        super(MeterModelForm, self).__init__(*args, **kwargs)
        self.fields['agent'].queryset = Agent.objects.filter(
            customer_id=customer_id)
