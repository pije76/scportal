#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit conversion library.

This is base on/inspired by the Python Buckingham module, available at
https://code.google.com/p/buckingham/ (though that thing crashes when
trying to convert a zero-valued quantity, because of obscure notion of
relative error).

Fraction is used for numbers.  This allows us to specify non-base units
concisely in terms of other non-base units without loss of precision, and means
that we avoid introducing errors beyond those present in the input.  (Most
"relevant" units are *defined* in terms of SI base units, and can be expressed
accurately --- but not necessarily as a Python Decimal or float value; there
are funny units like the survey foot, defined as 1200/3937 meter...)
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import operator
import numbers
import warnings
from fractions import Fraction
from decimal import Decimal
from collections import OrderedDict, namedtuple
from exceptions import UserWarning


__all__ = ['UnitConversionError', 'UnitParseError', 'IncompatibleUnitsError',
           'PhysicalQuantity', 'register_unit', 'simple_convert']


class UnitConversionError(ValueError):
    pass


class UnitParseError(UnitConversionError):
    pass


class IncompatibleUnitsError(UnitConversionError):
    pass


class UnitConversionTypeError(UnitConversionError, TypeError):
    pass


class NotPhysicalQuantityError(UnitConversionTypeError):
    pass


class UnitConversionWarning(UserWarning):
    pass


BASE_UNITS = OrderedDict([
    # http://en.wikipedia.org/wiki/SI_base_unit
    ('none',         (1, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))),
    ('meter',        (1, (1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))),
    ('gram',         (1, (0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))),
    ('second',       (1, (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))),
    ('ampere',       (1, (0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))),
    ('kelvin',       (1, (0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))),
    ('mole',         (1, (0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))),
    ('candela',      (1, (0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0))),
    # useful non-SI units
    ('currency_eur', (1, (0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0))),
    ('currency_dkk', (1, (0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0))),
    ('person',       (1, (0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0))),
    ('impulse',      (1, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0))),
    # customizable production units
    ('production_a', (1, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0))),
    ('production_b', (1, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0))),
    ('production_c', (1, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0))),
    ('production_d', (1, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0))),
    ('production_e', (1, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1))),
])


UNIT_NAMES = tuple(BASE_UNITS.keys()[1:])


SCALES = (
    ('yocto', Fraction(10)**-24),
    ('zepto', Fraction(10)**-21),
    ('atto', Fraction(10)**-18),
    ('femto', Fraction(10)**-15),
    ('pico', Fraction(10)**-12),
    ('nano', Fraction(10)**-9),
    ('micro', Fraction(10)**-6),
    ('milli', Fraction(10)**-3),
    ('centi', Fraction(10)**-2),
    ('deci', Fraction(10)**-1),
    ('deca', Fraction(10)**1),
    ('hecto', Fraction(10)**2),
    ('kilo', Fraction(10)**3),
    ('mega', Fraction(10)**6),
    ('giga', Fraction(10)**9),
    ('tera', Fraction(10)**12),
    ('peta', Fraction(10)**15),
    ('exa', Fraction(10)**18),
    ('zetta', Fraction(10)**21),
    ('yotta', Fraction(10)**24),

    ('quarter', Fraction(1, 4)),
)


UNITS = {}


__PhysicalQuantityBase = namedtuple(
    '__PhysicalQuantityBase', ('value', 'unit_vector'))


def _parse_unit_part(unit, elem):
    x = elem.split('^')
    try:
        base_unit = UNITS[x[0]]
    except KeyError:
        raise UnitParseError(
            "Error parsing unit string '%s' (unknown on '%s')" % (unit, x))
    if len(x) == 1:
        return base_unit
    elif len(x) == 2:
        try:
            power = int(x[1])
        except ValueError:
            raise UnitParseError(
                "Error parsing unit string '%s' "
                "(non-integer power '%s' for unit '%s')" % (
                    unit, x[1], x[0]))
        return base_unit._replace(
            value=base_unit.value**power,
            unit_vector=tuple([n * power for n in base_unit.unit_vector]))
    else:
        raise UnitParseError(
            "Error parsing unit string '%s' (error on '%s')" % (unit, x))


