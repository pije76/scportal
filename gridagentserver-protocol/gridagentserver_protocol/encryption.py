"""ARCFOUR encryption, implemented as partial file object interface."""

import logging

logger = logging.getLogger(__name__)


# deprecated; replaced
# Encrypter/StreamEncrypter splits responsibility for encryption state away
# from wrapping stream...  (Mostly to be able to use encryption without
# streams...)
class Encryption(object):
    """
    Simple ARCFOUR encryption implementation.  Wrapping an object with read()
    and write() operations to do encryption on read() and write().
    """
    def __init__(self, key, stream):
        """Initialize encryption/cipher state with the specified key.
        Key may be string or bytearray.
        (Or an iterable yielding integers [0,255]...)"""
        key = bytearray(key)
        state = bytearray(range(256))
        j = 0
        for i in range(256):
            j = (j + state[i] + key[i % len(key)]) % 256
            state[i], state[j] = state[j], state[i]
        self._i = 0
        self._j = 0
        self._state = state
        self.stream = stream

    def _crypt(self, data):
        """
        Encrypt/decrypt data and update the state of the stream cipher.
        Input/output data is represented as strings, for convenient use with
        the Python socket interface.  Returns the transformed data.
        """
        i = self._i
        j = self._j
        state = self._state
        result = bytearray(len(data))
        for n in range(len(data)):
            i = (i + 1) % 256
            j = (j + state[i]) % 256
            state[i], state[j] = state[j], state[i]
            k = state[(state[i] + state[j]) % 256]
            result[n] = (ord(data[n]) ^ k) % 256
        self._i = i
        self._j = j
        return str(result)

    def read(self, count):
        """
        Read and decrypt data from configured file/stream.
        """
        # rfile.read does not throw exception if connection closed...
        data = self._crypt(self.stream.read(count))
        # we check the length; we only get less than requested on "EOF";
        # i.e. if the connection was closed
        if len(data) != count:
            raise EOFError
        return data

    def write(self, data):
        """
        Encrypt and write data to configured file/stream.
        """
        # wfile.write throws exception if connection closed
        self.stream.write(self._crypt(data))
        self.stream.flush()

    def flush(self):
        self.stream.flush()


class Encrypter(object):
    def __init__(self, key):
        key = bytearray(key)
        state = bytearray(range(256))
        j = 0
        for i in range(256):
            j = (j + state[i] + key[i % len(key)]) % 256
            state[i], state[j] = state[j], state[i]
        self._i = 0
        self._j = 0
        self._state = state

    def __call__(self, data):
        """
        Encrypt/decrypt data and update the state of the stream cipher.
        Input/output data is represented as strings, for interoperability with
        Python APIs representing byte arrays as strings.  Returns the
        transformed data.
        """
        i = self._i
        j = self._j
        state = self._state
        result = bytearray(len(data))
        for n in range(len(data)):
            i = (i + 1) % 256
            j = (j + state[i]) % 256
            state[i], state[j] = state[j], state[i]
            k = state[(state[i] + state[j]) % 256]
            result[n] = (ord(data[n]) ^ k) % 256
        self._i = i
        self._j = j
        return str(result)

    def __cmp__(self, other):
        # note that object changes wrt. comparison on use...
        # (that's kind of the point of the object...)
        return cmp((self._i, self._j, self._state),
                   (other._i, other._j, other._state))

    def __hash__(self):
        # not a very good hash function, but agrees with __cmp__, correctness
        # before performance...
        return hash((self._i, self._j))


class StreamEncrypter(object):
    def __init__(self, key, stream):
        self._crypt = Encrypter(key)
        self.stream = stream

    def read(self, count):
        """
        Read and decrypt data from configured file/stream.
        """
        # rfile.read does not throw exception if connection closed...
        data = self._crypt(self.stream.read(count))
        # we check the length; we only get less than requested on "EOF";
        # i.e. if the connection was closed
        if len(data) != count:
            raise EOFError
        return data

    def write(self, data):
        """
        Encrypt and write data to configured file/stream.
        """
        # wfile.write throws exception if connection closed
        self.stream.write(self._crypt(data))
        self.stream.flush()

    def flush(self):
        self.stream.flush()
