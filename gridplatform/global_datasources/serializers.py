# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.datasources.serializers import DataSourceSerializerBase
from gridplatform.datasources.serializers import RawDataWithUnitSerializer as RawDataWithUnitSerializerBase  # noqa

from gridplatform.rest import serializers
from .models import GlobalDataSource


class GlobalDataSourceSerializer(DataSourceSerializerBase):
    raw_data = serializers.HyperlinkedIdentityField(
        view_name='api:datasources:rawdata-list')

    class Meta:
        model = GlobalDataSource
        fields = (
            'url', 'id', 'name', 'unit', 'display_unit', 'country',
            'hardware_id', 'raw_data'
        )
