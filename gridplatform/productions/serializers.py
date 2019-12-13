# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.rest import serializers
from . import models


class Production(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    periods = serializers.HyperlinkedRelatedField(
        source='period_set', many=True, read_only=True)
    hourly = serializers.SerializerMethodField('get_hourly')
    nonpulse_periods = serializers.HyperlinkedIdentityField(
        view_name='api:productions:nonpulseperiod-list')
    pulse_periods = serializers.HyperlinkedIdentityField(
        view_name='api:productions:pulseperiod-list')
    single_value_periods = serializers.HyperlinkedIdentityField(
        view_name='api:productions:singlevalueperiod-list')
    offlinetolerance = serializers.HyperlinkedIdentityField(
        view_name='api:productions:offlinetolerance-list')
    display_unit = serializers.SerializerMethodField('get_display_unit')

    class Meta:
        model = models.Production
        fields = (
            'url', 'id', 'name', 'unit', 'display_unit', 'hourly', 'customer',
            'periods', 'nonpulse_periods', 'single_value_periods',
            'offlinetolerance')

    def __init__(self, *args, **kwargs):
        super(Production, self).__init__(*args, **kwargs)
        customer = self.context['request'].user.customer
        if customer:
            self.fields['unit'] = serializers.ChoiceField(
                choices=customer.get_production_unit_choices())

    def get_hourly(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:productions:production-hourly', kwargs={'pk': obj.id})

    def get_display_unit(self, obj):
        return obj.customer.get_production_unit_choices()[obj.unit]


class ProductionGroup(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    description = serializers.CharField(source='description_plain')
    hourly = serializers.SerializerMethodField('get_hourly')
    display_unit = serializers.SerializerMethodField('get_display_unit')

    class Meta:
        model = models.ProductionGroup
        fields = (
            'url', 'id', 'customer', 'name', 'description',
            'productions', 'unit', 'display_unit', 'hourly')

    def __init__(self, *args, **kwargs):
        super(ProductionGroup, self).__init__(*args, **kwargs)
        customer = self.context['request'].user.customer
        if customer:
            self.fields['unit'] = serializers.ChoiceField(
                choices=customer.get_production_unit_choices())

    def get_hourly(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:productions:productiongroup-hourly',
            args=[obj.id], request=self.context['request'])

    def get_display_unit(self, obj):
        return obj.customer.get_production_unit_choices()[obj.unit]


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
        fields = ('url', 'id', 'hours', 'datasequence')
        read_only_fields = ('datasequence',)
