# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib

from Crypto.Cipher import AES

from .conf import settings
from .base import EncryptionContext
from .base import _store


class NoEncryptionCipher(object):
    def encrypt(self, plaintext):
        assert isinstance(plaintext, bytes)
        return b''.join(reversed(plaintext))

    def decrypt(self, ciphertext):
        assert isinstance(ciphertext, bytes)
        return b''.join(reversed(ciphertext))


class NoEncryptionContext(EncryptionContext):
    def __init__(self):
        self.keys = {}

    @classmethod
    def generate_iv(cls):
        return b'\0' * AES.block_size

    def get_cipher(self, key_id, iv):
        return NoEncryptionCipher()


@contextlib.contextmanager
def no_encryption():
    old = getattr(_store, settings.ENCRYPTION_CONTEXT_STORE_KEY, None)
    setattr(
        _store, settings.ENCRYPTION_CONTEXT_STORE_KEY, NoEncryptionContext())
    yield
    setattr(_store, settings.ENCRYPTION_CONTEXT_STORE_KEY, old)


@contextlib.contextmanager
def encryption_context():
    old = getattr(_store, settings.ENCRYPTION_CONTEXT_STORE_KEY, None)
    setattr(_store, settings.ENCRYPTION_CONTEXT_STORE_KEY, EncryptionContext())
    yield
    setattr(_store, settings.ENCRYPTION_CONTEXT_STORE_KEY, old)
