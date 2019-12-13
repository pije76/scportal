# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import re

from gridplatform.trackuser import get_customer
from gridplatform.utils import choices_extract_python_identifier
from gridplatform.utils import utilitytypes
from gridplatform.utils.preferredunits import AbsoluteCelsiusUnitConverter
from gridplatform.utils.preferredunits import AbsoluteFahrenheitUnitConverter
from gridplatform.utils.preferredunits import AreaENPIUnitConverter
from gridplatform.utils.preferredunits import EfficiencyUnitConverter
from gridplatform.utils.preferredunits import PersonsENPIUnitConverter
from gridplatform.utils.preferredunits import PhysicalQuantity
from gridplatform.utils.preferredunits import PhysicalUnitConverter
from gridplatform.utils.preferredunits import ProductionAENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionBENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionCENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionDENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionEENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionUnitConverter
from gridplatform.utils.preferredunits import RelativeCelsiusUnitConverter
from gridplatform.utils.preferredunits import RelativeFahrenheitUnitConverter
from gridplatform.utils.preferredunits import KvarUnitConverter
from gridplatform.utils.preferredunits import KvarhUnitConverter
from gridplatform.utils.preferredunits import PowerFactorUnitConverter
from legacy.measurementpoints.fields import DataRoleField


