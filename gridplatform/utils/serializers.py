# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.rest import serializers
from gridplatform.utils import units
from gridplatform.utils.preferredunits import PhysicalUnitConverter
from gridplatform.utils.preferredunits import ProductionUnitConverter


class SampleBase(serializers.Serializer):
    """
    Base :class:`~gridplatform.rest.serializers.Serializer` for
    :class:`~gridplatform.utils.samples.RangedSample` and
    :class:`~gridplatform.utils.samples.PointSample`.

    :ivar unit: The unit that the
        :class:`~gridplatform.utils.unitconversion.PhysicalQuantity`
        of serialized sample should be converted to.
    :ivar display_unit: A human readable version of ``self.unit``.
    :ivar value: The converted
        :class:`~gridplatform.utils.unitconversion.PhysicalQuantity`
        of serialized sample.
    """
    unit = serializers.SerializerMethodField('get_unit')
    display_unit = serializers.SerializerMethodField('get_display_unit')
    value = serializers.SerializerMethodField('get_value')

    def get_unit(self, obj):
        """
        :return: The unit that the
            :class:`~gridplatform.utils.unitconversion.PhysicalQuantity`
            of serialized sample should be converted to.
        """
        return self.context['unit']

    def get_display_unit(self, obj):
        """
        A human readable version of ``self.unit``.  Only production units
        and plain physical units are supported.
        """
        unit = self.get_unit(obj)
        if unit in units.PRODUCTION_UNITS:
            return ProductionUnitConverter(unit).get_display_unit()
        else:
            return PhysicalUnitConverter(unit).get_display_unit()

    def get_value(self, obj):
        """
        :return: The converted
            :class:`~gridplatform.utils.unitconversion.PhysicalQuantity`
            of given sample.
        :rtype: int
        :param obj: The sample to serialize.
        """
        if not obj:
            return None
        unit = self.get_unit(obj)
        # We don't care about decimals. If the unit isn't fine grained enough
        # then the problem is with the unit, not the lack of decimals.
        return int(obj.physical_quantity.convert(unit))


class PointSampleSerializer(SampleBase):
    """
    Serializer for :class:`~gridplatform.utils.samples.PointSample`.

    :see:
        :class:`gridplatform.datasources.viewsets.RawDataViewSetBase`
        for example usage.
    """
    timestamp = serializers.DateTimeField(source='timestamp')


class RangedSampleSerializer(SampleBase):
    """
    Serializer for :class:`~gridplatform.utils.samples.RangedSample`.

    :see: :class:`gridplatform.datasequences.views.HourlyDataView` for
        example usage.
    """
    from_timestamp = serializers.DateTimeField(source='from_timestamp')
    to_timestamp = serializers.DateTimeField(source='to_timestamp')