def _parse_unit(unit):
    divparts = unit.rsplit('/', 1)
    numerator = divparts[0]
    if len(divparts) == 2:
        denominator = divparts[1]
    else:
        denominator = None
    parts = []
    for elem in numerator.split('*'):
        part = _parse_unit_part(unit, elem)
        parts.append(part)
    if denominator:
        denominator_part = _parse_unit_part(unit, denominator)
        parts.append(part._replace(
            value=Fraction(1) / denominator_part.value,
            unit_vector=tuple([-n for n in denominator_part.unit_vector])))

    multiplier = reduce(operator.mul, [p.value for p in parts], 1)
    unit_vector = tuple(map(sum, zip(*[p.unit_vector for p in parts])))
    return PhysicalQuantity._make((multiplier, unit_vector))


class _UnitCacheDict(dict):
    def __missing__(self, key):
        val = _parse_unit(key)
        self[key] = val
        return val


# cache of PhysicalQuantity(scaling_factor, unit_vector) for unit strings; to
# speed up parsing unit strings...
_unit_cache = _UnitCacheDict()


class PhysicalQuantity(__PhysicalQuantityBase):
    """
    A numeric value with a unit.

    Normal aritmmetic works, provided that units are compatible; i.e.

    >>> PhysicalQuantity(1, 'kilometer') + \
        PhysicalQuantity(1, 'decimeter') == \
        PhysicalQuantity(Decimal('1000.1'), 'meter')
    True

    >>> PhysicalQuantity(1, 'kelvin') - PhysicalQuantity(1, 'ampere')
    Traceback (most recent call last):
    ...
    IncompatibleUnitsError: Incompatible Dimensions 'kelvin' and 'ampere'

    >>> PhysicalQuantity(10, 'meter') * PhysicalQuantity(2, 'meter') == \
        PhysicalQuantity(20, 'meter^2')
    True
    >>> PhysicalQuantity(100, 'gram') / PhysicalQuantity(2, 'meter') == \
        PhysicalQuantity(50, 'gram*meter^-1')
    True

    Internally, values are scaled to SI base units where possible.  The numeric
    value and unit vector are accessible as members ``value`` and
    ``unit_vector``; the unit vector as a human readable string in ``units``.

    >>> PhysicalQuantity(1, 'kilometer').value == 1000
    True
    >>> PhysicalQuantity(1, 'kilometer').units == 'meter'
    True

    For presentation, ``convert`` should be used to get a numeric
    value scaled to some specified unit --- the unit directly
    accessible from the :class:`.PhysicalQuantity` is unlikely to be
    the desired for presentation...

    >>> PhysicalQuantity(150, 'watt').units == 'meter^2*gram*second^-3'
    True
    >>> PhysicalQuantity(150, 'watt').convert('kilowatt') == Fraction('0.150')
    True
    """
    __slots__ = ()

    def __new__(cls, value, unit='none'):
        """
        >>> a = PhysicalQuantity(10, 'meter*second^-1')
        >>> b = PhysicalQuantity(2, 'yard*minute^-1')
        >>> c = a + b
        >>> print(float(c.convert('kilometer*hour^-1')))
        36.109728

        >>> float(PhysicalQuantity(1, 'joule').convert('electronvolt'))
        6.241509343260179e+18

        >>> print("%s %s" % (float(c.value), c.units))
        10.03048 meter*second^-1

        >>> a = PhysicalQuantity(1, 'decimeter^3')
        >>> b = PhysicalQuantity(2, 'liter')
        >>> c = PhysicalQuantity(5, 'gram*centimeter^-3')
        >>> d = (a + b)*c
        >>> print(d.convert('kilogram'))
        15

        Example of formula validation

        >>> a = PhysicalQuantity(10, 'meter*second^-1')
        >>> b = PhysicalQuantity(2, 'yard^3')
        >>> c = a + b
        ... # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
        ...
        IncompatibleUnitsError: Incompatible Dimensions 'meter*second^-1'
                                                        and 'meter^3'

        Examples of more complex formulas

        >>> a = PhysicalQuantity(10, 'meter*second^-1')
        >>> b = PhysicalQuantity(5, 'hour')
        >>> c = a**4 / (7*b)
        >>> print(c)
        5/63 meter^4*second^-5

        Financial application example

        >>> coupon = PhysicalQuantity(200, 'currency_dkk*day^-1')
        >>> expiration = PhysicalQuantity(365, 'day')
        >>> payoff = coupon*expiration
        >>> print(float(payoff.convert('currency_dkk')))
        73000.0

        >>> a = PhysicalQuantity(10, 'meter*second^-2')
        >>> b = PhysicalQuantity(10, 'meter/second^2')
        >>> a == b
        True

        >>> PhysicalQuantity(10, 'meter/second/liter')
        ... # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
        ...
        UnitParseError: Error parsing unit string 'meter/second/liter'
                        (unknown on '[u'meter/second']')

        >>> PhysicalQuantity(10, 'meter/second*liter')
        ... # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
        ...
        UnitParseError: Error parsing unit string 'meter/second*liter'
                        (unknown on '[u'second*liter']')
        """
        if isinstance(value, float) and value != int(value):
            warnings.warn(
                'Constructing PhysicalQuantity from float value %s' % value,
                UnitConversionWarning,
                stacklevel=2)
        if isinstance(unit, tuple):
            # Fix for serialisation/deserialisation issue...
            return PhysicalQuantity._make((Fraction(value), unit))
        base = _unit_cache[unit]
        value = base.value * Fraction(value)
        return base._replace(value=value)

    def __check_unit(self, other):
        if not isinstance(other, PhysicalQuantity):
            raise NotPhysicalQuantityError('%r is not a PhysicalQuantity' % (
                other,))
        if self.unit_vector != other.unit_vector:
            raise IncompatibleUnitsError(
                "Incompatible Dimensions '%s' and '%s'" %
                (self.units, other.units))

    def __add__(self, other):
        """
        >>> a = PhysicalQuantity(2)
        >>> b = PhysicalQuantity(3)
        >>> print(a + b)
        5 none

        >>> print(a + 5)
        Traceback (most recent call last):
        ...
        NotPhysicalQuantityError: 5 is not a PhysicalQuantity
        """
        self.__check_unit(other)
        value = self.value + other.value
        return self._replace(value=value)

    def __neg__(self):
        """
        >>> -PhysicalQuantity(1, 'joule') == PhysicalQuantity(-1, 'joule')
        True
        """
        return self._replace(value=-self.value)

    def __radd__(self, other):
        # NOTE: will currently raise exception...
        return self.__add__(other)

    def __sub__(self, other):
        """
        >>> a = PhysicalQuantity(2)
        >>> b = PhysicalQuantity(3)
        >>> print(a-b)
        -1 none
        """
        self.__check_unit(other)
        value = self.value - other.value
        return self._replace(value=value)

    def __rsub__(self, other):
        # NOTE: will currently raise exception...
        return self.__sub__(other) * (-1)

    def __mul__(self, other):
        """
        >>> print(PhysicalQuantity(2, 'meter') * 1)
        2 meter

        >>> print(PhysicalQuantity(4, 'gram') * PhysicalQuantity(7, 'gram'))
        28 gram^2
        """
        if not isinstance(other, PhysicalQuantity):
            value = self.value * Fraction(other)
            return self._replace(value=value)
        value = self.value * other.value
        unit_vector = map(operator.add, self.unit_vector, other.unit_vector)
        return self._make((value, tuple(unit_vector)))

    def __rmul__(self, other):
        """
        >>> print(3 * PhysicalQuantity(2, 'ampere'))
        6 ampere
        """
        return self.__mul__(other)

    def __div__(self, other):
        """
        >>> print(PhysicalQuantity(2) / 1)
        2 none

        >>> print(PhysicalQuantity(4) / PhysicalQuantity(7, 'second'))
        4/7 second^-1

        >>> print(PhysicalQuantity(4, 'meter') / PhysicalQuantity(2, 'meter'))
        2 none
        """
        if not isinstance(other, PhysicalQuantity):
            value = self.value / Fraction(other)
            return self._replace(value=value)
        elif self.unit_vector == other.unit_vector:
            return PhysicalQuantity(self.value / other.value)
        else:
            value = self.value / other.value
            unit_vector = map(
                operator.sub, self.unit_vector, other.unit_vector)
            return self._make((value, tuple(unit_vector)))

    def __truediv__(self, other):
        return self.__div__(other)

    def __rdiv__(self, other):
        """
        >>> print(1 / PhysicalQuantity(2))
        1/2 none
        """
        return PhysicalQuantity(other) / self

    def __rtruediv__(self, other):
        return PhysicalQuantity(other) / self

    def __pow__(self, other):
        """
        >>> print(PhysicalQuantity(2, 'meter^2')**2)
        4 meter^4
        """
        if not isinstance(other, numbers.Integral):
            raise UnitConversionTypeError("Non-integer power '%r'" % (other,))
        n = int(other)
        unit_vector = [v * n for v in self.unit_vector]
        value = self.value ** n
        return self._make((value, tuple(unit_vector)))

    def __lt__(self, other):
        """
        >>> a = PhysicalQuantity(2, 'meter')
        >>> b = PhysicalQuantity(1, 'kilometer')
        >>> c = PhysicalQuantity(3, 'meter^2')
        >>> a < b
        True
        >>> a < c
        Traceback (most recent call last):
        ...
        IncompatibleUnitsError: Incompatible Dimensions 'meter' and 'meter^2'
        """
        self.__check_unit(other)
        return self.value < other.value

    def __le__(self, other):
        """
        >>> a = PhysicalQuantity(1000, 'meter')
        >>> b = PhysicalQuantity(1, 'kilometer')
        >>> a <= b
        True
        """
        self.__check_unit(other)
        return self.value <= other.value

    def __gt__(self, other):
        """
        >>> a = PhysicalQuantity(1000, 'meter')
        >>> b = PhysicalQuantity(1, 'kilometer')
        >>> a > b
        False
        """
        self.__check_unit(other)
        return self.value > other.value

    def __ge__(self, other):
        """
        >>> a = PhysicalQuantity(1000, 'meter')
        >>> b = PhysicalQuantity(1, 'kilometer')
        >>> a >= b
        True
        """
        self.__check_unit(other)
        return self.value >= other.value

    # note: using inherited __eq__, __ne__ from tuple

    def __nonzero__(self):
        """
        >>> bool(PhysicalQuantity(10, 'meter'))
        True
        >>> bool(PhysicalQuantity(0, 'liter'))
        False
        """
        return bool(self.value)

    @property
    def units(self):
        """
        A human-readable representation of the objects (normalised) unit.
        """
        if all([v == 0 for v in self.unit_vector]):
            return u'none'

        def f(name, n):
            if n == 0:
                return ''
            elif n == 1:
                return name
            else:
                return u'%s^%s' % (name, n)

        return u'*'.join(filter(None, map(f, UNIT_NAMES, self.unit_vector)))

    def convert(self, unit):
        """
        Convert value to a possibly non-normalised but compatible unit,
        returning the resulting numeric value.

        >>> print(PhysicalQuantity(0, 'meter*second^-1').convert('kilometer*hour^-1')) # noqa
        0

        Note that the result is a unitless Fraction, not a PhysicalQuantity

        >>> print(PhysicalQuantity(1, 'kilometer*hour^-1').convert('kilometer*hour^-1').__class__) # noqa
        <class 'fractions.Fraction'>

        >>> PhysicalQuantity(1, 'kilometer').convert('kelvin')
        Traceback (most recent call last):
        ...
        IncompatibleUnitsError: Incompatible Dimensions 'meter' and 'kelvin'

        """
        other = _unit_cache[unit]
        self.__check_unit(other)
        return self.value / other.value

    def compatible_unit(self, unit):
        """
        Check whether the specified unit is a valid conversion target for this
        object, i.e. whether they have the same base units.

        >>> PhysicalQuantity(1, 'meter').compatible_unit('foot')
        True

        >>> PhysicalQuantity(1, 'kilometer').compatible_unit('watt')
        False
        """
        other = _unit_cache[unit]
        return self.unit_vector == other.unit_vector

    @staticmethod
    def compatible_units(unit_a, unit_b):
        """
        Check whether two units specifications are compatible.

        >>> PhysicalQuantity.compatible_units('meter', 'foot')
        True

        >>> PhysicalQuantity.compatible_units('meter', 'watt')
        False
        """
        return _unit_cache[unit_a].unit_vector == \
            _unit_cache[unit_b].unit_vector

    @staticmethod
    def same_unit(unit_a, unit_b):
        """
        Check whether to unit specifications specify the same unit.

        >>> PhysicalQuantity.same_unit('meter*meter', 'meter^2')
        True

        >>> PhysicalQuantity.same_unit('meter', 'foot')
        False

        >>> PhysicalQuantity.same_unit('meter', 'kelvin')
        False
        """
        a = _unit_cache[unit_a]
        b = _unit_cache[unit_b]
        return a.unit_vector == b.unit_vector and a.value == b.value

    def __repr__(self):
        if self.value.denominator == 1:
            n = self.value.numerator
        else:
            n = self.value
        return 'PhysicalQuantity(%r, %r)' % (n, self.units)

    def __str__(self):
        return '%s %s' % (self.value, self.units)

    def __reduce__(self):
        return (PhysicalQuantity, (str(self.value), self.unit_vector))


