import unittest
import datetime
import ctypes
from collections import namedtuple
from StringIO import StringIO
import random

from messages import parse
from datatypes import MeterData, Meter, MeasurementSet, Measurement
import messages

from client_messages import (
    BulkMeasurements,
    NotificationGaAddMode,
    NotificationGaTime,
    NotificationGaConnectedSet,
    NotificationGpState,
)


def parse_message(data, version):
    stream = StringIO(data)
    return parse(stream, version)

ConnectionMock = namedtuple('ConnectionMock', ['agent_mac'])

# NOTE: checking class names is perhaps silly, when what actually matters is
# the behaviour on message.process() --- but we really want to test parsing by
# itself, and checking the behaviour of process() requires a more complex test
# setup in that it may lead to more messages being sent, interaction with the
# database, interaction with the portal...


def cast_signed(val):
    return ctypes.c_longlong(val).value


class TestParsingVersion1(unittest.TestCase):
    def test_bulk_measurements(self):
        data = str(bytearray([
            0x00, 0x00, 0x00, 0x48,  # length
            0x00, 0x00,  # padding
            0,  # type
            0x01,  # flags (is last)
            0x00, 0x00,  # padding
            0x00, 0x03,  # count
            0xAA, 0xAA, 0xAA, 0xAA, 0xBB, 0xBB, 0xBB, 0xBB,  # id
            0xAB, 0xCD, 0xAB, 0xCD,  # timestamp
            0x00, 0x00, 0x00, 0x00, 0x11, 0x11, 0x11, 0x11,  # value
            0xAA, 0xAA, 0xAA, 0xAA, 0xBB, 0xBB, 0xBB, 0xBB,  # id
            0xAB, 0xCD, 0xAB, 0xEF,  # timestamp
            0x00, 0x00, 0x00, 0x00, 0x22, 0x22, 0x22, 0x22,  # value
            0xCC, 0xCC, 0xCC, 0xCC, 0xDD, 0xDD, 0xDD, 0xDD,  # id
            0x12, 0x34, 0x12, 0x34,  # timestamp
            0x00, 0x00, 0x00, 0x00, 0x33, 0x33, 0x33, 0x33,  # value
        ]))
        message = parse_message(data, 1)
        self.assertEqual(len(message.meter_data), 2)
        self.assertEqual(message.meter_data[0].meter.id,
                         cast_signed(0xAAAAAAAABBBBBBBB))
        self.assertEqual(message.meter_data[1].meter.id,
                         cast_signed(0xCCCCCCCCDDDDDDDD))
        self.assertEqual(len(message.meter_data[0].measurement_sets), 2)
        self.assertEqual(len(message.meter_data[0].measurement_sets[0]
                             .measurements), 1)
        self.assertEqual(message.meter_data[0].measurement_sets[0]
                         .measurements[0].type, 0)
        self.assertEqual(message.meter_data[0].measurement_sets[0]
                         .measurements[0].unit, 0)
        self.assertEqual(message.meter_data[0].measurement_sets[0]
                         .measurements[0].input_number, 0)
        self.assertEqual(message.meter_data[0].measurement_sets[0]
                         .measurements[0].value,
                         cast_signed(0x0000000011111111))
        self.assertEqual(message.meter_data[0].measurement_sets[1]
                         .measurements[0].value,
                         cast_signed(0x0000000022222222))
        self.assertEqual(message.meter_data[1].measurement_sets[0]
                         .measurements[0].value,
                         cast_signed(0x0000000033333333))
        self.assertEqual(message.meter_data[0].measurement_sets[1].timestamp -
                         message.meter_data[0].measurement_sets[0].timestamp,
                         datetime.timedelta(seconds=34))
        self.assertEqual(message.__class__.__name__, 'BulkMeasurements')

    def test_notification_ga_add_mode(self):
        data = str(bytearray([
            0x00, 0x00, 0x00, 0x0C,  # length
            0x00, 0x00,  # padding
            11,  # type
            0x00,  # flags (not in add mode)
            0x00, 0x00, 0xA4, 0xB2,  # time; 11:42:42
        ]))
        message = parse_message(data, 1)
        self.assertEqual(message.in_add_mode, False)
        self.assertEqual(message.timestamp,
                         datetime.datetime(2000, 1, 1, 11, 42, 42))
        self.assertEqual(message.__class__.__name__, 'NotificationGaAddMode')

    def test_notification_ga_time(self):
        data = str(bytearray([
            0x00, 0x00, 0x00, 0x0C,  # length
            0x00, 0x00,  # padding
            12,  # type
            0x00,  # flags
            0x00, 0x00, 0xA4, 0xB2,  # time; 11:42:42
        ]))
        message = parse_message(data, 1)
        self.assertEqual(message.timestamp,
                         datetime.datetime(2000, 1, 1, 11, 42, 42))
        self.assertEqual(message.__class__.__name__, 'NotificationGaTime')

    def test_notification_ga_connected_set(self):
        data = str(bytearray([
            0x00, 0x00, 0x00, 0x1C,  # length
            0x00, 0x00,  # padding
            13,  # type
            0x00,  # flags
            0x00, 0x00, 0x00, 0x02,  # count
            0xAA, 0xAA, 0xAA, 0xAA, 0xBB, 0xBB, 0xBB, 0xBB,  # id
            0xCC, 0xCC, 0xCC, 0xCC, 0xDD, 0xDD, 0xDD, 0xDD,  # id
        ]))
        message = parse_message(data, 1)
        self.assertEqual(len(message.meters), 2)
        self.assertEqual(message.meters[0].id,
                         cast_signed(0xAAAAAAAABBBBBBBB))
        self.assertEqual(message.meters[1].id,
                         cast_signed(0xCCCCCCCCDDDDDDDD))
        self.assertEqual(message.__class__.__name__,
                         'NotificationGaConnectedSet')

    def test_notification_gp_state(self):
        data = str(bytearray([
            0x00, 0x00, 0x00, 0x14,  # length
            0x00, 0x00,  # padding
            14,  # type
            0x03,  # flags (connected, manual mode, relay off)
            0x00, 0x00, 0xA4, 0xB2,  # time; 11:42:42
            0xFF, 0xEE, 0xFF, 0xFF, 0x00, 0x00, 0x11, 0x00,  # id
        ]))
        message = parse_message(data, 1)
        self.assertEqual(message.online, True)
        self.assertEqual(message.control_manual, True)
        self.assertEqual(message.relay_on, False)
        self.assertEqual(message.timestamp,
                         datetime.datetime(2000, 1, 1, 11, 42, 42))
        meter_id = cast_signed(0xFFEEFFFF00001100)
        self.assertEqual(message.meter, Meter(0, meter_id))
        self.assertEqual(message.__class__.__name__, 'NotificationGpState')


