"""Helper module and entry-point with the parse()/write() functions."""

import calendar
import datetime
import re
import logging
from struct import Struct

from pytz import utc

logger = logging.getLogger(__name__)

# 1970-01-01 base to 2000-01-01 base ...
epochoffset = calendar.timegm(datetime.date(2000, 1, 1).timetuple())


def timestamp_to_datetime(timestamp):
    return datetime.datetime.utcfromtimestamp(
        timestamp + epochoffset).replace(tzinfo=utc)


def datetime_to_timestamp(datetime):
    return calendar.timegm(datetime.timetuple()) - epochoffset


class UnknownMessageTypeError(ValueError):
    pass


class Header(object):
    # message-size, type-id, flags
    struct = Struct('!IxxBB')

    def __init__(self, length, MessageType, flags=0):
        self.length = length
        self.datalength = length - self.struct.size
        self.MessageType = MessageType
        self.flags = flags

    @classmethod
    def unpack(cls, read, version):
        length, type_id, flags = read(cls.struct)
        from message_types import message_types
        try:
            message_type = message_types[type_id]
        except IndexError:
            raise UnknownMessageTypeError(
                'Message type %s unknown' % (type_id,))
        return cls(length, message_type, flags)

    def pack(self, version):
        from message_types import message_types
        type_id = message_types.index(self.MessageType)
        return self.struct.pack(self.length, type_id, self.flags)

    def __repr__(self):
        return '<{} {}>'.format(
            self.__class__.__name__,
            ', '.join(['{}={}'.format(k, repr(v))
                       for k, v in self.__dict__.iteritems()])
        )


class Message(object):
    def accept(self, visitor):
        classname = self.__class__.__name__
        underscores_classname = re.sub('([a-z0-9])([A-Z])',
                                       r'\1_\2',
                                       classname).lower()
        methodname = 'visit_{}'.format(underscores_classname)
        # only catch/handle the immediate failure if the method does not exist
        try:
            method = getattr(visitor, methodname)
        except AttributeError:
            return
        method(self)

    # implement in children
    # (method signature here as a reminder...)
    # return child instance
    @classmethod
    def unpack(cls, read, version):
        # "read" is an instance of BufferReader
        raise Exception('Implementation missing')

    # implement in children
    # return data string
    def pack(self, version):
        # should normally use self._pack internallyb
        raise Exception('Implementation missing')

    # Helper for pack() implementations --- data should be a list of strings.
    # This is convenient for use with Struct.pack() --- each call returns a
    # string.  (And building a list rather than a string is more efficient and
    # feels "cleaner" from my point of view.  (I may use list comprehensions
    # "directly".))
    #
    # (Using Struct.pack_into() instead of Struct.pack() is inconvenient, as
    # that requires a preallocated buffer and management of the write offset.
    # Computing the size for preallocating the buffer for nested structures
    # takes about as much code as subsequently actually writing the data to the
    # buffer.)
    def _pack(self, data, version, header_flags=0):
        content_bytes = ''.join(data)
        package_size = Header.struct.size + len(content_bytes)
        header = Header(package_size, self.__class__, header_flags)
        return header.pack(version) + content_bytes

    # for debugging/logging
    def __repr__(self):
        return '<{} {}>'.format(
            self.__class__.__name__,
            ', '.join(['{}={}'.format(k, repr(v))
                       for k, v in self.__dict__.iteritems()])
        )


class BufferReader(object):
    """
    Helper class for deserialising data with struct.Struct: Keep track of
    offset for reading, read sequence of same Struct to list.
    """
    def __init__(self, data):
        self.offset = 0
        self.data = data

    def _read_single(self, struct):
        result = struct.unpack_from(self.data, self.offset)
        self.offset += struct.size
        return result

    def _read_list(self, struct, count):
        result = []
        for n in range(count):
            result.append(self._read_single(struct))
        return result

    def __call__(self, struct, count=None):
        if count is not None:
            return self._read_list(struct, count)
        else:
            return self._read_single(struct)

    def raw(self, count=None):
        if count is not None:
            new_offset = self.offset + count
        else:
            new_offset = len(self.data)
        assert new_offset <= len(self.data)
        result = self.data[self.offset:new_offset]
        self.offset = new_offset
        return result


timestamp_struct = Struct('!I')


# Decrypt stream; we read from that; it reads from actual input and decrypts.
# Makes testing easier; we can provide a directly unencrypted "stream".
def parse(stream, version):
    header_read = BufferReader(stream.read(Header.struct.size))
    header = Header.unpack(header_read, version)
    read = BufferReader(stream.read(header.datalength))
    logger.debug('Received header: %r, payload: %r', header, read.data)
    return header.MessageType.unpack(header, read, version)


# Encrypt stream; we write to that; it encrypts and writes to actual output.
# Makes testing easier; we may use an unencrypted "stream".
def write(stream, message, version):
    bytes = message.pack(version)
    logger.debug('Sending message: %r, bytes: %r', message, bytes)
    stream.write(bytes)
