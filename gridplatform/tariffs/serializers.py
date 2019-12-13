# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.rest import serializers
from gridplatform.utils import units

from . import models


class TariffSerializerBase(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    periods = serializers.HyperlinkedRelatedField(
        source='period_set', many=True, read_only=True)
    hourly = serializers.SerializerMethodField('get_hourly')
    fixed_price_periods = serializers.HyperlinkedIdentityField(
        view_name='api:tariffs:fixedpriceperiod-list')
    spot_price_periods = serializers.HyperlinkedIdentityField(
        view_name='api:tariffs:spotpriceperiod-list')
    unit = serializers.SerializerMethodField('get_unit')
    display_unit = serializers.SerializerMethodField('get_display_unit')

    class Meta:
        fields = (
            'url', 'id', 'name', 'customer', 'unit', 'display_unit',
            'periods', 'fixed_price_periods', 'spot_price_periods', 'hourly')

    def get_unit(self, obj):
        return obj.unit

    def get_display_unit(self, obj):
        return units.UNIT_DISPLAY_NAMES[obj.unit]


class EnergyTariff(TariffSerializerBase):
    class Meta(TariffSerializerBase.Meta):
        model = models.EnergyTariff

    def get_hourly(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:tariffs:energytariff-hourly', kwargs={'pk': obj.id})


class VolumeTariff(TariffSerializerBase):
    class Meta(TariffSerializerBase.Meta):
        model = models.VolumeTariff

    def get_hourly(self, obj):
        if not obj:
            return ''
        return self.reverse(
            'api:tariffs:volumetariff-hourly', kwargs={'pk': obj.id})


class FixedPricePeriod(serializers.DefaultSerializer):
    class Meta:
        model = models.FixedPricePeriod
        fields = (
            'url', 'id', 'from_timestamp', 'to_timestamp', 'datasequence',
            'subscription_fee', 'subscription_period', 'value', 'unit')
        read_only_fields = ('datasequence',)


class SpotPricePeriod(serializers.DefaultSerializer):
    class Meta:
        model = models.SpotPricePeriod
        fields = (
            'url', 'id', 'from_timestamp', 'to_timestamp', 'datasequence',
            'subscription_fee', 'subscription_period',
            'spotprice', 'coefficient',
            'unit_for_constant_and_ceiling', 'constant', 'ceiling')
        read_only_fields = ('datasequence',)
