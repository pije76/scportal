"""Messages to be sent from the GridAgent server to the (virtual) agent."""

import logging
from struct import Struct

from messages import Message, timestamp_to_datetime, datetime_to_timestamp
from datatypes import Meter, Rule, RuleSet, Price

logger = logging.getLogger(__name__)

uint32 = Struct('!I')
uint16 = Struct('!H')
uint8 = Struct('B')

# ZigBee timestamp, i.e. seconds since 2000-01-01
timestamp_struct = Struct('!I')

# major, minor, revision, extra string
version_struct = Struct('!BBB12s')


def normalise_version(version):
    """
    Replace the received fixed-length "extra" string with its prefix before the
    first \0 character.
    """
    major, minor, revision, extra = version
    extra = extra.split('\0', 1)[0]
    return (major, minor, revision, extra)


# connection_type, ID
meter_struct = Struct('!bq')


# DEPRECATED/useless:
# We always want 1 minute interval; ignoring intervals configured in DB...
class ConfigGp(Message):
    # ID, interval
    config1_struct = Struct('!qi')

    def __init__(self, measurement_intervals):
        self.measurement_intervals = measurement_intervals

    @classmethod
    def unpack(cls, header, read, version):
        pass

    def pack(self, version):
        if version == 1:
            data = [uint32.pack(len(self.measurement_intervals))]
            data.extend([self.config1_struct.pack(meter.id, interval)
                         for meter, interval
                         in self.measurement_intervals.iteritems()])
        else:
            # deprecated...
            data = []
        return self._pack(data, version)


class ConfigGaRulesets(Message):
    # override timeout, rule-count, meter-count
    ruleset_head_struct = Struct('!ihh')
    # relay-on?, start-time, end-time
    rule_struct = Struct('!xxx?II')
    # ID
    meter1_struct = Struct('!q')
    # connection type, ID
    meter2_struct = Struct('!bq')

    def __init__(self, rulesets):
        self.rulesets = rulesets

    @classmethod
    def unpack(cls, header, read, version):
        ruleset_count, = read(uint32)
        rulesets = []
        for n in range(ruleset_count):
            override_timeout, rule_count, meter_count = \
                read(cls.ruleset_head_struct)
            rules = [Rule(*entry)
                     for entry in read(cls.rule_struct, rule_count)]
            if version == 1:
                meters = [Meter(0, id)
                          for id, in read(cls.meter1_struct, meter_count)]
            else:
                meters = [Meter(*entry)
                          for entry in read(cls.meter2_struct, meter_count)]
            rulesets.append(RuleSet(override_timeout, rules, meters))
        return cls(rulesets)

    def pack(self, version):
        data = [uint32.pack(len(self.rulesets))]
        for override_timeout, rules, meters in self.rulesets:
            data.append(self.ruleset_head_struct.pack(override_timeout,
                                                      len(rules), len(meters)))
            data.extend([self.rule_struct.pack(*rule) for rule in rules])
            if version == 1:
                data.extend([self.meter1_struct.pack(meter.id)
                             for meter in meters])
            else:
                data.extend([self.meter2_struct.pack(*meter)
                             for meter in meters])
        return self._pack(data, version)


class ConfigGaTime(Message):
    def __init__(self, timestamp):
        self.timestamp = timestamp

    @classmethod
    def unpack(cls, header, read, version):
        timestamp = timestamp_to_datetime(*read(timestamp_struct))
        return cls(timestamp)

    def pack(self, version):
        data = timestamp_struct.pack(datetime_to_timestamp(self.timestamp))
        return self._pack([data], version)


class ConfigGaPrices(Message):
    # count
    price_head_struct = Struct('!xxH')
    # start timestamp, end timestamp, price per GWh
    # (price in some unspecified unit...)
    price_struct = Struct('!III')

    def __init__(self, prices):
        self.prices = prices

    @classmethod
    def unpack(cls, header, read, version):
        price_count, = read(cls.price_head_struct)
        prices = [Price(timestamp_to_datetime(start),
                        timestamp_to_datetime(end), price)
                  for start, end, price in read(cls.price_struct, price_count)]
        return cls(prices)

    def pack(self, version):
        data = [self.price_head_struct.pack(len(self.prices))]
        data.extend([self.price_struct.pack(datetime_to_timestamp(start),
                                            datetime_to_timestamp(end), price)
                     for start, end, price in self.prices])
        return self._pack(data, version)