def get_preferred_unit_converter(
        role, utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
        customer=None, unit=None):
    """
    Get preferred unit converter for the given arguments.

    @param role: A data role as defined in L{DataRoleField.CHOICES}

    @keyword utility_type: An optional utility type as defined in
    L{utilitytypes.METER_CHOICES}.

    @keyword customer: An optional customer instance.  This is required in
    contexts such as Celery tasks, where get_customer() does not work.

    @precondition: If C{customer} is not given, get_customer() returns a
    Customer instance.

    @raise ValueError: This exception is raised if no preferred unit object can
    be found for the given arguments.
    """
    if customer is None:
        customer = get_customer()
    assert customer is not None

    assert role in (db_value for db_value, _ in DataRoleField.CHOICES)
    assert utility_type in (db_value for db_value, _ in
                            utilitytypes.OPTIONAL_METER_CHOICES), utility_type

    if role == DataRoleField.RELATIVE_TEMPERATURE:
        if customer.temperature == 'celsius':
            return RelativeCelsiusUnitConverter()
        elif customer.temperature == 'fahrenheit':
            return RelativeFahrenheitUnitConverter()

    elif role == DataRoleField.ABSOLUTE_TEMPERATURE:
        if customer.temperature == 'celsius':
            return AbsoluteCelsiusUnitConverter()
        elif customer.temperature == 'fahrenheit':
            return AbsoluteFahrenheitUnitConverter()

    elif role in (DataRoleField.CONSUMPTION,
                  DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION):
        if utility_type == utilitytypes.OPTIONAL_METER_CHOICES.electricity:
            return PhysicalUnitConverter(customer.electricity_consumption)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.gas:
            return PhysicalUnitConverter(customer.gas_consumption)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.water:
            return PhysicalUnitConverter(customer.water_consumption)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.oil:
            return PhysicalUnitConverter(customer.oil_consumption)
        elif utility_type == utilitytypes.METER_CHOICES.district_heating:
            return PhysicalUnitConverter(customer.heat_consumption)

    elif role == DataRoleField.POWER:
        if utility_type == utilitytypes.OPTIONAL_METER_CHOICES.electricity:
            return PhysicalUnitConverter(customer.electricity_instantaneous)
        elif utility_type == utilitytypes.METER_CHOICES.district_heating:
            return PhysicalUnitConverter(customer.heat_instantaneous)

    elif role == DataRoleField.REACTIVE_POWER:
        return KvarUnitConverter()

    elif role == DataRoleField.REACTIVE_ENERGY:
        return KvarhUnitConverter()

    elif role == DataRoleField.POWER_FACTOR:
        return PowerFactorUnitConverter()

    elif role == DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES:
        if utility_type == utilitytypes.OPTIONAL_METER_CHOICES.electricity:
            return PersonsENPIUnitConverter(customer.electricity_consumption)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.gas:
            return PersonsENPIUnitConverter(customer.gas_consumption)
        elif utility_type == utilitytypes.METER_CHOICES.district_heating:
            return PersonsENPIUnitConverter(customer.heat_consumption)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.oil:
            return PersonsENPIUnitConverter(customer.oil_consumption)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.water:
            return PersonsENPIUnitConverter(customer.water_consumption)

    elif role == DataRoleField.CONSUMPTION_UTILIZATION_AREA:
        if utility_type == utilitytypes.OPTIONAL_METER_CHOICES.electricity:
            return AreaENPIUnitConverter(customer.electricity_consumption)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.gas:
            return AreaENPIUnitConverter(customer.gas_consumption)
        elif utility_type == utilitytypes.METER_CHOICES.district_heating:
            return AreaENPIUnitConverter(customer.heat_consumption)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.oil:
            return AreaENPIUnitConverter(customer.oil_consumption)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.water:
            return AreaENPIUnitConverter(customer.water_consumption)

    elif role == DataRoleField.VOLUME_FLOW:
        if utility_type == utilitytypes.OPTIONAL_METER_CHOICES.gas:
            return PhysicalUnitConverter(customer.gas_instantaneous)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.oil:
            return PhysicalUnitConverter(customer.oil_instantaneous)
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.water:
            return PhysicalUnitConverter(customer.water_instantaneous)

    elif role == DataRoleField.COST and unit is not None:
        normalized_unit = PhysicalQuantity(1, unit).units
        assert re.match('currency_[a-z]{3}', normalized_unit)
        return PhysicalUnitConverter(normalized_unit)

    elif role == DataRoleField.HEATING_DEGREE_DAYS:
        return PhysicalUnitConverter('kelvin*day')

    elif role == DataRoleField.CO2:
        return PhysicalUnitConverter('tonne')

    elif role == DataRoleField.VOLTAGE:
        return PhysicalUnitConverter('volt')

    elif role == DataRoleField.CURRENT:
        return PhysicalUnitConverter('ampere')

    elif role == DataRoleField.PRODUCTION:
        return ProductionUnitConverter(unit)

    elif role == DataRoleField.PRODUCTION_ENPI:
        if unit.endswith('production_a^-1'):
            return ProductionAENPIUnitConverter(
                unit[:-len('*production_a^-1')])
        elif unit.endswith('production_b^-1'):
            return ProductionBENPIUnitConverter(
                unit[:-len('*production_b^-1')])
        elif unit.endswith('production_c^-1'):
            return ProductionCENPIUnitConverter(
                unit[:-len('*production_c^-1')])
        elif unit.endswith('production_d^-1'):
            return ProductionDENPIUnitConverter(
                unit[:-len('*production_d^-1')])
        elif unit.endswith('production_e^-1'):
            return ProductionEENPIUnitConverter(
                unit[:-len('*production_e^-1')])

    elif role == DataRoleField.HEAT_LOSS_COEFFICIENT:
        return PhysicalUnitConverter('watt*kelvin^-1')

    elif role == DataRoleField.MEAN_COOLDOWN_TEMPERATURE:
        if customer.temperature == 'celsius':
            return RelativeCelsiusUnitConverter()
        elif customer.temperature == 'fahrenheit':
            return RelativeFahrenheitUnitConverter()

    elif role == DataRoleField.VOLUME and \
            utility_type == utilitytypes.METER_CHOICES.district_heating:
        return PhysicalUnitConverter(customer.water_consumption)

    elif role == DataRoleField.EFFICIENCY:
        return EfficiencyUnitConverter()

    raise ValueError(
        'A preferred unit object for role=%s and utility_type=%s '
        'is not defined.' % (
            unicode(dict(DataRoleField.CHOICES)[role]),
            choices_extract_python_identifier(
                utilitytypes.OPTIONAL_METER_CHOICES, utility_type)))
