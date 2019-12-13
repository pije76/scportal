# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.rest import serializers
from gridplatform.utils import units

from . import models


class EnergyPerVolumeDataSequence(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    periods = serializers.HyperlinkedRelatedField(
        source='period_set',
        view_name='api:datasequences:energypervolumeperiod-detail',
        many=True, read_only=True)
    hourly = serializers.SerializerMethodField('get_hourly')
    energy_per_volume_periods = serializers.HyperlinkedIdentityField(
        view_name='api:datasequences:energypervolumeperiod-list')
    unit = serializers.SerializerMethodField('get_unit')
    display_unit = serializers.SerializerMethodField('get_display_unit')

    class Meta:
        model = models.EnergyPerVolumeDataSequence
        fields = ('url', 'id', 'name', 'unit', 'display_unit', 'customer',
                  'periods', 'hourly', 'energy_per_volume_periods')

    def get_unit(self, obj):
        return obj.unit

    def get_display_unit(self, obj):
        return units.UNIT_DISPLAY_NAMES[obj.unit]

    def get_hourly(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:datasequences:energypervolumedatasequence-hourly',
            kwargs={'pk': obj.id})


class EnergyPerVolumePeriod(serializers.DefaultSerializer):
    class Meta:
        model = models.EnergyPerVolumePeriod
        fields = (
            'url', 'id', 'from_timestamp', 'to_timestamp', 'datasequence',
            'datasource')
        read_only_fields = ('datasequence',)


class NonaccumulationDataSequence(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    periods = serializers.HyperlinkedRelatedField(
        source='period_set',
        view_name='api:datasequences:nonaccumulationperiod-detail',
        many=True, read_only=True)
    nonaccumulation_periods = serializers.HyperlinkedIdentityField(
        view_name='api:datasequences:nonaccumulationperiod-list')
    raw_data = serializers.SerializerMethodField('get_raw_data')
    offlinetolerance = serializers.HyperlinkedIdentityField(
        view_name='api:datasequences:nonaccumulationofflinetolerance-list')
    display_unit = serializers.SerializerMethodField('get_display_unit')

    class Meta:
        model = models.NonaccumulationDataSequence
        fields = ('url', 'id', 'name', 'unit', 'display_unit', 'customer',
                  'periods', 'nonaccumulation_periods', 'offlinetolerance',
                  'raw_data')

    def get_display_unit(self, obj):
        return units.UNIT_DISPLAY_NAMES[obj.unit]

    def get_raw_data(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:datasequences:nonaccumulationdatasequence-raw-data',
            kwargs={'pk': obj.id})


class NonaccumulationPeriod(serializers.DefaultSerializer):
    class Meta:
        model = models.NonaccumulationPeriod
        fields = (
            'url', 'id', 'from_timestamp', 'to_timestamp', 'datasequence',
            'datasource')
        read_only_fields = ('datasequence',)


class NonaccumulationOfflineTolerance(serializers.DefaultSerializer):
    class Meta:
        model = models.NonaccumulationOfflineTolerance
        fields = ('url', 'id', 'hours', 'datasequence')
        read_only_fields = ('datasequence',)
