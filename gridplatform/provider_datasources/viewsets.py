# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import django_filters
from rest_framework import viewsets

from . import models
from . import serializers


class ProviderDataSourceFilter(django_filters.FilterSet):
    hardware_id_contains = django_filters.CharFilter(
        name='hardware_id', lookup_type='contains')

    class Meta:
        model = models.ProviderDataSource
        fields = (
            'unit', 'hardware_id',
            'hardware_id_contains',
        )


class ProviderDataSourceViewSet(viewsets.ModelViewSet):
    model = models.ProviderDataSource
    serializer_class = serializers.ProviderDataSourceSerializer
    filter_class = ProviderDataSourceFilter
    filter_fields = ProviderDataSourceFilter.Meta.fields
