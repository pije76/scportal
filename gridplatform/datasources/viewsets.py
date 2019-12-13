# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
import pytz

from gridplatform.rest.viewsets import NestedMixin
from gridplatform.utils.paginator import parse_date_or_404
from gridplatform.utils.serializers import PointSampleSerializer
from gridplatform.utils.unitconversion import PhysicalQuantity
from rest_framework.templatetags.rest_framework import replace_query_param

from . import models
from . import serializers


def _unit_check(unit, expected_unit):
    if PhysicalQuantity.compatible_units(unit, expected_unit):
        return {}
    else:
        return {
            'unit': [b'unit %s is not compatible with data source unit %s' % (
                unit, expected_unit)],
        }


class RawDataViewSetBase(viewsets.ModelViewSet):
    method_name = 'raw_sequence'

    def list(self, request, *args, **kwargs):
        if 'datasource_id' in kwargs:
            # DataSource instance
            owner_id = kwargs.get('datasource_id')
            owner_model = getattr(self.model, 'datasource').field.rel.to
        else:
            # NonaccumulationDataSequence
            owner_id = kwargs.get('datasequence_id')
            owner_model = models.NonaccumulationDataSequence
        owner = get_object_or_404(owner_model, pk=owner_id)
        # NOTE: Same view used by both provider and customer users, so
        # get_customer() is not well-defined.  Also same view is used for both
        # global as well as customer data sources' raw data, so fetching "the
        # customer" via some relation is not possible either.
        timezone = pytz.utc
        return self._list(request, owner, timezone)

    def _list(self, request, owner, timezone):
        unit = owner.unit
        date_query_param = request.QUERY_PARAMS.get('date')
        date = date_query_param or timezone.normalize(
            datetime.datetime.now(timezone)).date()
        date = parse_date_or_404(date)
        from_timestamp = timezone.localize(
            datetime.datetime.combine(date, datetime.time()))
        to_timestamp = timezone.localize(
            datetime.datetime.combine(
                date + datetime.timedelta(days=1), datetime.time()))
        method = getattr(owner, self.method_name)
        data = method(from_timestamp, to_timestamp)
        serializer = PointSampleSerializer(
            data, many=True, context={'unit': unit})

        base_url = request and request.build_absolute_uri() or ''
        next_date = owner.next_valid_date(date, timezone)
        if next_date:
            next_url = replace_query_param(base_url, 'date', next_date)
        else:
            next_url = None
        previous_date = owner.previous_valid_date(date, timezone)
        if previous_date:
            previous_url = replace_query_param(base_url, 'date', previous_date)
        else:
            previous_url = None
        return Response({
            'next': next_url,
            'previous': previous_url,
            'results': serializer.data,
        })

    def create(self, request, *args, **kwargs):
        bulk = isinstance(request.DATA, list)
        if bulk:
            return self._bulk_create(request, *args, **kwargs)
        else:
            return self._create(request, *args, **kwargs)

    def _create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.DATA,
            files=request.FILES,
            context={'request': request})

        if serializer.is_valid():
            datasource = \
                self.model._meta.get_field('datasource').rel.to.objects.get(
                    id=request.parser_context['kwargs']['datasource_id'])
            errors = _unit_check(request.DATA['unit'], datasource.unit)
            if errors:
                serializer._errors = errors
            else:
                serializer.save(force_insert=True)
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data, status=status.HTTP_201_CREATED,
                    headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _bulk_create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.DATA,
            files=request.FILES,
            many=True)
        if serializer.is_valid():
            datasource = \
                self.model._meta.get_field('datasource').rel.to.objects.get(
                    id=request.parser_context['kwargs']['datasource_id'])
            errors = []
            for data in request.DATA:
                errors.append(_unit_check(data['unit'], datasource.unit))
            if any(errors):
                serializer._errors = errors
            else:
                for obj in serializer.object:
                    obj.datasource_id = datasource.id
                serializer.save(force_insert=True)
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data, status=status.HTTP_201_CREATED,
                    headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def metadata(self, request):
        res = super(RawDataViewSetBase, self).metadata(request)
        res['bulk_actions'] = ['POST']
        return res


class RawDataViewSet(NestedMixin, RawDataViewSetBase):
    model = models.RawData
    serializer_class = serializers.RawDataWithUnitSerializer


class DataSourceViewSet(NestedMixin, viewsets.ModelViewSet):
    model = models.DataSource
    serializer_class = serializers.DataSourceSerializer
