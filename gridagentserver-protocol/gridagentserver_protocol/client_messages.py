"""Messages to be sent from the (virtual) agent to the GridAgent server."""

from struct import Struct
import logging

from messages import Message, timestamp_to_datetime, datetime_to_timestamp
from datatypes import Meter, MeterData, MeasurementSet, Measurement, Version


logger = logging.getLogger(__name__)

int32 = Struct('!i')
uint32 = Struct('!I')
int16 = Struct('!h')
uint16 = Struct('!H')
uint8 = Struct('!B')


# ZigBee timestamp, i.e. seconds since 2000-01-01
timestamp_struct = Struct('!I')

# major, minor, revision, extra string
version_struct = Struct('!BBB12s')


def normalise_version(version):
    """
    Replace the received fixed-length "extra" string with its prefix before the
    first \0 character.
    """
    major, minor, revision, extra_bytes = version
    extra_bytes = extra_bytes.split('\0', 1)[0]
    extra = extra_bytes.decode('iso8859-1')
    return (major, minor, revision, extra)


class BulkMeasurements(Message):
    # ID, timestamp, value
    measurement1_struct = Struct('!qIq')
    # type, unit, input_number, value
    measurement2_struct = Struct('!bbbq')
    # connection_type, ID
    meter2_struct = Struct('!bq')

    def __init__(self, meter_data):
        self.meter_data = meter_data

    def __cmp__(self, other):
        return cmp(self.meter_data, other.meter_data)

    def __hash__(self):
        return hash(self.meter_data)

    @classmethod
    def unpack(cls, header, read, version):
        if version == 1:
            return cls.unpack_1(read)
        else:
            return cls.unpack_2(read)

    # meter id, connection_type --- ver1 only id...
    @classmethod
    def unpack_1(cls, read):
        def group_ids(acc, elem):
            id, timestamp, value = elem
            if not acc:
                acc = [(id, [(timestamp, value)])]
            else:
                old_id = acc[-1][0]
                if id == old_id:
                    acc[-1][1].append((timestamp, value))
                else:
                    acc.append((id, [(timestamp, value)]))
            return acc
        count, = read(uint32)
        # [(id, timestamp, value), ...]
        raw_list = read(cls.measurement1_struct, count)
        raw_list.sort()
        # to [(id, [(timestamp, value), ...]), ...]
        data = reduce(group_ids, raw_list, [])
        meter_data = []
        for meter_id, measurements in data:
            meter = Meter(0, meter_id)
            measurement_sets = [
                MeasurementSet(timestamp_to_datetime(timestamp),
                               [Measurement(0, 0, 0, value)])
                for timestamp, value in measurements]
            meter_data.append(MeterData(meter, measurement_sets))
        return cls(meter_data)

    @classmethod
    def unpack_2(cls, read):
        meter_data_count, = read(uint16)
        meter_data = []
        for n in range(meter_data_count):
            meter = Meter(*read(cls.meter2_struct))
            measurement_set_count, = read(uint16)
            measurement_sets = []
            for m in range(measurement_set_count):
                timestamp, = read(timestamp_struct)
                measurement_count, = read(uint16)
                measurements = []
                for l in range(measurement_count):
                    measurements.append(
                        Measurement(*read(cls.measurement2_struct)))
                measurement_sets.append(
                    MeasurementSet(timestamp_to_datetime(timestamp),
                                   measurements))
            meter_data.append(MeterData(meter, measurement_sets))
        return cls(meter_data)

    def pack(self, version):
        if version < 2:
            raise Exception("Not implemented for version {}".format(version))
        data = []
        data.append(uint16.pack(len(self.meter_data)))
        for meter, measurement_sets in self.meter_data:
            data.append(self.meter2_struct.pack(*meter))
            data.append(uint16.pack(len(measurement_sets)))
            for timestamp, measurements in measurement_sets:
                data.append(timestamp_struct.pack(
                    datetime_to_timestamp(timestamp)))
                data.append(uint16.pack(len(measurements)))
                data.extend([self.measurement2_struct.pack(*measurement)
                             for measurement in measurements])
        return self._pack(data, version)


class NotificationGaAddMode(Message):
    def __init__(self, timestamp, in_add_mode):
        self.timestamp = timestamp
        self.in_add_mode = in_add_mode

    def __cmp__(self, other):
        return cmp((self.timestamp, self.in_add_mode),
                   (other.timestamp, other.in_add_mode))

    def __hash__(self):
        return hash((self.timestamp, self.in_add_mode))

    @classmethod
    def unpack(cls, header, read, version):
        timestamp = timestamp_to_datetime(*read(timestamp_struct))
        in_add_mode = bool(header.flags & 1)
        return cls(timestamp, in_add_mode)

    def pack(self, version):
        data = timestamp_struct.pack(datetime_to_timestamp(self.timestamp))
        return self._pack([data], version, int(self.in_add_mode))


class NotificationGaTime(Message):
    def __init__(self, timestamp):
        self.timestamp = timestamp

    def __cmp__(self, other):
        return cmp(self.timestamp, other.timestamp)

    def __hash__(self):
        return hash(self.timestamp)

    @classmethod
    def unpack(cls, header, read, version):
        timestamp = timestamp_to_datetime(*read(timestamp_struct))
        return cls(timestamp)

    def pack(self, version):
        data = timestamp_struct.pack(datetime_to_timestamp(self.timestamp))
        return self._pack([data], version)


