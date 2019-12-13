# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
import rest_framework.reverse

from gridplatform.datasequences.views import HourlyDataView
from gridplatform.rest.viewsets import NestedMixin

from . import models
from . import serializers


class HourlyView(NestedMixin, HourlyDataView):
    method_name = 'value_sequence'

    def get(self, request, datasequence_id=None, format=None):
        datasequence = get_object_or_404(
            models.CostCompensation, pk=datasequence_id)
        timezone = datasequence.customer.timezone
        return self._get(request, datasequence, timezone)


class CostCompensation(NestedMixin, viewsets.ModelViewSet):
    model = models.CostCompensation
    serializer_class = serializers.CostCompensation
    filter_fields = ('name', 'customer')

    @action(methods=['GET', 'OPTIONS'])
    def hourly(self, request, pk=None):
        view_fn = HourlyView.as_view()
        return view_fn(request, datasequence_id=pk)


class FixedCompensationPeriod(NestedMixin, viewsets.ModelViewSet):
    model = models.FixedCompensationPeriod
    serializer_class = serializers.FixedCompensationPeriod

    def create(self, request, *args, **kwargs):
        request.DATA['datasequence'] = rest_framework.reverse.reverse(
            viewname='api:cost_compensations:costcompensation-detail',
            kwargs={
                'pk': kwargs.pop('datasequence_id'),
            }
        )
        return super(FixedCompensationPeriod, self).create(
            request, *args, **kwargs)