def register_unit(name, value):
    """
    Define a new input unit, equal to some expression in already existing
    units.

    @param name: Name of new unit.
    @param value: Pair of (number, dimensions), where dimensions is (as)
    interpreted by the PhysicalQuantity constructor.

    @precondition: Unit ``name`` not already registered.

    Example use:
        register_unit('lightyear', (9460730472580800, 'meter'))
        PhysicalQuantity(200, 'lightyear').convert('mile')
    """
    if name in UNITS:
        return
    for prefix, scale in SCALES:
        assert not name.startswith(prefix), \
            'Unit %s appears to include prefix %s' % (name, prefix)
    n, unit = value

    if isinstance(unit, basestring):
        # new unit from existing
        v = PhysicalQuantity(n, unit)
    else:
        assert isinstance(unit, tuple)
        # base unit
        v = PhysicalQuantity._make((Fraction(n), unit))

    UNITS[name] = v
    for prefix, scale in SCALES:
        UNITS[prefix + name] = v._replace(value=v.value*scale)


for name, value in BASE_UNITS.items():
    register_unit(name, value)


# http://en.wikipedia.org/wiki/SI_derived_unit
SI_DERIVED_UNITS = OrderedDict([
    ('hertz', (1, 'second^-1')),
    ('radian', (1, 'none')),
    ('steradian', (1, 'none')),
    ('newton', (1, 'kilogram*meter*second^-2')),
    ('pascal', (1, 'newton*meter^-2')),
    ('joule', (1, 'newton*meter')),
    ('watt', (1, 'joule*second^-1')),
    ('coulomb', (1, 'second*ampere')),
    ('volt', (1, 'watt*ampere^-1')),
    ('farad', (1, 'coulomb*volt^-1')),
    ('ohm', (1, 'volt*ampere^-1')),
    ('siemens', (1, 'ohm^-1')),
    ('weber', (1, 'joule*ampere^-1')),
    ('tesla', (1, 'volt*second*meter^-2')),
    ('henry', (1, 'volt*second*ampere^-1')),
    # degree celsius not added...
    ('lumen', (1, 'candela*steradian')),
    ('lux', (1, 'lumen*meter^-2')),
    ('becquerel', (1, 'second^-1')),
    ('gray', (1, 'joule*kilogram^-1')),
    ('sievert', (1, 'joule*kilogram^-1')),
    ('katal', (1, 'mole*second^-1')),
])


