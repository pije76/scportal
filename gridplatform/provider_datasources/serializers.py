# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.datasources.serializers import DataSourceSerializerBase

from gridplatform.rest import serializers
from .models import ProviderDataSource


class ProviderDataSourceSerializer(DataSourceSerializerBase):
    raw_data = serializers.HyperlinkedIdentityField(
        view_name='api:datasources:rawdata-list')

    class Meta:
        model = ProviderDataSource
        fields = ('url', 'id', 'unit', 'display_unit',
                  'hardware_id', 'raw_data')
