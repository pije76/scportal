# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.rest import serializers
from . import models


class ComputeMixin(object):
    def get_default_fields(self):
        result = super(ComputeMixin, self).get_default_fields()
        result['compute'] = serializers.SerializerMethodField('compute')
        return result


class ProductionEnergyPerformance(
        ComputeMixin, serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    description = serializers.CharField(source='description_plain')
    display_production_unit = serializers.SerializerMethodField(
        'get_display_production_unit')

    class Meta:
        model = models.ProductionEnergyPerformance
        fields = (
            'url', 'id', 'customer', 'name', 'description',
            'production_unit', 'display_production_unit', 'consumptiongroups',
            'productiongroups', 'compute')

    def __init__(self, *args, **kwargs):
        super(ProductionEnergyPerformance, self).__init__(*args, **kwargs)
        customer = self.context['request'].user.customer
        if customer:
            self.fields['production_unit'] = serializers.ChoiceField(
                choices=customer.get_production_unit_choices())

    def get_display_production_unit(self, obj):
        return obj.unit_converter.get_display_unit()

    def compute(self, instance):
        request = self.context['request']
        return self.reverse(
            'api:energyperformances:productionenergyperformance-compute',
            args=[getattr(instance, 'id', None)], request=request)


class TimeEnergyPerformance(
        ComputeMixin, serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    description = serializers.CharField(source='description_plain')
    display_unit = serializers.SerializerMethodField('get_display_unit')

    class Meta:
        model = models.TimeEnergyPerformance
        fields = (
            'url', 'id', 'customer', 'name', 'description',
            'unit', 'display_unit', 'consumptiongroups', 'compute')

    def get_display_unit(self, obj):
        return obj.unit_converter.get_display_unit()

    def compute(self, instance):
        request = self.context['request']
        return self.reverse(
            'api:energyperformances:timeenergyperformance-compute',
            args=[getattr(instance, 'id', None)], request=request)
