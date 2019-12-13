# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from gridplatform import trackuser
from legacy.measurementpoints.proxies import CurrentMeasurementPoint
from legacy.measurementpoints.models import Collection

from .measurementpointform import MeasurementPointForm

from gridplatform.datasequences.models import NonaccumulationDataSequence  # noqa


class CurrentMeasurementPointForm(MeasurementPointForm):
    """
    A C{CurrentMeasurementPointForm} sets properties on a
    L{CurrentMeasurementPoint} that can be both set when creating and when
    updating.
    """
    class Meta:
        model = CurrentMeasurementPoint
        fields = ('name', 'parent',
                  'hidden_on_details_page', 'hidden_on_reports_page',
                  'comment', 'image')
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CurrentMeasurementPointForm, self).__init__(*args, **kwargs)
        self.fields['parent'].queryset = \
            Collection.objects.filter(
                role=Collection.GROUP,
                customer=trackuser.get_customer())

    def _get_edit_headline_display(self):
        return _(u'Edit Current Measurement Point')


class InputCurrentMeasurementPointForm(CurrentMeasurementPointForm):
    """
    An C{InputCurrentMeasurementPointForm} is a
    L{CurrentMeasurementPointForm}, that in addition also sets properties
    that can only be set when creating a L{CurrentMeasurementPointForm}.
    """
    input_configuration = forms.ModelChoiceField(
        required=True,
        queryset=NonaccumulationDataSequence.objects.none())

    class ProxyMeta:
        fields = ('input_configuration', )

    def __init__(self, *args, **kwargs):
        super(InputCurrentMeasurementPointForm, self).__init__(
            *args, **kwargs)

        self.fields['input_configuration'].queryset = \
            CurrentMeasurementPoint.get_input_configuration_choices()

    def _get_new_headline_display(self):
        return _(u'New Current Measurement Point')
