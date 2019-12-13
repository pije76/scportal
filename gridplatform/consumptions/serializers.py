# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.rest import serializers
from gridplatform.utils import units

from . import models


class Consumption(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    periods = serializers.HyperlinkedRelatedField(
        source='period_set', many=True, read_only=True)
    hourly = serializers.SerializerMethodField('get_hourly')
    nonpulse_periods = serializers.HyperlinkedIdentityField(
        view_name='api:consumptions:nonpulseperiod-list')
    pulse_periods = serializers.HyperlinkedIdentityField(
        view_name='api:consumptions:pulseperiod-list')
    single_value_periods = serializers.HyperlinkedIdentityField(
        view_name='api:consumptions:singlevalueperiod-list')
    offlinetolerance = serializers.HyperlinkedIdentityField(
        view_name='api:consumptions:offlinetolerance-list')
    display_unit = serializers.SerializerMethodField('get_display_unit')

    class Meta:
        model = models.Consumption
        fields = ('url', 'id', 'name', 'unit', 'display_unit', 'customer',
                  'periods', 'offlinetolerance', 'hourly', 'nonpulse_periods',
                  'pulse_periods', 'single_value_periods')

    def get_hourly(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:consumptions:consumption-hourly', kwargs={'pk': obj.id})

    def get_display_unit(self, obj):
        return units.UNIT_DISPLAY_NAMES[obj.unit]


class MainConsumption(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    description = serializers.CharField(source='description_plain')
    hourly = serializers.SerializerMethodField('get_hourly')

    class Meta:
        model = models.MainConsumption
        fields = (
            'url', 'id', 'customer',
            'name', 'description', 'utility_type',
            'tariff', 'cost_compensation', 'hourly',
            'from_date', 'to_date',
        )

    def get_hourly(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:consumptions:mainconsumption-hourly',
            args=[obj.id], request=self.context['request'])


class ConsumptionGroup(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    description = serializers.CharField(source='description_plain')
    hourly = serializers.SerializerMethodField('get_hourly')

    class Meta:
        model = models.ConsumptionGroup
        fields = (
            'url', 'id', 'customer', 'name', 'description',
            'mainconsumption', 'cost_compensation', 'hourly',
            'from_date', 'to_date',
        )

    def get_hourly(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:consumptions:consumptiongroup-hourly',
            args=[obj.id], request=self.context['request'])


class NonpulsePeriod(serializers.DefaultSerializer):
    class Meta:
        model = models.NonpulsePeriod
        fields = (
            'url', 'id', 'from_timestamp', 'to_timestamp', 'datasequence',
            'datasource')
        read_only_fields = ('datasequence',)


class PulsePeriod(serializers.DefaultSerializer):
    class Meta:
        model = models.PulsePeriod
        fields = (
            'url', 'id', 'from_timestamp', 'to_timestamp', 'datasequence',
            'datasource', 'pulse_quantity', 'output_quantity', 'output_unit')
        read_only_fields = ('datasequence',)


class SingleValuePeriod(serializers.DefaultSerializer):
    class Meta:
        model = models.SingleValuePeriod
        fields = (
            'url', 'id', 'from_timestamp', 'to_timestamp', 'datasequence',
            'value', 'unit')
        read_only_fields = ('datasequence',)


class OfflineTolerance(serializers.DefaultSerializer):
    class Meta:
        model = models.OfflineTolerance
        fields = (
            'url', 'id', 'hours', 'datasequence')
        read_only_fields = ('datasequence',)
