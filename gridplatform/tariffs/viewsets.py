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
        datasequence = get_object_or_404(models.Tariff, pk=datasequence_id)
        timezone = datasequence.customer.timezone
        return self._get(request, datasequence, timezone)


class EnergyTariff(viewsets.ModelViewSet):
    model = models.EnergyTariff
    serializer_class = serializers.EnergyTariff
    filter_fields = ('name', 'customer')

    @action(methods=['GET', 'OPTIONS'])
    def hourly(self, request, pk=None):
        view_fn = HourlyView.as_view()
        return view_fn(request, datasequence_id=pk)


class VolumeTariff(viewsets.ModelViewSet):
    model = models.VolumeTariff
    serializer_class = serializers.VolumeTariff
    filter_fields = ('name', 'customer')

    @action(methods=['GET', 'OPTIONS'])
    def hourly(self, request, pk=None):
        view_fn = HourlyView.as_view()
        return view_fn(request, datasequence_id=pk)


class TariffParentMixin(object):
    def create(self, request, *args, **kwargs):
        request.DATA['datasequence'] = rest_framework.reverse.reverse(
            viewname='api:tariff:tariff-detail',
            kwargs={
                'pk': kwargs.pop('datasequence_id'),
            }
        )
        return super(TariffParentMixin, self).create(
            request, *args, **kwargs)


class FixedPricePeriod(NestedMixin, TariffParentMixin, viewsets.ModelViewSet):
    model = models.FixedPricePeriod
    serializer_class = serializers.FixedPricePeriod


class SpotPricePeriod(NestedMixin, TariffParentMixin, viewsets.ModelViewSet):
    model = models.SpotPricePeriod
    serializer_class = serializers.SpotPricePeriod
