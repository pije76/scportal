"""Data types used for members in message objects on the Python side."""

# also used outside the protocol module --- but in code depending on the
# protocol module, so extracting this to a separate module/repository would not
# provide any clear benefits

from collections import namedtuple

# Measurement data format:
#
# list of "meter_data"
# meter_data: "meter_id", list of "measurement_set"
# meter_id: "connection_type", "id_number"
# connection_type: enum;
#   "unknown",
#   "ZigBee",
#   "MBus primary",
#   "MBus secondary",
#   "Kamstrup UtiliDriver"
#   ...?
# id_number: a local numeric ID specific to the connection technology
# measurement_set: timestamp, list of "measurement"
# measurement: "type", "unit", "input number", "value"
# type: enum;
#   "unknown",
#   "electricity consumption",
#   ... (whatever from M-Bus medium)
# unit: enum; "unknown", "mWh", "mW", ...?

MeterData = namedtuple('MeterData', ['meter', 'measurement_sets'])
Meter = namedtuple('Meter', ['connection_type', 'id'])
MeasurementSet = namedtuple('MeasurementSet', ['timestamp', 'measurements'])
Measurement = namedtuple('Measurement',
                         ['type', 'unit', 'input_number', 'value'])

Rule = namedtuple('Rule', ['relay_on', 'start_time', 'end_time'])
RuleSet = namedtuple('RuleSet', ['override_timeout', 'rules', 'meters'])
Price = namedtuple('Price', ['start_timestamp', 'end_timestamp', 'price'])

Version = namedtuple(
    'Version', ['major', 'minor', 'revision', 'revisionstring'])

connection_types = [
    'unknown',
    'ZigBee',
    'MBus primary',
    # Meter IDs in MBus GM legacy follow a spec. from the old GridPortal 1.5
    # days. This should be removed in future software version of the GridAgents
    'MBus GM legacy',
    'Kamstrup UtiliDriver',
    'PLC Mitsubishi FX1S',
    'Modbus',
    'Aux Serial',
    'MBus secondary',
]

measurement_types = [
    'unknown',
    'electricity',
    'heat',
]

measurement_units = [
    'unknown',
    'mWh',
    'mW',
    'pulse count',
    'um^3',
    'um^3/h',
    'mdegC',
    'mV',
    'mA',
    'mHz',
    'g',
    'mbar',
    's',
]
