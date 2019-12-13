# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytz

from django.core.exceptions import ValidationError

from gridplatform.rest import serializers
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.units import BASE_UNITS
from gridplatform.utils.units import unit_conversion_map
from gridplatform.utils import units

from .models import RawData
from .models import DataSource


class DataSourceSerializerBase(serializers.DefaultSerializer):
    display_unit = serializers.SerializerMethodField('get_display_unit')

    def get_display_unit(self, obj):
        if obj.unit == 'millibar':
            return 'efficiency'
        return units.UNIT_DISPLAY_NAMES[obj.unit]

    def validate_unit(self, attrs, source):
        unit = attrs[source]
        if unit not in unit_conversion_map:
            raise ValidationError(b'invalid unit %s' % unit)
        attrs[source] = unit_conversion_map[unit]
        return attrs

    def _url_parameters(self):
        model_meta = self.opts.model._meta
        return {
            'app_label': model_meta.app_label,
            'model_name': model_meta.object_name.lower()
        }


class RawDataWithUnitSerializer(serializers.ModelSerializer):
    unit = serializers.ChoiceField(choices=())

    class Meta:
        model = RawData
        fields = ('timestamp', 'value', 'unit')

    def __init__(self, *args, **kwargs):
        super(RawDataWithUnitSerializer, self).__init__(*args, **kwargs)
        parser_context = self.context['request'].parser_context
        datasource_id = parser_context['kwargs'].get('datasource_id')
        datasource_model = self.opts.model.datasource.field.rel.to
        self.datasource = datasource_model.objects.get(id=datasource_id)
        unit_choices = (
            (unit, display_name) for unit, display_name in
            units.UNIT_DISPLAY_NAMES.items()
            if PhysicalQuantity.compatible_units(self.datasource.unit, unit)
        )
        self.fields['unit'].choices = unit_choices

    def restore_object(self, attrs, instance=None):
        assert instance is None
        value = attrs['value']
        unit = attrs['unit']
        assert unit in BASE_UNITS
        instance = self.opts.model(
            value=value, timestamp=attrs['timestamp'],
            datasource=self.datasource)
        return instance

    def validate_unit(self, attrs, source):
        # only checks that unit is valid
        unit = attrs[source]
        if unit not in unit_conversion_map:
            raise ValidationError(b'invalid unit %s' % unit)
        return attrs

    def validate(self, attrs):
        # actually convert unit/value
        value = attrs['value']
        unit = attrs['unit']
        timestamp = attrs['timestamp']
        # unit is known to be present in conversion map from validate_unit()
        base_unit = unit_conversion_map[unit]
        attrs['value'] = int(PhysicalQuantity(value, unit).convert(base_unit))
        attrs['unit'] = base_unit
        attrs['timestamp'] = timestamp.replace(tzinfo=pytz.utc)
        return attrs

    def get_validation_exclusions(self, instance=None):
        # NOTE: datasource is set in restore_object and we would like
        # uniqueness constraints to be validated.
        return [
            exclusion for exclusion in
            super(RawDataWithUnitSerializer, self).get_validation_exclusions()
            if exclusion != 'datasource']


class DataSourceSerializer(DataSourceSerializerBase):
    raw_data = serializers.HyperlinkedIdentityField(
        view_name='api:datasources:rawdata-list')

    class Meta:
        model = DataSource
        fields = (
            'url', 'id', 'customer', 'unit', 'display_unit',
            'hardware_id', 'raw_data'
        )
