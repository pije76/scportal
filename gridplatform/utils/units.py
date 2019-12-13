# -*- coding: utf-8 -*-
"""
This module defines physical units as they are to be identified in the code,
and as they are to be shown to the user.

:note: Not all buckingham units will have defined a user-friendly name
    in this module.  And likewise, not all units that get their
    user-friendly name defined in this module are buckingham units; in
    particular celsius.  All units that should ever be shown to the
    user must be defined in this module.

:see: :class:`gridplatform.utils.preferredunits.UnitConverter` and its
    subclasses for abstractions related to displaying physical
    quantities with human readable units.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from model_utils import Choices

from .unitconversion import PhysicalQuantity
from .unitconversion import UnitParseError
from .unitconversion import register_unit

WATT_POWER_CHOICES = (
    ("milliwatt", _('mW')),
    ("watt", _('W')),
    ("kilowatt", _('kW')),
    ("megawatt", _('MW')))

JOULE_PR_HOUR_POWER_CHOICES = (
    ("millijoule*hour^-1", _('mJ/h')),
    ("joule*hour^-1", _('J/h')),
    ("kilojoule*hour^-1", _('kJ/h')),
    ("megajoule*hour^-1", _('MJ/h')))

POWER_CHOICES = WATT_POWER_CHOICES + JOULE_PR_HOUR_POWER_CHOICES

WATT_HOUR_ENERGY_CHOICES = (
    ("milliwatt*hour", _('mWh')),
    ("watt*hour", _('Wh')),
    ("kilowatt*hour", _('kWh')),
    ("megawatt*hour", _('MWh')))

JOULE_ENERGY_CHOICES = (
    ("millijoule", _('mJ')),
    ("joule", _('J')),
    ("kilojoule", _('kJ')),
    ("megajoule", _('MJ')))

ENERGY_CHOICES = WATT_HOUR_ENERGY_CHOICES + JOULE_ENERGY_CHOICES

VOLUME_CHOICES = (
    ("liter", _('L')),
    ("milliliter", _('mL')),
    ("meter*meter*meter", _(u'm³')))

VOLUME_FLOW_CHOICES = (
    ("liter*second^-1", _("L/s")),
    ("liter*minute^-1", _("L/min")),
    ("liter*hour^-1", _("L/h")),
    ("milliliter*hour^-1", _("mL/h")),
    ("meter*meter*meter*second^-1", _(u"m³/s")),
    ("meter*meter*meter*minute^-1", _(u"m³/min")),
    ("meter*meter*meter*hour^-1", _(u"m³/h")))

# Be aware buckingham (and any other unit conversion library) does
# not recognize celsius and fahrenheit as physical units, because
# neither are basisvectors in a metrical space.  In fact, you
# can't convert celsius to fahrenheit because you don't know if
# its a relative temperature or an absolute temperature.  This
# always depend on the application.
#
# Luckily, these units will raise exceptions if used with
# Buckingham, so the mistake will be discovered in due time.
TEMPERATURE_CHOICES = (
    ("celsius", _(u"°C")),
    ("fahrenheit", _(u"°F")),
    ("millikelvin", _(u"mK")),
    ("kelvin", _(u"K")),
)

TIME_UNITS = (
    ('second', _('s')),
    ('minute', _('m')),
    ('hour', _('h')),
)

VOLTAGE_CHOICES = (
    ('volt', _('V')),
    ('millivolt', _('mV')),
)

CURRENT_CHOICES = (
    ('ampere', _('A')),
    ('milliampere', _('mA')),
)

ENERGY_TARIFF_CHOICES = (
    ("currency_eur*kilowatt^-1*hour^-1", _(u"EUR/kWh")),
    ("currency_eur*megawatt^-1*hour^-1", _(u"EUR/MWh")),
    ("currency_dkk*kilowatt^-1*hour^-1", _(u"DKK/kWh")),
    ("currency_dkk*megawatt^-1*hour^-1", _(u"DKK/MWh")),
)

VOLUME_TARIFF_CHOICES = (
    ("currency_eur*liter^-1", _(u"EUR/l")),
    ("currency_eur*meter^-3", _(u"EUR/m³")),
    ("currency_dkk*liter^-1", _(u"DKK/l")),
    ("currency_dkk*meter^-3", _(u"DKK/m³")),
)

TARIFF_CHOICES = ENERGY_TARIFF_CHOICES + VOLUME_TARIFF_CHOICES

COST_COMPENSATION_CHOICES = (
    ('currency_eur*kilowatt^-1*hour^-1', _('EUR/kWh')),
    ('currency_eur*megawatt^-1*hour^-1', _('EUR/MWh')),
    ('currency_dkk*kilowatt^-1*hour^-1', _('DKK/kWh')),
    ('currency_dkk*megawatt^-1*hour^-1', _('DKK/MWh')),
)

INPUT_CHOICES = POWER_CHOICES + ENERGY_CHOICES + \
    VOLUME_CHOICES + VOLUME_FLOW_CHOICES + TEMPERATURE_CHOICES + \
    VOLTAGE_CHOICES + CURRENT_CHOICES

DEGREE_DAYS_CHOICES = (
    ('kelvin*day', _(u'degree days')),)

MISC_INDEX_CHOICES = (
    ('gram*kilowatt^-1*hour^-1', 'g/kWh'),
    ('gram*meter^-3', 'g/m³'),
    ('meter^2', 'm²'),
    ('person', _('Person')),
    ('tonne', _('tonne')),
    ('kilogram', 'kg'),
)

CURRENCY_CHOICES = (
    ('currency_eur', 'EUR'),
    ('currency_dkk', 'DKK'),
)

ENPI_CHOICES = (
    ('watt*kelvin^-1', 'W/K'),
)

CO2_CONVERSION_CHOICES = (
    ('gram*kilowatt^-1*hour^-1', 'g/kWh'),
    ('kilogram*kilowatt^-1*hour^-1', 'kg/kWh'),
    ('tonne*megawatt^-1*hour^-1', _('tonne/MWh')),

    ('gram*meter^-3', 'g/m³'),
    ('gram*liter^-1', 'g/l'),
    ('kilogram*meter^-3', 'kg/m³'),
    ('kilogram*liter^-1', 'kg/l'),
)

register_unit('year', (365, 'day'))
assert PhysicalQuantity(365, 'day') == PhysicalQuantity(1, 'year')

register_unit('month', (30, 'day'))
assert PhysicalQuantity(30, 'day') == PhysicalQuantity(1, 'month')

register_unit('week', (7, 'day'))
assert PhysicalQuantity(7, 'day') == PhysicalQuantity(1, 'week')

CONSUMPTION_PER_TIME_CHOICES = (
    ('kilowatt*hour*year^-1', _('kWh/year')),
    ('kilowatt*hour*quarteryear^-1', _('kWh/quarter')),
    ('kilowatt*hour*month^-1', _('kWh/month')),
    ('kilowatt*hour*week^-1', _('kWh/week')),
    ('kilowatt*hour*day^-1', _('kWh/day')),
    ('kilowatt*hour*hour^-1', _('kWh/hour')),
)

IMPULSE_CHOICE = (
    ('impulse', _('impulse')),
)

POWER_FACTOR_CHOICE = (
    ('millinone', ''),
)

UNIT_CHOICES = INPUT_CHOICES + TARIFF_CHOICES + \
    DEGREE_DAYS_CHOICES + MISC_INDEX_CHOICES + CURRENCY_CHOICES + \
    ENPI_CHOICES + CONSUMPTION_PER_TIME_CHOICES + VOLTAGE_CHOICES + \
    CURRENT_CHOICES + ENERGY_TARIFF_CHOICES + IMPULSE_CHOICE + \
    POWER_FACTOR_CHOICE + TIME_UNITS

preferred_unit_bases = {}
for lst, base in [(POWER_CHOICES, 'millijoule*hour^-1'),
                  (ENERGY_CHOICES, 'millijoule'),
                  (VOLUME_CHOICES, 'milliliter'),
                  (VOLUME_FLOW_CHOICES, 'milliliter*hour^-1')]:
    for unit, string in lst:
        preferred_unit_bases[unit] = base


ACCUMULATION_BASE_UNITS = [
    'milliwatt*hour',
    'milliliter',
    'gram',
]
TIME_BASE_UNITS = [
    'second',
]
IMPULSE_BASE_UNITS = [
    'impulse',
]
NONACCUMULATION_BASE_UNITS = [
    'milliwatt',
    'milliliter*hour^-1',
    'millikelvin',
    'millivolt',
    'milliampere',
    'millibar',
    'millinone',
]
ENERGY_PER_VOLUME_BASE_UNITS = [
    'milliwatt*hour/meter^3',
]
ENERGY_PER_MASS_BASE_UNITS = [
    'milliwatt*hour/tonne',
]

PRODUCTION_UNITS = ['production_%s' % c for c in 'abcde']

ENERGY_TARIFF_BASE_UNITS = [
    'currency_dkk*gigawatt^-1*hour^-1',
    'currency_eur*gigawatt^-1*hour^-1',
]

VOLUME_TARIFF_BASE_UNITS = [
    'millicurrency_eur*meter^-3',
    'millicurrency_dkk*meter^-3',
]


TARIFF_BASE_UNITS = VOLUME_TARIFF_BASE_UNITS + ENERGY_TARIFF_BASE_UNITS

VOLUME_CO2_CONVERSION_BASE_UNIT = 'gram*meter^-3'

ENERGY_CO2_CONVERSION_BASE_UNIT = 'gram*kilowatt^-1*hour^-1'

CO2_CONVERSION_BASE_UNITS = [
    VOLUME_CO2_CONVERSION_BASE_UNIT,
    ENERGY_CO2_CONVERSION_BASE_UNIT
]

BASE_UNITS = ACCUMULATION_BASE_UNITS + IMPULSE_BASE_UNITS + \
    NONACCUMULATION_BASE_UNITS + ENERGY_PER_VOLUME_BASE_UNITS + \
    ENERGY_PER_MASS_BASE_UNITS + TARIFF_BASE_UNITS + CO2_CONVERSION_BASE_UNITS + TIME_BASE_UNITS

# Note: names should not be internationalized.  They are supposed to be the
# prober SI unit names.
UNIT_DISPLAY_NAMES = {
    'kilowatt*hour': 'kWh',
    'watt*hour': 'Wh',
    'milliwatt*hour': 'mWh',
    'kilowatt': 'kW',
    'watt': 'W',
    'milliwatt': 'mW',
    'meter*meter*meter': 'm³',
    'liter': 'L',
    'milliliter': 'mL',
    'gram': 'g',
    'milliliter*hour^-1': 'mL/h',
    'millikelvin': 'mK',
    'kelvin': 'K',
    'volt': 'V',
    'millivolt': 'mV',
    'ampere': 'A',
    'milliampere': 'mA',
    'kilowatt*hour/meter^3': 'kWh/m³',
    'watt*hour/meter^3': 'Wh/m³',
    'milliwatt*hour/meter^3': 'mWh/m³',
    'joule': 'J',
    # http://en.wikipedia.org/wiki/Tonne#Symbol_and_abbreviations
    'milliwatt*hour/tonne': 'mWh/t',
    'currency_eur*gigawatt^-1*hour^-1': 'EUR/GWh',
    'currency_eur*kilowatt^-1*hour^-1': 'EUR/kWh',
    'currency_eur*megawatt^-1*hour^-1': 'EUR/MWh',
    'currency_dkk*gigawatt^-1*hour^-1': 'DKK/GWh',
    'currency_dkk*kilowatt^-1*hour^-1': 'DKK/kWh',
    'currency_dkk*megawatt^-1*hour^-1': 'DKK/MWh',
    'millicurrency_dkk*meter^-3': 'DKK/1000m³',
    'millicurrency_eur*meter^-3': 'EUR/1000m³',
    'currency_dkk*meter^-3': 'DKK/m³',
    'currency_eur*meter^-3': 'EUR/m³',
    # Impulse cannot have a proper SI name, so it gets internationalized
    # anyway.
    'impulse': _('impulse'),
    'millibar': 'mBar',
    'gram*kilowatt^-1*hour^-1': 'g/kWh',
    'gram*meter^-3': 'g/m3',
    'none': '',
    'millinone': '',
    'second': 's',
    'minute': 'm',
    'hour': 'h',
}
assert set(BASE_UNITS) <= set(UNIT_DISPLAY_NAMES.keys())

ACCUMULATION_BASE_UNIT_CHOICES = Choices(*[
    (unit, UNIT_DISPLAY_NAMES[unit])
    for unit in ACCUMULATION_BASE_UNITS
])
NONACCUMULATION_BASE_UNIT_CHOICES = Choices(*[
    (unit, UNIT_DISPLAY_NAMES[unit])
    for unit in NONACCUMULATION_BASE_UNITS
])
ENERGY_PER_VOLUME_BASE_UNIT_CHOICES = Choices(*[
    (unit, UNIT_DISPLAY_NAMES[unit])
    for unit in ENERGY_PER_VOLUME_BASE_UNITS
])
ENERGY_PER_MASS_BASE_UNIT_CHOICES = Choices(*[
    (unit, UNIT_DISPLAY_NAMES[unit])
    for unit in ENERGY_PER_MASS_BASE_UNITS
])
BASE_UNIT_CHOICES = Choices(*[
    (unit, UNIT_DISPLAY_NAMES[unit])
    for unit in BASE_UNITS
])


class _UnitConversionCacheDict(dict):
    """
    unit string -> base unit string mapping; populated on use.
    """

    def __missing__(self, key):
        """
        Try to find compatible base unit when queried for unknown/uncached key.
        """
        try:
            for base_unit in BASE_UNITS:
                if PhysicalQuantity.compatible_units(base_unit, key):
                    self[key] = base_unit
                    return base_unit
        except UnitParseError:
            # not a valid unit string (we assume base units to be valid)
            raise KeyError(key)
        # not compatible with any known base unit
        raise KeyError(key)

    def __contains__(self, item):
        """
        Auto-populate also on `in` and `not in` checks.  (This allows cleaner
        code in serializer validation for units.)
        """
        try:
            self[item]
            return True
        except KeyError:
            return False


unit_conversion_map = _UnitConversionCacheDict()
