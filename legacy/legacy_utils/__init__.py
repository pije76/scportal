# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.utils import utilitytypes
from legacy.measurementpoints.fields import DataRoleField


def get_customer_preferred_unit_attribute_name(
        customer, role, utility_type=None):
    """
    Get preferred attribute unit name for given role and resource type.

    @param role: The given DataRoleField value.

    @param utility_type: The given resource type, as defined by the
    L{utilitytypes.OPTIONAL_METER_CHOICES}.  If not given
    C{utilitytypes.OPTIONAL_METER_CHOICES.unknown} is assumed.

    @return: Returns either a valid field name, or C{None}.
    """
    if not utility_type:
        utility_type = utilitytypes.OPTIONAL_METER_CHOICES.unknown

    result = None
    if role in (DataRoleField.HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION,
                DataRoleField.CONSUMPTION):
        if utility_type == utilitytypes.OPTIONAL_METER_CHOICES.electricity:
            result = 'electricity_consumption'
        elif utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.district_heating:
            result = 'heat_consumption'
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.gas:
            result = 'gas_consumption'
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.water:
            result = 'water_consumption'
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.oil:
            result = 'oil_consumption'
    elif role == DataRoleField.POWER:
        if utility_type == utilitytypes.OPTIONAL_METER_CHOICES.electricity:
            result = 'electricity_instantaneous'
        elif utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.district_heating:
            result = 'heat_instantaneous'
    elif role == DataRoleField.VOLUME_FLOW:
        if utility_type == utilitytypes.OPTIONAL_METER_CHOICES.water:
            result = 'water_instantaneous'
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.gas:
            result = 'gas_instantaneous'
        elif utility_type == utilitytypes.OPTIONAL_METER_CHOICES.oil:
            result = 'oil_instantaneous'
    elif role == DataRoleField.VOLUME:
        if utility_type == \
                utilitytypes.OPTIONAL_METER_CHOICES.district_heating:
            result = 'water_consumption'
    elif role in [DataRoleField.ABSOLUTE_TEMPERATURE,
                  DataRoleField.RELATIVE_TEMPERATURE,
                  DataRoleField.MEAN_COOLDOWN_TEMPERATURE]:
        result = 'temperature'

    if result is not None:
        assert hasattr(customer, result)
    return result
