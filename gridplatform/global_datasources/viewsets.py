# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import django_filters
from rest_framework import viewsets

from . import models
from . import serializers


class GlobalDataSourceFilter(django_filters.FilterSet):
    hardware_id_contains = django_filters.CharFilter(
        name='hardware_id', lookup_type='contains')
    name_contains = django_filters.CharFilter(
        name='name', lookup_type='icontains')

    class Meta:
        model = models.GlobalDataSource
        fields = (
            'name', 'unit', 'hardware_id',
            'hardware_id_contains', 'name_contains'
        )


class GlobalDataSourceViewSet(viewsets.ModelViewSet):
    model = models.GlobalDataSource
    serializer_class = serializers.GlobalDataSourceSerializer
    filter_class = GlobalDataSourceFilter
    filter_fields = GlobalDataSourceFilter.Meta.fields
