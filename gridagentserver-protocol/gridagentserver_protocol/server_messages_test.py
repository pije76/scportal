import unittest
import ctypes
import datetime
from StringIO import StringIO
import random

from datatypes import Meter, RuleSet, Rule, Price
import server_messages
import messages

from server_messages import (
    # ConfigGp,
    ConfigGaRulesets,
    ConfigGaTime,
    ConfigGaPrices,
    CommandGaPollMeasurements,
    CommandGaPropagateTime,
    CommandGpSwitchControl,
    CommandGpSwitchRelay,
    ConfigGaSoftware,
    ConfigGpSoftware,
)


def signed_64(val):
    return ctypes.c_longlong(val).value


def signed_32(val):
    return ctypes.c_long(val).value


class TestSerializingVersion1(unittest.TestCase):
    def test_config_gp(self):
        pass

    def test_config_ga_rulesets(self):
        expected = str(bytearray([
            0x00, 0x00, 0x00, 0x38,  # length
            0x00, 0x00,  # padding
            2,  # type
            0x00,  # flags
            0x00, 0x00, 0x00, 0x02,  # count
            # entries
            0x00, 0x00, 0x00, 0x01,  # override timeout
            0x00, 0x00,  # rule count
            0x00, 0x00,  # endpoint count
            0x00, 0x00, 0x00, 0x0F,  # override timeout
            0x00, 0x01,  # rule count
            0x00, 0x02,  # endpoint count
            # rules
            0x00, 0x00, 0x00,  # padding
            0x01,  # action (turn on)
            0x00, 0x00, 0x10, 0x00,  # time begin
            0x00, 0x00, 0x20, 0x00,  # time end
            # endpoints
            0xAB, 0xCD, 0xAB, 0xCD, 0xAB, 0xCD, 0xAB, 0xCD,  # id
            0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34,  # id
        ]))
        actual = server_messages.ConfigGaRulesets([
            RuleSet(1, [], []),
            RuleSet(
                15,
                [Rule(True, 4096, 8192)],
                [
                    Meter(0, signed_64(0xABCDABCDABCDABCD)),
                    Meter(0, signed_64(0x1234123412341234)),
                ]
            ),
        ]).pack(1)
        self.assertEqual(actual, expected)

    def test_config_ga_time(self):
        expected = str(bytearray([
            0x00, 0x00, 0x00, 0x0C,  # length
            0x00, 0x00,  # padding
            3,  # type
            0x00,  # flags
            0x00, 0x00, 0x69, 0x78,  # timestamp
        ]))
        actual = server_messages.ConfigGaTime(
            datetime.datetime(2000, 1, 1, 7, 30)
        ).pack(1)
        self.assertEqual(actual, expected)

    def test_config_ga_prices(self):
        expected = str(bytearray([
            0x00, 0x00, 0x00, 0x24,  # length
            0x00, 0x00,  # padding
            4,  # type
            0x00,  # flags
            0x00, 0x00,  # padding
            0x00, 0x02,  # count
            0x00, 0x00, 0x00, 0x00,  # start time
            0x00, 0x00, 0x01, 0x00,  # end time
            0x12, 0x12, 0x21, 0x21,  # price
            0x00, 0x00, 0x01, 0x00,  # start time
            0x00, 0x00, 0x02, 0x00,  # end time
            0x32, 0x32, 0x23, 0x23,  # price
        ]))
        actual = server_messages.ConfigGaPrices([
            Price(
                datetime.datetime(2000, 1, 1, 0, 0, 0),
                datetime.datetime(2000, 1, 1, 0, 4, 16),
                signed_32(0x12122121)
            ),
            Price(
                datetime.datetime(2000, 1, 1, 0, 4, 16),
                datetime.datetime(2000, 1, 1, 0, 8, 32),
                signed_32(0x32322323)
            ),
        ]).pack(1)
        self.assertEqual(len(actual), len(expected))
        self.assertEqual(actual, expected)

    def test_command_ga_poll_measurements(self):
        expected = str(bytearray([
            0x00, 0x00, 0x00, 0x08,  # length
            0x00, 0x00,  # padding
            7,  # type
            0x00,  # flags
        ]))
        actual = server_messages.CommandGaPollMeasurements().pack(1)
        self.assertEqual(actual, expected)

    def test_command_ga_propagate_time(self):
        expected = str(bytearray([
            0x00, 0x00, 0x00, 0x08,  # length
            0x00, 0x00,  # padding
            8,  # type
            0x00,  # flags
        ]))
        actual = server_messages.CommandGaPropagateTime().pack(1)
        self.assertEqual(actual, expected)

    def test_command_gp_switch_control(self):
        expected = str(bytearray([
            0x00, 0x00, 0x00, 0x10,  # length
            0x00, 0x00,  # padding
            9,  # type
            0x01,  # flags (manual control)
            0x12, 0x34, 0x56, 0x78, 0x12, 0x34, 0x56, 0x78,  # id
        ]))
        actual = server_messages.CommandGpSwitchControl(
            Meter(0, signed_64(0x1234567812345678)),
            True
        ).pack(1)
        self.assertEqual(actual, expected)

    def test_command_gp_switch_relay(self):
        expected = str(bytearray([
            0x00, 0x00, 0x00, 0x10,  # length
            0x00, 0x00,  # padding
            10,  # type
            0x01,  # flags (relay on)
            0x12, 0x34, 0x56, 0x78, 0x12, 0x34, 0x56, 0x78,  # id
        ]))
        actual = server_messages.CommandGpSwitchRelay(
            Meter(0, signed_64(0x1234567812345678)),
            True
        ).pack(1)
        self.assertEqual(actual, expected)


