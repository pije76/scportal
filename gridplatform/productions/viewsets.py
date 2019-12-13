# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.decorators import link
import rest_framework.reverse

from gridplatform.datasequences.views import HourlyDataView
from gridplatform.rest.viewsets import NestedMixin

from . import models
from . import serializers


class HourlyProductionView(NestedMixin, HourlyDataView):
    method_name = 'development_sequence'

    def get(self, request, production_id=None, format=None):
        production = get_object_or_404(models.Production, pk=production_id)
        timezone = production.customer.timezone
        return self._get(request, production, timezone)


class Production(viewsets.ModelViewSet):
    model = models.Production
    serializer_class = serializers.Production
    filter_fields = ('name', 'unit', 'customer')

    @action(methods=['GET', 'OPTIONS'])
    def hourly(self, request, pk=None):
        view_fn = HourlyProductionView.as_view()
        return view_fn(request, production_id=pk)


class HourlyProductionGroupView(NestedMixin, HourlyDataView):
    method_name = 'production_sequence'

    def get(self, request, production_id=None, format=None):
        production = get_object_or_404(
            models.ProductionGroup, pk=production_id)
        timezone = production.customer.timezone
        return self._get(request, production, timezone)


class ProductionGroup(viewsets.ModelViewSet):
    model = models.ProductionGroup
    serializer_class = serializers.ProductionGroup
    filter_fields = ('name', 'customer')

    @link()
    def hourly(self, request, pk=None):
        view_fn = HourlyProductionGroupView.as_view()
        return view_fn(request, production_id=pk)


class ProductionParentMixin(object):
    def create(self, request, *args, **kwargs):
        request.DATA['datasequence'] = rest_framework.reverse.reverse(
            viewname='api:productions:production-detail',
            kwargs={
                'pk': kwargs.pop('datasequence_id'),
            }
        )
        return super(ProductionParentMixin, self).create(
            request, *args, **kwargs)


class NonpulsePeriod(
        NestedMixin, ProductionParentMixin, viewsets.ModelViewSet):
    model = models.NonpulsePeriod
    serializer_class = serializers.NonpulsePeriod


class PulsePeriod(NestedMixin, ProductionParentMixin, viewsets.ModelViewSet):
    model = models.PulsePeriod
    serializer_class = serializers.PulsePeriod


class SingleValuePeriod(
        NestedMixin, ProductionParentMixin, viewsets.ModelViewSet):
    model = models.SingleValuePeriod
    serializer_class = serializers.SingleValuePeriod


class OfflineTolerance(
        NestedMixin, ProductionParentMixin, viewsets.ModelViewSet):
    model = models.OfflineTolerance
    serializer_class = serializers.OfflineTolerance
