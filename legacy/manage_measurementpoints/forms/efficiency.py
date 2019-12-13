# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.models import Collection
from gridplatform.datasequences.models import NonaccumulationDataSequence  # noqa
from legacy.datasequence_adapters.models import NonaccumulationAdapter
from legacy.efficiencymeasurementpoints.models import EfficiencyMeasurementPoint  # noqa

from .measurementpointform import MeasurementPointForm


class EfficiencyMeasurementPointForm(MeasurementPointForm):
    """
    A C{EfficiencyMeasurementPointForm} sets properties on a
    L{EfficiencyMeasurementPoint} that can be both set when creating and when
    updating.
    """
    class Meta:
        model = EfficiencyMeasurementPoint
        fields = ('name', 'parent',
                  'hidden_on_details_page', 'hidden_on_reports_page',
                  'comment', 'image')
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(EfficiencyMeasurementPointForm, self).__init__(*args, **kwargs)
        self.fields['parent'].queryset = \
            Collection.objects.filter(
                role=Collection.GROUP,
                customer=trackuser.get_customer())

    def _get_edit_headline_display(self):
        return _(u'Edit Efficiency Measurement Point')


class InputEfficiencyMeasurementPointForm(EfficiencyMeasurementPointForm):
    """
    An C{InputEfficiencyMeasurementPointForm} is a
    L{EfficiencyMeasurementPointForm}, that in addition also sets properties
    that can only be set when creating a L{EfficiencyMeasurementPointForm}.
    """
    input_configuration = forms.ModelChoiceField(
        required=True,
        queryset=NonaccumulationAdapter.objects.none())

    class ProxyMeta:
        fields = ('input_configuration', )

    def __init__(self, *args, **kwargs):
        super(InputEfficiencyMeasurementPointForm, self).__init__(
            *args, **kwargs)

        self.fields['input_configuration'].queryset = \
            EfficiencyMeasurementPoint.get_input_configuration_choices()

    def _get_new_headline_display(self):
        return _(u'New Efficiency Measurement Point')