for name, value in SI_DERIVED_UNITS.items():
    register_unit(name, value)


# http://en.wikipedia.org/wiki/Non-SI_units_accepted_for_use_with_SI
COMMON_UNITS = OrderedDict([
    # widely used
    ('minute', (60, 'second')),
    ('hour', (60, 'minute')),
    ('day', (24, 'hour')),
    ('hectare', (1, 'hectometer^2')),
    ('litre', (1, 'decimeter^3')),
    ('liter', (1, 'decimeter^3')),
    ('tonne', (1000, 'kilogram')),
    # experimentally determined
    ('electronvolt', (Decimal('1.602176565e-19'), 'joule')),
    ('dalton', (Decimal('1.66053886e-27'), 'kilogram')),
    ('astronomical_unit', (Decimal('1.4959787069e11'), 'meter')),
    # not officially sanctioned
    ('angstrom', (Decimal('1e-10'), 'meter')),
    ('are', (100, 'meter^2')),
    ('barn', (Decimal('1e-28'), 'meter^2')),
    ('bar', (10**5, 'pascal')),
    ('atmosphere', (101325, 'pascal')),
    ('barye', (Decimal('0.1'), 'pascal')),
    ('torr', (Fraction(1, 760), 'atmosphere')),
])


for name, value in COMMON_UNITS.items():
    register_unit(name, value)