class NotificationGaConnectedSet(Message):
    # ID
    meter1_struct = Struct('!q')
    # connection_type, ID
    meter2_struct = Struct('!bq')
    # connection_type, ID, device type, device option,
    # hw major, hw minor, hw revision, hw revisionstring
    # sw major, sw minor, sw revision, sw revisionstring
    meter4_struct = Struct('!BqBB' + 'BBB12s' + 'BBB12s')

    def __init__(self, meters, device_opts=None, versions=None):
        self.meters = meters
        self.device_opts = device_opts
        self.versions = versions

    def __cmp__(self, other):
        return cmp(self.meters, other.meters)

    def __hash__(self):
        return hash(self.meters)

    @classmethod
    def unpack(cls, header, read, version):
        count, = read(uint32)
        if version == 1:
            meters = [Meter(0, id) for id, in read(cls.meter1_struct, count)]
            return cls(meters)
        elif version < 4:
            meters = [Meter(*data) for data in read(cls.meter2_struct, count)]
            return cls(meters)
        else:
            data = read(cls.meter4_struct, count)
            meters = [Meter(elem[0], elem[1]) for elem in data]
            device_opts = [(elem[2], elem[3]) for elem in data]
            versions = [(Version(*elem[4:8]), Version(*elem[8:12]))
                        for elem in data]
            return cls(meters, device_opts, versions)

    def pack(self, version):
        if version < 2:
            raise Exception("Not implemented for version {}".format(version))
        data = [uint32.pack(len(self.meters))]
        data.extend([self.meter2_struct.pack(*meter) for meter in self.meters])
        return self._pack(data, version)


class NotificationGpState(Message):
    # ID
    meter1_struct = Struct('!q')
    # connection_type, ID
    meter2_struct = Struct('!bq')

    def __init__(self, meter, online, control_manual, relay_on, timestamp):
        self.meter = meter
        self.online = online
        self.control_manual = control_manual
        self.relay_on = relay_on
        self.timestamp = timestamp

    def __cmp__(self, other):
        return cmp((self.meter, self.timestamp,
                    self.online, self.control_manual, self.relay_on),
                   (other.meter, other.timestamp,
                    other.online, other.control_manual, other.relay_on))

    def __hash__(self):
        return hash((self.meter, self.timestamp,
                     self.online, self.control_manual, self.relay_on))

    @classmethod
    def unpack(cls, header, read, version):
        online = bool(header.flags & 1)
        control_manual = bool(header.flags & 2)
        relay_on = bool(header.flags & 4)
        timestamp = timestamp_to_datetime(*read(timestamp_struct))
        if version == 1:
            id, = read(cls.meter1_struct)
            meter = Meter(0, id)
        else:
            meter = Meter(*read(cls.meter2_struct))
        return cls(meter, online, control_manual, relay_on, timestamp)

    def pack(self, version):
        if version < 2:
            raise Exception("Not implemented for version {}".format(version))
        flags = self.online * 1 + self.control_manual * 2 + self.relay_on * 4
        data = [timestamp_struct.pack(datetime_to_timestamp(self.timestamp)),
                self.meter2_struct.pack(*self.meter)]
        return self._pack(data, version, flags)


class AcknowledgementGpSoftware(Message):
    # no members...
    @classmethod
    def unpack(cls, header, read, version):
        return cls()

    def pack(self, version):
        return self._pack([], version)


class AcknowledgementGaSoftware(Message):
    # no members...
    @classmethod
    def unpack(cls, header, read, version):
        return cls()

    def pack(self, version):
        return self._pack([], version)


class ErrorGpSoftware(Message):
    # no members...
    @classmethod
    def unpack(cls, header, read, version):
        return cls()

    def pack(self, version):
        return self._pack([], version)


class ErrorGaSoftware(Message):
    # no members...
    @classmethod
    def unpack(cls, header, read, version):
        return cls()

    def pack(self, version):
        return self._pack([], version)


class InfoAgentVersions(Message):
    def __init__(self, sw_version, device_type, hw_revision, serial):
        self.sw_version = sw_version
        self.device_type = device_type
        self.hw_revision = hw_revision
        self.serial = serial

    @classmethod
    def unpack(cls, header, read, version):
        assert version >= 3
        sw_version = normalise_version(read(version_struct))
        device_type, = read(uint8)
        hw_revision = normalise_version(read(version_struct))
        serial, = read(int32)
        return cls(sw_version, device_type, hw_revision, serial)

    def pack(self, version):
        assert version >= 3
        data = [version_struct.pack(*self.sw_version),
                uint8.pack(self.device_type),
                version_struct.pack(*self.hw_revision),
                uint32.pack(self.serial)]
        return self._pack(data, version)


class InfoEventLog(Message):
    eventtext_struct = Struct('!128s')

    def __init__(self, timestamp, code, text):
        self.timestamp = timestamp
        self.code = code
        self.text = text

    @classmethod
    def unpack(cls, header, read, version):
        timestamp_raw, = read(timestamp_struct)
        timestamp = timestamp_to_datetime(timestamp_raw)
        code, = read(int16)
        text_raw, = read(cls.eventtext_struct)
        text = text_raw.split('\0', 1)[0]
        return cls(timestamp, code, text)

    def pack(self, version):
        assert version >= 5
        data = [timestamp_struct.pack(datetime_to_timestamp(self.timestamp)),
                int16.pack(self.code),
                self.eventtext_struct.pack(self.text)]
        return self._pack(data, version)
