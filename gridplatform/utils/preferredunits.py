# -*- coding: utf-8 -*-
"""
This module defines a class hierachy of unit converters starting
with the abstract base class :class:`.UnitConverter`.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from fractions import Fraction

from django.utils.translation import ugettext_lazy as _

from gridplatform.trackuser import get_customer

from . import units
from .unitconversion import register_unit
from .unitconversion import PhysicalQuantity


class UnitConverter(object):
    """
    Abstract class for defining preferred unit objects.

    Preferred unit objects are able to extract a numeric value from a physical
    quantity, and give a displayable version of the unit they repressent.
    """

    def extract_value(self, physical_quantity):
        """
        Extract value in preferred unit from given C{physical_quantity}
        """
        raise NotImplementedError(
            'This method is not implemented by %r' % self.__class__)

    def get_display_unit(self):
        """
        Return a human readable version of this preferred unit.
        """
        raise NotImplementedError(
            'This method is not implemented by %r' % self.__class__)


class PhysicalUnitConverter(UnitConverter):
    """
    A :class:`.PhysicalUnitConverter` is a :class:`.UnitConverter`
    implemented on top of the physical units that can be handled
    directly by :class:`.PhysicalQuantity`.

    :invariant: ``self.physical_unit`` must be listed in
        :data:`units.UNIT_CHOICES`
    """
    def __init__(self, physical_unit):
        """
        Construct a :class:`.PhysicalUnitConverter` from the given
        ``physical_unit``.
        """
        self.physical_unit = physical_unit
        self._assert_invariant()

    def extract_value(self, physical_quantity):
        return physical_quantity.convert(self.physical_unit)

    def get_display_unit(self):
        return dict(units.UNIT_CHOICES)[self.physical_unit]

    def _assert_invariant(self):
        assert self.physical_unit in (
            key for key, value in units.UNIT_CHOICES), self.physical_unit


class KvarUnitConverter(UnitConverter):
    """
    Unit converter for reactive power.
    """
    def extract_value(self, physical_quantity):
        return physical_quantity.convert('kilovolt*ampere')

    def get_display_unit(self):
        return 'kVAr'


class KvarhUnitConverter(UnitConverter):
    """
    Unit converter for reactive energy
    """
    def extract_value(self, physical_quantity):
        return physical_quantity.convert('kilovolt*ampere*hour')

    def get_display_unit(self):
        return 'kVArh'


class PowerFactorUnitConverter(UnitConverter):
    """
    Unit converter for power factor
    """
    def extract_value(self, physical_quantity):
        return physical_quantity.convert('none')

    def get_display_unit(self):
        return ''


class DisplayCelsiusMixin(object):
    """
    Mixes :meth:`.DisplayCelsiusMixin.get_display_unit` into a unit
    converter.

    :invariant: ``self.physical_unit`` is ``'kelvin'``.
    """
    def get_display_unit(self):
        """
        :return: A degrees Celsius symbol.
        """
        return dict(units.UNIT_CHOICES)['celsius']

    def _assert_invariant(self):
        assert self.physical_unit == 'kelvin'


class RelativeCelsiusUnitConverter(DisplayCelsiusMixin, PhysicalUnitConverter):
    """
    Unit converter for relative temperature in degrees Celsius.
    """
    def __init__(self):
        super(RelativeCelsiusUnitConverter, self).__init__('kelvin')


class AbsoluteCelsiusUnitConverter(DisplayCelsiusMixin, UnitConverter):
    """
    Unit converter for absolute temperature in degrees Celsius.
    """
    def extract_value(self, physical_quantity):
        """
        :return: The degrees Kelvin differense between 273.15 K and the
            given :class:`.PhysicalQuantity`.

        :param physical_quantity: The given :class:`.PhysicalQuantity`
            to extract value from.
        """
        return physical_quantity.convert('kelvin') - Fraction('273.15')


class DisplayFahrenheitMixin(object):
    """
    Mixes :meth:`.DisplayFahrenheitMixin.get_display_unit` into a unit
    converter.

    :invariant: ``self.physical_unit`` is ``'rankine'``.
    """
    def get_display_unit(self):
        """
        :return: A degrees Fahrenheit symbol.
        """
        return dict(units.UNIT_CHOICES)['fahrenheit']

    def _assert_invariant(self):
        assert self.physical_unit == 'rankine'


class RelativeFahrenheitUnitConverter(DisplayFahrenheitMixin,
                                      PhysicalUnitConverter):
    """
    Unit converter for relative temperature in degrees Fahrenheit.
    """
    def __init__(self):
        super(RelativeFahrenheitUnitConverter, self).__init__('rankine')


class AbsoluteFahrenheitUnitConverter(DisplayFahrenheitMixin, UnitConverter):
    """
    Unit converter for absolute temperature in degrees Fahrenheit.
    """
    def extract_value(self, physical_quantity):
        """
        :return: The degrees Rankine differense between 459.67 R and the
            given :class:`.PhysicalQuantity`.

        :param physical_quantity: The given :class:`.PhysicalQuantity`
            to extract value from.
        """
        return physical_quantity.convert('rankine') - Fraction('459.67')


class AbstractENPIUnitConverter(UnitConverter):
    """
    Abstract generic unit converter for ENPI.  In this case that is a
    fraction of energy divided by an energy driver.

    Concrete subclasses should set the following two class members:

    :ivar energy_unit:  The unit of energy.
    :ivar physical_unit: The ENPI unit, defined by multiplying
        ``energy_unit`` and ``RECIPROCAL_ENERGY_DRIVER_UNIT``
    :cvar RECIPROCAL_ENERGY_DRIVER_UNIT: The reciprocal energy driver
        unit
    :cvar UNIT_DISPLAY_FORMAT: The ENPI unit in a human readable
        string meant to be string interpolated with ``energy_unit``
        format argument, i.e. containing the substring
        ``{energy_unit}``
    """
    RECIPROCAL_ENERGY_DRIVER_UNIT = None
    UNIT_DISPLAY_FORMAT = None

    def __init__(self, energy_unit):
        """
        :param energy_unit: The initial value of ``self.energy_unit``.
        """
        assert self.RECIPROCAL_ENERGY_DRIVER_UNIT is not None
        assert self.UNIT_DISPLAY_FORMAT is not None
        self.energy_unit = energy_unit

    def extract_value(self, physical_quantity):
        assert self.RECIPROCAL_ENERGY_DRIVER_UNIT is not None
        return physical_quantity.convert(self.physical_unit)

    def get_display_unit(self):
        assert self.UNIT_DISPLAY_FORMAT is not None
        return self.UNIT_DISPLAY_FORMAT.format(
            energy_unit=dict(units.UNIT_CHOICES)[self.energy_unit])

    @property
    def physical_unit(self):
        return '%s*%s' % (self.energy_unit, self.RECIPROCAL_ENERGY_DRIVER_UNIT)


register_unit('personyear', (365, 'person*day'))
assert PhysicalQuantity(365, 'person*day') == PhysicalQuantity(1, 'personyear')


class PersonsENPIUnitConverter(AbstractENPIUnitConverter):
    """
    Unit converter for ENPI with number of person years as energy
    driver.  Equivalent to power per person.
    """
    RECIPROCAL_ENERGY_DRIVER_UNIT = 'personyear^-1'
    UNIT_DISPLAY_FORMAT = _('{energy_unit}/person year')


register_unit('squaremeteryear', (365, 'meter^2*day'))
assert PhysicalQuantity(365, 'meter^2*day') == \
    PhysicalQuantity(1, 'squaremeteryear')


class AreaENPIUnitConverter(AbstractENPIUnitConverter):
    """
    Unit converter for ENPI with number of square meter years as
    energy driver.  Equivalent to power per square meter.
    """
    RECIPROCAL_ENERGY_DRIVER_UNIT = 'squaremeteryear^-1'
    UNIT_DISPLAY_FORMAT = _('{energy_unit}/m² year')


class AbstractProductionENPIUnitConverter(AbstractENPIUnitConverter):
    """
    Abstract unit converter for ENPI with production as energy driver.

    :cvar PRODUCTION_UNIT: The production unit.
    """
    PRODUCTION_UNIT = None

    def __init__(self, energy_unit, customer=None):
        assert self.PRODUCTION_UNIT is not None
        if customer is None:
            customer = get_customer()
        production_unit_display = getattr(
            customer, self.PRODUCTION_UNIT + '_unit_plain') or \
            self.PRODUCTION_UNIT
        self.UNIT_DISPLAY_FORMAT = '{energy_unit}/' + production_unit_display
        self.RECIPROCAL_ENERGY_DRIVER_UNIT = self.PRODUCTION_UNIT + '^-1'
        super(AbstractProductionENPIUnitConverter, self).__init__(energy_unit)


class ProductionAENPIUnitConverter(AbstractProductionENPIUnitConverter):
    """
    Unit converter for ENPI with ``'production_a'`` as energy driver.
    """
    PRODUCTION_UNIT = 'production_a'


class ProductionBENPIUnitConverter(AbstractProductionENPIUnitConverter):
    """
    Unit converter for ENPI with ``'production_b'`` as energy driver.
    """
    PRODUCTION_UNIT = 'production_b'


class ProductionCENPIUnitConverter(AbstractProductionENPIUnitConverter):
    """
    Unit converter for ENPI with ``'production_c'`` as energy driver.
    """
    PRODUCTION_UNIT = 'production_c'


class ProductionDENPIUnitConverter(AbstractProductionENPIUnitConverter):
    """
    Unit converter for ENPI with ``'production_d'`` as energy driver.
    """
    PRODUCTION_UNIT = 'production_d'


class ProductionEENPIUnitConverter(AbstractProductionENPIUnitConverter):
    """
    Unit converter for ENPI with ``'production_e'`` as energy driver.
    """
    PRODUCTION_UNIT = 'production_e'


class ProductionUnitConverter(PhysicalUnitConverter):
    """
    Unit converter for productions.
    """
    def get_display_unit(self):
        """
        :return: The human readable production unit as set by current
            :class:`gridplatform.customers.models.Customer`.
        """
        if get_customer() is None:
            return self.physical_unit

        display_unit = getattr(
            get_customer(), '%s_unit_plain' % self.physical_unit)
        if display_unit:
            return display_unit
        else:
            return self.physical_unit

    def _assert_invariant(self):
        pass


class EfficiencyUnitConverter(UnitConverter):
    """
    Unit converter for efficiency.

    :note: (UGLY-HACK) The GridAgent doesn't have a suitable unit for
        modbus register values that are efficiencies (which is really
        unitless), so as a temponary work-around we have decided to
        use millibar instead.
    """
    def extract_value(self, physical_quantity):
        return physical_quantity.convert('bar')

    def get_display_unit(self):
        return _('efficiency')