class ConfigGpSoftware(Message):
    def __init__(self, sw_version, hw_model, target_hw_version, image, meters):
        # version: major, minor, revision
        self.sw_version = sw_version
        self.hw_model = hw_model
        self.target_hw_version = target_hw_version
        self.image = image
        self.meters = meters

    @classmethod
    def unpack(cls, header, read, version):
        image_offset, = read(uint32)
        sw_version = normalise_version(read(version_struct))
        hw_model, = read(uint8)
        target_hw_version = normalise_version(read(version_struct))
        meter_count, = read(uint32)
        meters = [Meter(*entry)
                  for entry in read(meter_struct, meter_count)]
        image = read.raw()
        return cls(sw_version, hw_model, target_hw_version, image, meters)

    def pack(self, version):
        assert version >= 3
        # differ from agent software message with inclusion of model, meter ids
        image_offset = (uint32.size + 2 * version_struct.size + uint8.size +
                        uint32.size + len(self.meters) * meter_struct.size)
        data = [uint32.pack(image_offset),
                version_struct.pack(*self.sw_version),
                uint8.pack(self.hw_model),
                version_struct.pack(*self.target_hw_version)]
        # meter_ids
        data.append(uint32.pack(len(self.meters)))
        data.extend([meter_struct.pack(*meter) for meter in self.meters])
        # image
        data.append(self.image)
        return self._pack(data, version)


class ConfigGaSoftware(Message):
    def __init__(self, sw_version, hw_model, target_hw_version, image):
        # version: major, minor, revision
        self.sw_version = sw_version
        self.hw_model = hw_model
        self.target_hw_version = target_hw_version
        self.image = image

    @classmethod
    def unpack(cls, header, read, version):
        image_offset, = read(uint32)
        sw_version = normalise_version(read(version_struct))
        hw_model, = read(uint8)
        hw_version = normalise_version(read(version_struct))
        image = read.raw()
        return cls(sw_version, hw_model, hw_version, image)

    def pack(self, version):
        assert version >= 3
        image_offset = uint32.size + 2 * version_struct.size + uint8.size
        data = [uint32.pack(image_offset),
                version_struct.pack(*self.sw_version),
                uint8.pack(self.hw_model),
                version_struct.pack(*self.target_hw_version),
                self.image]
        return self._pack(data, version)


class CommandGaPollMeasurements(Message):
    # no members...
    @classmethod
    def unpack(cls, header, read, version):
        return cls()

    def pack(self, version):
        return self._pack([], version)


class CommandGaPropagateTime(Message):
    # no members...
    @classmethod
    def unpack(cls, header, read, version):
        return cls()

    def pack(self, version):
        return self._pack([], version)


class CommandGpSwitchControl(Message):
    # ID
    meter1_struct = Struct('!q')
    # ID, connection type
    meter2_struct = Struct('!bq')

    def __init__(self, meter, control_manual):
        self.meter = meter
        self.control_manual = control_manual

    @classmethod
    def unpack(cls, header, read, version):
        control_manual = bool(header.flags)
        if version == 1:
            id, = read(cls.meter1_struct)
            meter = Meter(0, id)
        else:
            meter = Meter(*read(cls.meter2_struct))
        return cls(meter, control_manual)

    def pack(self, version):
        if version == 1:
            data = self.meter1_struct.pack(self.meter.id)
        else:
            data = self.meter2_struct.pack(*self.meter)
        flags = int(self.control_manual)
        return self._pack([data], version, flags)


class CommandGpSwitchRelay(Message):
    # ID
    meter1_struct = Struct('!q')
    # ID, connection type
    meter2_struct = Struct('!bq')

    def __init__(self, meter, relay_on):
        self.meter = meter
        self.relay_on = relay_on

    @classmethod
    def unpack(cls, header, read, version):
        relay_on = bool(header.flags)
        if version == 1:
            id, = read(cls.meter1_struct)
            meter = Meter(0, id)
        else:
            meter = Meter(*read(cls.meter2_struct))
        return cls(meter, relay_on)

    def pack(self, version):
        if version == 1:
            data = self.meter1_struct.pack(self.meter.id)
        else:
            data = self.meter2_struct.pack(*self.meter)
        flags = int(self.relay_on)
        return self._pack([data], version, flags)