# messages send timestamp as second; i.e. output will *not* match the
# microsecond of input if we use timestamps with microseconds...
def utcsecond():
    return datetime.datetime.utcnow().replace(microsecond=0)


class TestRoundtripVersion2(unittest.TestCase):
    def test_bulk_measurements(self):
        data = [MeterData(Meter(0, 0xaabbcc),
                          [MeasurementSet(utcsecond(),
                                          [Measurement(0, 0, 5, 123456),
                                           Measurement(0, 0, 9, 456789)]),
                           MeasurementSet((utcsecond() +
                                           datetime.timedelta(hours=1)),
                                          [Measurement(0, 0, 9, 123457),
                                           Measurement(0, 0, 5, 456788)])]),
                MeterData(Meter(0, 0xccddee),
                          [MeasurementSet(utcsecond(),
                                          [Measurement(0, 0, 1, 123),
                                           Measurement(0, 0, 3, 789)])])]
        bytes = StringIO()
        messages.write(bytes, BulkMeasurements(data), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.meter_data, data)
        self.assertEqual(message.__class__, BulkMeasurements)

    def test_notification_ga_add_mode(self):
        timestamp = utcsecond()
        in_add_mode = bool(random.randint(0, 1))
        bytes = StringIO()
        messages.write(bytes, NotificationGaAddMode(timestamp, in_add_mode), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.timestamp, timestamp)
        self.assertEqual(message.in_add_mode, in_add_mode)
        self.assertEqual(message.__class__, NotificationGaAddMode)

    def test_notification_ga_time(self):
        timestamp = utcsecond()
        bytes = StringIO()
        messages.write(bytes, NotificationGaTime(timestamp), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.timestamp, timestamp)
        self.assertEqual(message.__class__, NotificationGaTime)

    def test_notification_ga_connected_set(self):
        # NOTE: IDs are signed numbers --- because they are signed numbers
        # towards the DB...
        meters = [Meter(0, 0xAa), Meter(1, 0xBb), Meter(2, 0x7CDDEEFFCCDDEEFF)]
        bytes = StringIO()
        messages.write(bytes, NotificationGaConnectedSet(meters), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.meters, meters)
        self.assertEqual(message.__class__, NotificationGaConnectedSet)

    def test_notification_gp_state(self):
        meter = Meter(1, 0xAABBCC)
        online = bool(random.randint(0, 1))
        control_manual = bool(random.randint(0, 1))
        relay_on = bool(random.randint(0, 1))
        timestamp = utcsecond()
        bytes = StringIO()
        messages.write(bytes, NotificationGpState(
            meter, online, control_manual, relay_on, timestamp), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.meter, meter)
        self.assertEqual(message.online, online)
        self.assertEqual(message.control_manual, control_manual)
        self.assertEqual(message.relay_on, relay_on)
        self.assertEqual(message.timestamp, timestamp)
        self.assertEqual(message.__class__, NotificationGpState)
