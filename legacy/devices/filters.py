from __future__ import absolute_import

import django_filters

from .models import RawData


class RawDataFilter(django_filters.FilterSet):
    value_gte = django_filters.NumberFilter(
        name='value', lookup_type='gte')
    value_lte = django_filters.NumberFilter(
        name='value', lookup_type='lte')
    timestamp_gte = django_filters.DateTimeFilter(
        name='timestamp', lookup_type='gte')
    timestamp_lte = django_filters.DateTimeFilter(
        name='timestamp', lookup_type='lte')

    class Meta:
        model = RawData
        fields = [
            'physicalinput',
            'value_gte', 'value_lte',
            'timestamp_gte', 'timestamp_lte'
        ]