# messages send timestamp as second; i.e. output will *not* match the
# microsecond of input if we use timestamps with microseconds...
def utcsecond():
    return datetime.datetime.utcnow().replace(microsecond=0)


class TestRoundtripVersion2(unittest.TestCase):
    def test_config_gp(self):
        pass

    def test_config_ga_rulesets(self):
        rulesets = [RuleSet(0, [Rule(True, 0, 604800)], [Meter(0, 0xAABBCC)]),
                    RuleSet(15, [Rule(True, 5, 15), Rule(False, 0, 604800)],
                            [Meter(1, 0xABC), Meter(2, 0xDEF)])]
        bytes = StringIO()
        messages.write(bytes, ConfigGaRulesets(rulesets), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.rulesets, rulesets)
        self.assertEqual(message.__class__, ConfigGaRulesets)

    def test_config_ga_time(self):
        timestamp = utcsecond()
        bytes = StringIO()
        messages.write(bytes, ConfigGaTime(timestamp), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.timestamp, timestamp)
        self.assertEqual(message.__class__, ConfigGaTime)

    def test_config_ga_prices(self):
        now = utcsecond()
        prices = [Price(now,
                        now + datetime.timedelta(hours=1),
                        100),
                  Price(now + datetime.timedelta(hours=1),
                        now + datetime.timedelta(hours=2),
                        200)]
        bytes = StringIO()
        messages.write(bytes, ConfigGaPrices(prices), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.prices, prices)
        self.assertEqual(message.__class__, ConfigGaPrices)

    def test_command_ga_poll_meauserements(self):
        bytes = StringIO()
        messages.write(bytes, CommandGaPollMeasurements(), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.__class__, CommandGaPollMeasurements)

    def test_command_ga_propagate_time(self):
        bytes = StringIO()
        messages.write(bytes, CommandGaPropagateTime(), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.__class__, CommandGaPropagateTime)

    def test_command_gp_switch_control(self):
        meter = Meter(1, 0xABCD)
        control_manual = bool(random.randint(0, 1))
        bytes = StringIO()
        messages.write(bytes, CommandGpSwitchControl(meter, control_manual), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.meter, meter)
        self.assertEqual(message.control_manual, control_manual)
        self.assertEqual(message.__class__, CommandGpSwitchControl)

    def test_command_gp_switch_relay(self):
        meter = Meter(1, 0xABCD)
        relay_on = bool(random.randint(0, 1))
        bytes = StringIO()
        messages.write(bytes, CommandGpSwitchRelay(meter, relay_on), 2)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.meter, meter)
        self.assertEqual(message.relay_on, relay_on)
        self.assertEqual(message.__class__, CommandGpSwitchRelay)

    def test_config_ga_software(self):
        sw_version = (0xaa, 0xbb, 0xcc, 'debug')
        hw_model = 1
        target_hw_version = (0x11, 0x22, 0x33, '')
        image = 'abc' * 100
        bytes = StringIO()
        messages.write(bytes, ConfigGaSoftware(
            sw_version, hw_model, target_hw_version, image), 3)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.sw_version, sw_version)
        self.assertEqual(message.target_hw_version, target_hw_version)
        self.assertEqual(message.image, image)

    def test_config_ga_gp_software(self):
        sw_version = (0xaa, 0xbb, 0xcc, 'test')
        hw_model = 3
        target_hw_version = (0x11, 0x22, 0x33, '')
        image = 'abc' * 100
        meters = [Meter(1, 0xABCD)]
        bytes = StringIO()
        messages.write(bytes, ConfigGpSoftware(
            sw_version, hw_model, target_hw_version, image, meters), 3)
        bytes.seek(0)
        message = messages.parse(bytes, 2)
        self.assertEqual(message.sw_version, sw_version)
        self.assertEqual(message.target_hw_version, target_hw_version)
        self.assertEqual(message.hw_model, hw_model)
        self.assertEqual(message.image, image)
        self.assertEqual(message.meters, meters)
