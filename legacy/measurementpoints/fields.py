# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from south.modelsinspector import add_introspection_rules


class DataRoleField(models.IntegerField):
    """
    A C{DataRoleField} holds the role of some data, such as a L{DataSeries} or
    a L{Graph}.
    """

    CONSUMPTION = 0
    POWER = 1
    # 2 is taken! Scroll down!
    COST = 3
    VOLUME_FLOW = 4
    VOLTAGE = 5
    CURRENT = 6
    FREQUENCY = 7
    MASS = 8
    PRESSURE = 9
    TIME = 10
    STATE = 11
    HEAT_TARIFF = 12
    GAS_TARIFF = 13
    ELECTRICITY_TARIFF = 14
    WATER_TARIFF = 15
    CO2_QUOTIENT = 16
    EMPLOYEES = 17
    CACHE = 18
    # 19 is taken! Scroll down!
    # No, really; scroll down; it's not just 19; the list actually continues...
    #
    # All temperatures can be stored in Kelvin, but unit conversions change
    # depending on the temperature being relative or absolute.  Mostly because
    # Celsius and Fahrenheit are bogus units.
    #
    # For relative temperatures: Kelvin == Celsius == (5/9) * Fahrenheit
    RELATIVE_TEMPERATURE = 2  # < must equal 2 for historical reasons.
    #
    # For absolute temperatures: Kelvin == Celsius + 273.15 == (5/9) *
    # (Fahrenheit + 459.67)
    ABSOLUTE_TEMPERATURE = 19
    STANDARD_HEATING_DEGREE_DAYS = 20
    HEATING_DEGREE_DAYS = 21
    HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION = 22
    #
    AREA = 23
    CO2 = 24
    VOLUME = 25  # < if volume consumed, use CONSUMPTION instead.
    MEAN_COOLDOWN_TEMPERATURE = 26  # < relative temp. that is piecewise const.
    OIL_TARIFF = 27
    ENERGY_DRIVER = 28
    PRODUCTION = 29
    REACTIVE_POWER = 30
    REACTIVE_ENERGY = 31
    POWER_FACTOR = 32

    HIDDEN = 100
    HIDDEN_ELECTRICITY_TARIFF = 101
    HIDDEN_GAS_TARIFF = 102
    HIDDEN_HEAT_TARIFF = 103
    HIDDEN_WATER_TARIFF = 104
    HIDDEN_OIL_TARIFF = 105

    CONSUMPTION_UTILIZATION_EMPLOYEES = 200
    CONSUMPTION_UTILIZATION_AREA = 201
    PRODUCTION_ENPI = 202
    HEAT_LOSS_COEFFICIENT = 203

    LINEAR_REGRESSION = 300

    EFFICIENCY = 400

    CHOICES = (
        (CONSUMPTION, _(u"Consumption")),
        (POWER, _(u"Power")),
        (REACTIVE_POWER, _(u"Reactive power")),
        (REACTIVE_ENERGY, _(u"Reactive energy")),
        (POWER_FACTOR, _(u"Power factor")),
        (RELATIVE_TEMPERATURE, _(u"Relative temperature")),
        (ABSOLUTE_TEMPERATURE, _(u'Absolute temperature')),
        (COST, _(u"Cost")),
        (VOLUME, _(u'Volume')),
        (VOLUME_FLOW, _(u"Volume flow")),
        (VOLTAGE, _(u"Voltage")),
        (CURRENT, _(u"Current")),
        (FREQUENCY, _(u"Frequency")),
        (MASS, _(u"Mass")),
        (PRESSURE, _(u"Pressure")),
        (TIME, _(u"Time")),
        (STATE, _(u"State")),
        (HEAT_TARIFF, _('Heat tariff')),
        (GAS_TARIFF, _('Gas tariff')),
        (ELECTRICITY_TARIFF, _('Electricity tariff')),
        (WATER_TARIFF, _('Water tariff')),
        (CO2_QUOTIENT, _(u'CO₂ quotient')),
        (EMPLOYEES, _('Employees')),
        (CACHE, _('Cached data series')),
        (HIDDEN, _('Hidden data series')),
        (STANDARD_HEATING_DEGREE_DAYS, _('Standard heating degree days')),
        (HEATING_DEGREE_DAYS, _('Heating degree days')),
        (HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION,
         _(u'Heating degree days corrected consumption')),
        (AREA, _('Area')),
        (CO2, _('CO₂')),
        (HIDDEN_ELECTRICITY_TARIFF, _('Hidden electricity tariff')),
        (HIDDEN_GAS_TARIFF, _('Hidden gas tariff')),
        (HIDDEN_HEAT_TARIFF, _('Hidden heat tariff')),
        (HIDDEN_WATER_TARIFF, _('Hidden water tariff')),
        (CONSUMPTION_UTILIZATION_EMPLOYEES,
         _('Consumption utilisation according to number of employees')),
        (CONSUMPTION_UTILIZATION_AREA,
         _('Consumption utilisation according to area')),
        (PRODUCTION_ENPI, _('Production EnPI')),
        (MEAN_COOLDOWN_TEMPERATURE, _(u'Mean cool-down temperature')),
        (OIL_TARIFF, _(u'Oil tariff')),
        (HIDDEN_OIL_TARIFF, _(u'Hidden oil tariff')),
        (LINEAR_REGRESSION, _(u'Linear regression')),
        (ENERGY_DRIVER, _(u'Energy driver')),
        (PRODUCTION, _(u'Production')),
        (HEAT_LOSS_COEFFICIENT, _('Heat loss coefficient')),
        (EFFICIENCY, _('Efficiency')),
    )

    TARIFFS = [HEAT_TARIFF, GAS_TARIFF,
               ELECTRICITY_TARIFF, WATER_TARIFF, OIL_TARIFF]

    def __init__(self, verbose_name=_(u"Role"), choices=CHOICES,
                 *args, **kwargs):
        """
        Construct a C{DataRoleField} as an C{IntegerField} with certain default
        arguments.
        """
        super(DataRoleField, self).__init__(
            verbose_name, *args, choices=choices, **kwargs)

    @staticmethod
    def hidden_tariff_for_role(role):
        """
        Return hidden tariff role

        @param role: DataRoleField tariff role
        """
        hidden_tariffs = {
            DataRoleField.ELECTRICITY_TARIFF:
            DataRoleField.HIDDEN_ELECTRICITY_TARIFF,
            DataRoleField.HEAT_TARIFF:
            DataRoleField.HIDDEN_HEAT_TARIFF,
            DataRoleField.GAS_TARIFF:
            DataRoleField.HIDDEN_GAS_TARIFF,
            DataRoleField.WATER_TARIFF:
            DataRoleField.HIDDEN_WATER_TARIFF,
            DataRoleField.OIL_TARIFF:
            DataRoleField.HIDDEN_OIL_TARIFF,
        }
        return hidden_tariffs[role]


add_introspection_rules([], [
    "^legacy\.measurementpoints\.fields\.DataRoleField"])