# http://en.wikipedia.org/wiki/United_States_customary_units
OTHER_UNITS = OrderedDict([
    # International
    ('inch', (Decimal('2.54'), 'centimeter')),
    ('foot', (12, 'inch')),
    ('yard', (3, 'foot')),
    ('mile', (1760, 'yard')),
    # US Survey
    ('survey_foot', (Fraction(1200, 3937), 'meter')),
    ('link', (Fraction(33, 50), 'survey_foot')),
    ('rod', (25, 'link')),
    ('chain', (4, 'rod')),
    ('furlong', (10, 'chain')),
    ('survey_mile', (8, 'furlong')),
    ('league', (3, 'survey_mile')),
    # Nautical
    ('fathom', (2, 'yard')),
    ('cable', (1, 'fathom')),
    ('nautical_mile', (Decimal('1.852'), 'kilometer')),
    # Area
    ('acre', (10, 'chain^2')),
    ('section', (1, 'survey_mile^2')),
    ('survey_township', (4, 'league^2')),
    # Fluid Volume
    ('minim', (Decimal('61.611519921875'), 'microlitre')),
    ('us_fluid_dram', (60, 'minim')),
    ('teaspoon', (80, 'minim')),
    ('tablespoon', (3, 'teaspoon')),
    ('us_fluid_ounce', (2, 'tablespoon')),
    ('us_shot', (3, 'tablespoon')),
    ('us_gill', (4, 'us_fluid_ounce')),
    ('us_cup', (2, 'us_gill')),
    ('liquid_us_pint', (2, 'us_cup')),
    ('liquid_us_quart', (2, 'liquid_us_pint')),
    ('liquid_us_gallon', (4, 'liquid_us_quart')),
    ('liquid_barrel', (Decimal('31.5'), 'liquid_us_gallon')),
    ('oil_barrel', (42, 'liquid_us_gallon')),
    ('hogshead', (63, 'liquid_us_gallon')),
    # Dry Volume
    ('dry_gallon', (Decimal('268.8025'), 'inch^3')),
    ('dry_quart', (Fraction(1, 4), 'dry_gallon')),
    ('dry_pint', (Fraction(1, 2), 'dry_quart')),
    ('peck', (2, 'dry_gallon')),
    ('bushel', (4, 'peck')),
    ('dry_barrel', (7056, 'inch^3')),
    # Mass (avoirdupois)
    ('pound', (Decimal('453.59237'), 'gram')),
    ('ounce', (Fraction(1, 16), 'pound')),
    ('dram', (Fraction(1, 16), 'ounce')),
    ('grain', (Fraction(1, 7000), 'pound')),
    ('us_hundredweight', (100, 'pound')),
    ('long_hundredweight', (112, 'pound')),
    ('short_ton', (20, 'us_hundredweight')),
    ('long_ton', (20, 'long_hundredweight')),
    # ...
    ('rankine', (Fraction(5, 9), 'kelvin')),
    ('percent', (Fraction(1, 100), 'none')),
])


for name, value in OTHER_UNITS.items():
    register_unit(name, value)


_unit_cache[''] = _unit_cache['none']


def simple_convert(number, from_unit, to_unit):
    """
    >>> simple_convert(1000, 'meter', 'kilometer')
    Fraction(1, 1)
    """
    return PhysicalQuantity(number, from_unit).convert(to_unit)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
