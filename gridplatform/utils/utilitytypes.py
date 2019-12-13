# -*- coding: utf-8 -*-
"""
Reoccuring choices defined in one place to implement DRY.  Choices that are
unique to their application should just be defined inline, but choices that are
likely to overlap or be similar with choices of other apps are to be defined
here.

In particular the granularity of energy consumption classes vary a lot from
application to application (and so it should).
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from model_utils import Choices


__all__ = [
    'AREA_OF_ENERGY_USE_CHOICES',
    'METER_CHOICES',
    'OPTIONAL_METER_CHOICES',
    'UTILITY_TYPE_TO_COLOR',
]

UNKNOWN = (1000, 'unknown', _('unknown'))
TEMPERATURE = (1001, 'temperature', _('temperature'))

ELECTRICITY = (2000, 'electricity', _('electricity'))

DISTRICT_HEATING = (3000, 'district_heating', _('district heating'))

FUEL = (4000, 'fuel', _('fuel'))

LIQUID_FUEL = (5000, 'liquid_fuel', _('liquid fuel'))
OIL = (5500, 'oil', _('oil'))

SOLID_FUEL = (6000, 'solid_fuel', _('solid fuel'))

GAS = (7000, 'gas', _('gas'))

WATER = (8000, 'water', _('water'))

AREA_OF_ENERGY_USE_CHOICES = Choices(
    ELECTRICITY,
    WATER,
    DISTRICT_HEATING,
    FUEL,
)

METER_CHOICES = Choices(
    ELECTRICITY,
    WATER,
    GAS,
    DISTRICT_HEATING,
    OIL,
)

ENERGY_UTILITY_TYPE_CHOICES = Choices(
    ELECTRICITY,
    GAS,
    DISTRICT_HEATING,
    SOLID_FUEL,
    LIQUID_FUEL,
)

ENERGY_UTILITY_TYPE_TO_BASE_UNIT_MAP = {
    ELECTRICITY[0]: 'milliwatt*hour',
    GAS[0]: 'milliliter',
    DISTRICT_HEATING[0]: 'milliwatt*hour',
    SOLID_FUEL[0]: 'gram',
    LIQUID_FUEL[0]: 'milliliter',
}

ENERGY_UTILITY_TYPE_TO_DISPLAY_UNIT_MAP = {
    ELECTRICITY[0]: 'kilowatt*hour',
    GAS[0]: 'meter*meter*meter',
    DISTRICT_HEATING[0]: 'kilowatt*hour',
    SOLID_FUEL[0]: 'kilogram',
    LIQUID_FUEL[0]: 'meter*meter*meter',
}

# @deprecated: Use METER_UTILITY_TYPE_CHOICES and null=True instead.
OPTIONAL_METER_CHOICES = Choices(UNKNOWN,) + Choices(TEMPERATURE,) + \
    METER_CHOICES

METER_TYPE_CHOICES = Choices(TEMPERATURE,) + \
    METER_CHOICES

UTILITY_TYPE_TO_COLOR = {
    METER_CHOICES.electricity: '#294995',
    METER_CHOICES.water: '#009DE0',
    METER_CHOICES.gas: '#F2D4A3',
    METER_CHOICES.district_heating: '#B31117',
    METER_CHOICES.oil: '#E3A64A',
}
