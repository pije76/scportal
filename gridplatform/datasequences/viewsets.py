# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
import rest_framework.reverse

from gridplatform.datasources.viewsets import RawDataViewSet
from gridplatform.datasequences.views import HourlyDataView
from gridplatform.rest.viewsets import NestedMixin

from . import models
from . import serializers


class HourlyEnergyPerVolumeView(NestedMixin, HourlyDataView):
    method_name = 'rate_sequence'

    def get(self, request, datasequence_id=None, format=None):
        datasequence = get_object_or_404(
            models.EnergyPerVolumeDataSequence, pk=datasequence_id)
        timezone = datasequence.customer.timezone
        return self._get(request, datasequence, timezone)


class EnergyPerVolumeDataSequence(viewsets.ModelViewSet):
    model = models.EnergyPerVolumeDataSequence
    serializer_class = serializers.EnergyPerVolumeDataSequence
    filter_fields = ('name', 'customer')

    @action(methods=['GET', 'OPTIONS'])
    def hourly(self, request, pk=None):
        view_fn = HourlyEnergyPerVolumeView.as_view()
        return view_fn(request, datasequence_id=pk)


class EnergyPerVolumePeriod(NestedMixin, viewsets.ModelViewSet):
    model = models.EnergyPerVolumePeriod
    serializer_class = serializers.EnergyPerVolumePeriod

    def create(self, request, *args, **kwargs):
        request.DATA['datasequence'] = rest_framework.reverse.reverse(
            viewname='api:datasequences:energypervolumedatasequence-detail',
            kwargs={
                'pk': kwargs.pop('datasequence_id'),
            }
        )
        return super(EnergyPerVolumePeriod, object).create(
            request, *args, **kwargs)


class NonaccumulationDataSequence(viewsets.ModelViewSet):
    model = models.NonaccumulationDataSequence
    serializer_class = serializers.NonaccumulationDataSequence
    filter_fields = ('name', 'unit', 'customer')

    @action(methods=['GET', 'OPTIONS'])
    def raw_data(self, request, pk=None):
        return RawDataViewSet().list(request, datasource_id=pk)


class NonaccumulationParentMixin(object):
    def create(self, request, *args, **kwargs):
        request.DATA['datasequence'] = rest_framework.reverse.reverse(
            viewname='api:datasequences:nonaccumulationdatasequence-detail',
            kwargs={
                'pk': kwargs.pop('datasequence_id'),
            }
        )
        return super(NonaccumulationParentMixin, object).create(
            request, *args, **kwargs)


class NonaccumulationPeriod(
        NestedMixin, NonaccumulationParentMixin, viewsets.ModelViewSet):
    model = models.NonaccumulationPeriod
    serializer_class = serializers.NonaccumulationPeriod


class NonaccumulationOfflineTolerance(
        NestedMixin, NonaccumulationParentMixin, viewsets.ModelViewSet):
    model = models.NonaccumulationOfflineTolerance
    serializer_class = serializers.NonaccumulationOfflineTolerance
