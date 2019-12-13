# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.utils import utilitytypes

from .fields import DataRoleField


def default_unit_for_data_series(data_role, utility_type=None):
    """
    Default unit for L{DataSeries} given a data role and optionally a data
    origin.

    @param data_role: A data role (see L{DataRoleField}) to lookup the
    default data series unit for.

    @param utility_type: A member of L{utilitytypes.METER_CHOICES} to
    further narrow down the default data series unit.

    @precondition: The C{utility_type} argument is required for
    C{DataRoleField.CONSUMPTION} and C{DataRoleField.CO2_QUOTIENT}
    C{data_role}s, and otherwise ignored.

    @precondition: When C{utility_type} is given it must be in
    L{utilitytypes.METER_CHOICES}.

    @return: Returns a default unit for L{DataSeries} in the form of a
    L{buckingham} unit string.

    @deprecated: Some data roles may be meaningfull with different units
    that are not compatible with each other.  Most of the time we would be
    better of not to use this method at all.
    """
    assert utility_type is None or utility_type in (
        db_value for db_value, _ in utilitytypes.METER_CHOICES), \
        'invalid utility_type %d for this function' % utility_type

    assert data_role not in \
        [DataRoleField.CONSUMPTION] or \
        utility_type is not None, 'utility_type required for ' \
        'data_role %d' % data_role

    unit_map = {
        DataRoleField.CO2: 'gram',
        DataRoleField.CURRENT: 'milliampere',
        DataRoleField.EMPLOYEES: 'none',
        DataRoleField.FREQUENCY: 'millihertz',
        DataRoleField.MASS: 'gram',
        DataRoleField.POWER: 'milliwatt',
        DataRoleField.PRESSURE: 'millibar',
        DataRoleField.STATE: 'none',
        DataRoleField.ABSOLUTE_TEMPERATURE: 'millikelvin',
        DataRoleField.RELATIVE_TEMPERATURE: 'millikelvin',
        DataRoleField.TIME: 'second',
        DataRoleField.VOLTAGE: 'millivolt',
        DataRoleField.VOLUME_FLOW: 'milliliter*hour^-1',
    }

    if utility_type in [utilitytypes.METER_CHOICES.electricity,
                        utilitytypes.METER_CHOICES.district_heating]:
        unit_map.update({
            DataRoleField.CONSUMPTION: 'milliwatt*hour',
            DataRoleField.PRODUCTION_ENPI: 'milliwatt*hour*unit^-1'
        })
    elif utility_type == utilitytypes.METER_CHOICES.gas:
        unit_map.update({
            DataRoleField.CONSUMPTION: 'milliliter',
            DataRoleField.PRODUCTION_ENPI: 'milliliter*unit^-1'
        })
    elif utility_type in [utilitytypes.METER_CHOICES.water,
                          utilitytypes.METER_CHOICES.oil]:
        unit_map.update({
            DataRoleField.CONSUMPTION: 'milliliter',
            DataRoleField.PRODUCTION_ENPI: 'milliliter*unit^-1'
        })
    return unit_map[data_role]
