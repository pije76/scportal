# -*- coding: utf-8 -*-
"""
This module wraps the parts of the Python Cryptography Toolkit (pycrypto)
that is used in this encryption app.  The pycrypto package requires some form
of native compilation during installation, which makes it nontrivial to install
correctly on windows machines.  So to support the possible case of an
alternative cryptography toolkit in some deployments this cipher module can be
switched out per deployment via :data:`settings.ENCRYPTION_CIPHER_MODULE`.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA


from .conf import settings


def _random_bytes(count):
    return Random.new().read(count)


def generate_iv():
    """
    Generate a random encryption data initialization vector of size
    :data:`AES.block_size`.
    """
    return _random_bytes(AES.block_size)


def generate_symmetric_key():
    """
    Generate a random symmetric key of size
    :data:`settings.ENCRYPTION_AES_KEYLENGTH`.
    """
    assert settings.ENCRYPTION_AES_KEYLENGTH in AES.key_size
    return _random_bytes(settings.ENCRYPTION_AES_KEYLENGTH)


def hash_symmetric_key(text):
    """
    One-way hash of symmetric key ``text`` (usually a password).  The result is
    intended to be used as ``key`` argument to :func:`.symmetric_cipher`.

    :return: A hash of ``text``.
    """
    key = SHA256.new(text).digest()
    assert len(key) in AES.key_size
    return key


def symmetric_cipher(key, iv):
    """
    Construct symmetric cipher object from given key and encryption data
    initialization vector.

    :param key: The given key, (a password hashed by
        :func:`.hash_symmetric_key`).

    :param iv: The given encryption data initialization vector (random bytes
        generated per symmetric cipher using :func:`.generate_iv`).
    """
    return AES.new(key, AES.MODE_CFB, iv)


def generate_private_public_keypair():
    """
    Generate a private-public key pair.

    :return: A tuple with first element being the private key and the second
        being the public key.  The keys are in a textual representation.
    """
    rsa_key = RSA.generate(settings.ENCRYPTION_RSA_KEYLENGTH)
    private_key = rsa_key.exportKey(format='DER')
    public_key = rsa_key.publickey().exportKey(format='DER')
    return (private_key, public_key)


def load_private_key(text):
    """
    Load a private key object from given private key text representation.

    :param text: The text representation of the private key (from first element
        in result of :func:`.generate_private_public_keypair`)
    """
    key = RSA.importKey(text)
    assert key.has_private()
    return key


def load_public_key(text):
    """
    Load a public key object from given public key text representation.

    :param text: The text representation of the public key (from second element
        in result of :func:`.generate_private_public_keypair`)
    """
    key = RSA.importKey(text)
    assert not key.has_private()
    return key


def private_key_cipher(key):
    """
    Construct a cipher object from a given private key.

    :param key: The given private key (as returned by
        :func:`.load_private_key`).

    :return: A cipher object.
    """
    assert key.has_private()
    return PKCS1_OAEP.new(key)


def public_key_cipher(key):
    """
    Construct a cipher object from a given public key.

    :param key: The given public key (as returned by
        :func:`.load_public_key`).

    :return: A cipher object.
    """
    assert not key.has_private()
    return PKCS1_OAEP.new(key)
