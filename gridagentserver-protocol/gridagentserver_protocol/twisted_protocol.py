import random
from struct import Struct
import logging

from twisted.internet.protocol import Protocol, ServerFactory, connectionDone
from twisted.internet.defer import DeferredQueue, CancelledError

from . import PROTOCOL_VERSION, SECRET
from encryption import Encrypter
from messages import Header, BufferReader, UnknownMessageTypeError

logger = logging.getLogger(__name__)

# protocol version, ID/nonce
handshake_struct = Struct('!IQ')
uint64 = Struct('!Q')
uint32 = Struct('!I')


class EncryptedProtocol(Protocol):
    """
    A protocol with ARC-4 encryption.

    After handshake, messages start with a 4-byte (network byte order) length
    field, and subclasses may receive/parse only complete messages.

    (The encryption initialisation protocol is far from perfect, but should
    work...)
    """

    def __init__(self):
        self.other_id = None
        self.version = None

    def connectionMade(self):
        logger.debug('Connection from %s', self.transport.getPeer().host)
        self._handshake_done = False
        self._buffer = ''
        self._nonce = random.randint(0, 2 ** 64)
        self.send_handshake()

    def send_handshake(self):
        handshake_data = handshake_struct.pack(PROTOCOL_VERSION, self._nonce)
        logger.debug('Writing handshake %r %s', handshake_data,
                     len(handshake_data))
        self.transport.write(handshake_data)

    def dataReceived(self, data):
        logger.debug('Received data (%s)', len(data))
        if not self._handshake_done:
            self._buffer += data
            self.receive_handshake()
        else:
            self._buffer += self._decrypt(data)
            while self.receive_message():
                pass

    def connectionLost(self, reason=connectionDone):
        logger.debug('Connection lost, reason: %s', reason)
        self.unregister()

    def receive_handshake(self):
        assert not self._handshake_done
        if len(self._buffer) < handshake_struct.size:
            return
        logger.debug('Handshake data received')
        handshake_data = self._buffer[0:handshake_struct.size]
        extra_data = self._buffer[handshake_struct.size:]
        self._buffer = ''
        self.version, self.other_id = handshake_struct.unpack(handshake_data)
        logger.info('Connection from %X, protocol %d',
                     self.other_id, self.version)
        if self.version > PROTOCOL_VERSION or self.version <= 0:
            logger.info('Protocol %d not supported; disconnecting %X',
                        self.version, self.other_id)
            self.transport.loseConnection()
            return
        self.init_encryption()
        self._handshake_done = True
        self.register()
        if extra_data != '':
            self.dataReceived(extra_data)

    def init_encryption(self):
        # initialise encryption state with nonce + secret + incoming data
        key_bytes = bytearray(SECRET)
        id_bytes = bytearray(uint64.pack(self.other_id))
        nonce_bytes = bytearray(uint64.pack(self._nonce))
        for i in range(len(nonce_bytes)):
            key_bytes[i] = key_bytes[i] ^ id_bytes[i] ^ nonce_bytes[i]
        self._encrypt = Encrypter(key_bytes)
        self._decrypt = Encrypter(key_bytes)

    def receive_message(self):
        if len(self._buffer) < uint32.size:
            return False
        length, = uint32.unpack_from(self._buffer)
        if len(self._buffer) < length:
            return False
        message = self._buffer[:length]
        self._buffer = self._buffer[length:]
        self.message_received(message)
        return True

    def write_encrypted(self, bytes):
        self.transport.write(self._encrypt(bytes))

    # Override this.
    def message_received(self, data):
        pass

    # Override this.  Called after processing handshake.
    def register(self):
        pass

    # Override this.  Called from connectionLost.
    def unregister(self):
        pass


