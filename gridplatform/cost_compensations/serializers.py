# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.rest import serializers
from gridplatform.utils import units

from . import models


class CostCompensation(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    periods = serializers.HyperlinkedRelatedField(
        source='period_set', many=True, read_only=True)
    hourly = serializers.SerializerMethodField('get_hourly')
    fixed_compensation_periods = serializers.HyperlinkedIdentityField(
        view_name='api:cost_compensations:fixedcompensationperiod-list')
    unit = serializers.SerializerMethodField('get_unit')
    display_unit = serializers.SerializerMethodField('get_display_unit')

    class Meta:
        model = models.CostCompensation
        fields = ('url', 'id', 'name', 'unit', 'display_unit', 'customer',
                  'periods', 'fixed_compensation_periods', 'hourly')

    def get_unit(self, obj):
        return obj.unit

    def get_display_unit(self, obj):
        return units.UNIT_DISPLAY_NAMES[obj.unit]

    def get_hourly(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:cost_compensations:costcompensation-hourly',
            kwargs={'pk': obj.id})


class FixedCompensationPeriod(serializers.DefaultSerializer):
    display_unit = serializers.SerializerMethodField('get_display_unit')

    class Meta:
        model = models.FixedCompensationPeriod
        fields = (
            'url', 'id', 'from_timestamp', 'to_timestamp', 'datasequence',
            'value', 'unit', 'display_unit')
        read_only_fields = ('datasequence',)

    def get_display_unit(self, obj):
        return units.UNIT_DISPLAY_NAMES[obj.unit]
