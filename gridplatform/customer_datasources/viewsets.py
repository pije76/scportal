# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import django_filters
from rest_framework.viewsets import ModelViewSet

from gridplatform.encryption.filters import DecryptingSearchFilter
from gridplatform.rest.viewsets import NestedMixin
from . import models
from . import serializers


class CustomerDataSourceFilter(django_filters.FilterSet):
    hardware_id_contains = django_filters.CharFilter(
        name='hardware_id', lookup_type='contains')
    name_contains = DecryptingSearchFilter(name='name_plain')

    class Meta:
        model = models.CustomerDataSource
        fields = (
            'customer', 'unit', 'hardware_id',
            'hardware_id_contains', 'name_contains'
        )


class CustomerDataSourceViewSet(NestedMixin, ModelViewSet):
    model = models.CustomerDataSource
    serializer_class = serializers.CustomerDataSourceSerializer
    filter_class = CustomerDataSourceFilter
    filter_fields = CustomerDataSourceFilter.Meta.fields
