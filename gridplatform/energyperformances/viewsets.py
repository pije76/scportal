# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import link
from rest_framework.response import Response
import rest_framework.reverse

from . import models
from . import serializers


def _parse_date(date_string):
    return datetime.datetime.strptime(date_string, '%Y-%m-%d').date()

def _compute(model, request, pk=None, format=None):
    performance = get_object_or_404(model, pk=pk)
    tz = performance.customer.timezone
    day = datetime.timedelta(days=1)
    try:
        from_date = _parse_date(request.GET['from_date'])
        to_date = _parse_date(request.GET['to_date'])
    except (KeyError, ValueError):
        from_date = datetime.datetime.now(tz=tz).date()
        to_date = from_date
    from_timestamp = tz.localize(
        datetime.datetime.combine(from_date, datetime.time()))
    to_timestamp = tz.localize(
        datetime.datetime.combine(
            to_date + day, datetime.time()))
    result = performance.compute_performance(from_timestamp, to_timestamp)
    if result is not None:
        num = float(performance.unit_converter.extract_value(result))
    else:
        num = None
    delta = to_date - from_date
    previous_period_end = from_date - day
    previous_period_start = previous_period_end - delta
    next_period_start = to_date + day
    next_period_end = next_period_start + delta
    return Response({
        'previous': '%s?from_date=%s&to_date=%s' % (
            rest_framework.reverse.reverse(
                'api:energyperformances:productionenergyperformance-compute',  # noqa
                args=[pk], request=request),
            previous_period_start,
            previous_period_end),
        'next': '%s?from_date=%s&to_date=%s' % (
            rest_framework.reverse.reverse(
                'api:energyperformances:productionenergyperformance-compute',  # noqa
                args=[pk], request=request),
            next_period_start,
            next_period_end),
        'from_date': from_date,
        'to_date': to_date,
        'unit': performance.unit,
        'display_unit': performance.unit_converter.get_display_unit(),
        'value': num,
    })


class ProductionEnergyPerformance(viewsets.ModelViewSet):
    model = models.ProductionEnergyPerformance
    serializer_class = serializers.ProductionEnergyPerformance
    filter_fields = ('name', 'customer')

    @link()
    def compute(self, request, pk=None, format=None):
        return _compute(self.model, request, pk, format)


class TimeEnergyPerformance(viewsets.ModelViewSet):
    model = models.TimeEnergyPerformance
    serializer_class = serializers.TimeEnergyPerformance
    filter_fields = ('name', 'customer')

    @link()
    def compute(self, request, pk=None, format=None):
        return _compute(self.model, request, pk, format)