# gets a "factory" member set to the factory used to obtain it
# connection from: self.transport.getPeer().host (ip addr as string)
class BaseAgentProtocol(EncryptedProtocol):
    def __init__(self):
        EncryptedProtocol.__init__(self)
        self.agent_mac = None
        # We serialise incoming/outgoing messages in these queues...
        # (Serialise as in "order sequentially"...)
        self.outgoing = DeferredQueue(backlog=1)
        self.incoming = DeferredQueue(backlog=1)

    # Called after handshake, when encryption is initialised and we have an
    # identifier (MAC address) for the other end.  (Overridden + called from
    # implementation in GridAgent Server.)
    def register(self):
        """
        Registers self in the factory handlers dictionary; disconnecting any
        currently present handler for the same agent MAC.  Return True if old
        handler removed, False if no old handler existed.
        """
        logger.debug('Adding %X to handler map', self.other_id)
        self.agent_mac = self.other_id
        return self.factory.register(self)

    # Called on disconnect.  Return true if agent has already reconnected,
    # i.e. new connection for same id exist.  (Overridden + called from
    # implementation in GridAgent Server.)
    def unregister(self):
        """
        Stops sending messages from the outgoing queue and removes self from
        the factory handlers dictionary; return True if already replaced, False
        otherwise.
        """
        if self.other_id:
            logger.debug('Removing %X from handler map', self.other_id)
        for deferred in self.outgoing.waiting:
            deferred.cancel()
        return self.factory.unregister(self)

    # Called when a complete message is arrived (the base class decrypts and
    # reads the length field at the start of each message).
    def message_received(self, data):
        """
        Parses a complete, decrypted message and puts it on the incoming queue.
        Resumes the sending of messages from the outgoing queue if indicated by
        resume_sending_after().
        """
        header_read = BufferReader(data[:Header.struct.size])
        try:
            header = Header.unpack(header_read, self.version)
            read = BufferReader(data[Header.struct.size:])
            message = header.MessageType.unpack(header, read, self.version)
            logger.debug('Received message of type %s', message.__class__.__name__)
            self.incoming.put(message)
            if self.transport.connected and self.resume_sending_after(message):
                # process next message when available...
                # no-op error handler to allow cancel
                self.outgoing.get().addCallbacks(self.send_message, lambda ex: None)
        except UnknownMessageTypeError as e:
            logger.info(e.message)

    def send_message(self, message):
        """
        Serialises and sends a message; pauses the sending of messages
        afterwards if indicated by pause_sending_after(); otherwise, sets up
        handling/sending of the next message from the outgoing queue.
        """
        logger.debug('Sending message of type %s', message.__class__.__name__)
        bytes = message.pack(self.version)
        self.write_encrypted(bytes)
        if self.transport.connected and not self.pause_sending_after(message):
            # process next message when available...
            # no-op error handler to allow cancel
            self.outgoing.get().addCallbacks(self.send_message, lambda ex: None)

    # Some messages --- software updates in particular --- demand the complete
    # attention of the GridAgent.  After sending such a message, writing
    # mesages is paused/delayed until we receive an acknowledgement.
    # Override in subclass.
    def pause_sending_after(self, message):
        """
        Specifies whether sending messages should be paused after sending a
        specific message --- by default always False; override in subclass.
        """
        return False

    # See pause_sending_after
    # Override in subclass.
    def resume_sending_after(self, message):
        """
        Specifies whether sending messages should be resumed after receiving
        (not processing) a specific message --- by default always False;
        override in subclass.
        """
        return False


class BaseAgentProtocolFactory(ServerFactory):
    protocol = BaseAgentProtocol

    def __init__(self):
        self.handlers = {}

    def register(self, handler):
        """
        Return True if this replaces an existing connection; i.e. this is a
        reconnect before/without a disconnect; False if this is a "new"
        connection.
        """
        previous = self.handlers.pop(handler.agent_mac, None)
        self.handlers[handler.agent_mac] = handler
        if previous is not None:
            assert previous is not handler
            previous.transport.loseConnection()
        # handling/sending outgoing messages now safe; start processing
        if handler.transport.connected:
            # no-op error handler to allow cancel
            # (reading from the queue shouldn't "fail" otherwise, so this
            # shouldn't mask real errors...)
            handler.outgoing.get().addCallbacks(handler.send_message,
                                                lambda ex: None)
        return (previous is not None)

    def unregister(self, handler):
        """
        Return True if another handler is registered for this connection,
        i.e. a reconnect has occurred before this disconnect; False if this is
        a "normal" disconnect.
        """
        current = self.handlers.get(handler.agent_mac, None)
        if current is handler:
            del self.handlers[handler.agent_mac]
        return (current is not handler) and (current is not None)
