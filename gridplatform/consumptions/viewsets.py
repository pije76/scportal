# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.decorators import link
import rest_framework.reverse
from rest_framework.response import Response
from rest_framework import status

from gridplatform.datasequences.views import HourlyDataView
from gridplatform.rest.viewsets import NestedMixin

from . import models
from . import serializers


class HourlyConsumptionView(NestedMixin, HourlyDataView):
    method_name = 'development_sequence'

    def get(self, request, consumption_id=None, format=None):
        consumption = get_object_or_404(
            models.Consumption, pk=consumption_id)
        timezone = consumption.customer.timezone
        return self._get(request, consumption, timezone)


class Consumption(viewsets.ModelViewSet):
    model = models.Consumption
    serializer_class = serializers.Consumption
    filter_fields = ('name', 'unit', 'customer')

    @action(methods=['GET', 'OPTIONS'])
    def hourly(self, request, pk=None):
        view_fn = HourlyConsumptionView.as_view()
        return view_fn(request, consumption_id=pk)


class HourlyMainConsumptionView(NestedMixin, HourlyDataView):
    method_name = 'utility_sequence'
    unit_field = 'utility_unit'

    def get(self, request, consumption_id=None, format=None):
        consumption = get_object_or_404(
            models.MainConsumption, pk=consumption_id)
        timezone = consumption.customer.timezone
        return self._get(
            request, consumption, timezone)


class MainConsumption(viewsets.ModelViewSet):
    model = models.MainConsumption
    serializer_class = serializers.MainConsumption
    filter_fields = ('name', 'customer')

    @link()
    def hourly(self, request, pk=None):
        view_fn = HourlyMainConsumptionView.as_view()
        return view_fn(request, consumption_id=pk)


class HourlyConsumptionGroup(NestedMixin, HourlyDataView):
    method_name = 'utility_sequence'
    unit_field = 'utility_unit'

    def get(self, request, consumption_id=None, format=None):
        consumption = get_object_or_404(
            models.ConsumptionGroup, pk=consumption_id)
        timezone = consumption.customer.timezone
        return self._get(
            request, consumption, timezone)


class ConsumptionGroup(viewsets.ModelViewSet):
    model = models.ConsumptionGroup
    serializer_class = serializers.ConsumptionGroup
    filter_fields = ('name', 'customer')

    @link()
    def hourly(self, request, pk=None):
        view_fn = HourlyConsumptionGroup.as_view()
        return view_fn(request, consumption_id=pk)


class ConsumptionParentMixin(object):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)

        if serializer.is_valid():

            self.pre_save(serializer.object)
            serializer.object.datasequence_id = kwargs.pop('datasequence_id')
            self.object = serializer.save(force_insert=True)

            self.post_save(self.object, created=True)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NonpulsePeriod(
        NestedMixin, ConsumptionParentMixin, viewsets.ModelViewSet):
    model = models.NonpulsePeriod
    serializer_class = serializers.NonpulsePeriod


class PulsePeriod(NestedMixin, ConsumptionParentMixin, viewsets.ModelViewSet):
    model = models.PulsePeriod
    serializer_class = serializers.PulsePeriod


class SingleValuePeriod(
        NestedMixin, ConsumptionParentMixin, viewsets.ModelViewSet):
    model = models.SingleValuePeriod
    serializer_class = serializers.SingleValuePeriod


class OfflineTolerance(
        NestedMixin, ConsumptionParentMixin, viewsets.ModelViewSet):
    model = models.OfflineTolerance
    serializer_class = serializers.OfflineTolerance
