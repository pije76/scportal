# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.datasources.serializers import DataSourceSerializerBase

from gridplatform.rest import serializers
from .models import CustomerDataSource


class CustomerDataSourceSerializer(DataSourceSerializerBase):
    name = serializers.CharField(source='name_plain')
    raw_data = serializers.HyperlinkedIdentityField(
        view_name='api:datasources:rawdata-list')

    class Meta:
        model = CustomerDataSource
        fields = (
            'url', 'id', 'customer', 'name', 'unit', 'display_unit',
            'hardware_id', 'raw_data'
        )
