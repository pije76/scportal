from struct import Struct
import copy
import datetime
import random

from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.internet.protocol import ServerFactory

from . import PROTOCOL_VERSION, SECRET
from client_messages import NotificationGpState
from datatypes import Meter
from encryption import Encrypter
from twisted_protocol import (
    EncryptedProtocol,
    BaseAgentProtocol,
    BaseAgentProtocolFactory,
)

# version, id/nonce
handshake_struct = Struct('!IQ')
uint64 = Struct('!Q')


def make_key(client_id, nonce):
    return bytearray(map(lambda a, b, c: (a or 0) ^ (b or 0) ^ (c or 0),
                         bytearray(SECRET),
                         bytearray(uint64.pack(client_id)),
                         bytearray(uint64.pack(nonce))))


class EncryptionProtocolFactory(ServerFactory):
    protocol = EncryptedProtocol


class EncryptionProtocolTestCase(unittest.TestCase):
    def setUp(self):
        factory = EncryptionProtocolFactory()
        self.proto = factory.buildProtocol(('127.0.0.1', 0))
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)

    def test_handshake(self):
        handshake = handshake_struct.pack(2, 0x3c970e1e8e4e)
        self.proto.dataReceived(handshake)
        version, nonce = handshake_struct.unpack(self.tr.value())
        self.assertEqual(version, PROTOCOL_VERSION)

    def test_init_encryption(self):
        client_id = 0x3c970e1e8e4e
        client_version = 2
        handshake = handshake_struct.pack(client_version, client_id)
        self.proto.dataReceived(handshake)
        server_version, nonce = handshake_struct.unpack(self.tr.value())
        key = make_key(client_id, nonce)
        encrypter = Encrypter(key)
        self.assertEqual(encrypter, self.proto._encrypt)
        self.assertEqual(encrypter, self.proto._decrypt)


class BaseAgentProtocolTestCase(unittest.TestCase):
    def setUp(self):
        self.factory = BaseAgentProtocolFactory()
        self.proto = self.factory.buildProtocol(('127.0.0.1', 0))
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)
        self.agent_mac = random.randint(0, 0xffffffffffff)  # 6 bytes...
        client_version = 2
        handshake = handshake_struct.pack(client_version, self.agent_mac)
        self.proto.dataReceived(handshake)
        server_version, nonce = handshake_struct.unpack(self.tr.value())
        key = make_key(self.agent_mac, nonce)
        self.encrypter = Encrypter(key)
        self.decrypter = copy.deepcopy(self.encrypter)

    def test_register(self):
        self.assertEqual(self.factory.handlers.keys(), [self.agent_mac])

    def test_unregister(self):
        self.assertEqual(self.factory.handlers.keys(), [self.agent_mac])
        self.proto.connectionLost()
        self.assertEqual(self.factory.handlers.keys(), [])

    def test_message(self):
        meter = Meter(2, 24)
        timestamp = datetime.datetime.now().replace(microsecond=0)
        notification = NotificationGpState(meter, True, False, True, timestamp)
        data = self.encrypter(notification.pack(2))
        splitpoint = random.randint(0, len(data))
        self.proto.dataReceived(data[:splitpoint])
        self.proto.dataReceived(data[splitpoint:])
        self.assertEqual(self.proto.incoming.pending, [notification])
