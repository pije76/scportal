from __future__ import absolute_import

import threading

from django.utils.importlib import import_module

from gridplatform.trackuser import get_user

from .conf import settings


_store = threading.local()


_cipher_modules = {}


def _get_cipher_module(import_path):
    """
    Get cipher module from given path.

    :param import_path:  The given path.
    """
    if import_path not in _cipher_modules:
        _cipher_modules[import_path] = import_module(import_path)
    return _cipher_modules[import_path]


def get_cipher_module():
    """
    Get cipher module from :data:`settings.ENCRYPTION_CIPHER_MODULE`.
    """
    return _get_cipher_module(settings.ENCRYPTION_CIPHER_MODULE)


class MissingEncryptionKeyError(Exception):
    """
    Exception raised when a requested encryption key is not found in the
    current encryption context.

    :see: :meth:`.EncryptionContext.get_cipher`.
    """
    def __init__(self, cls, pk):
        super(MissingEncryptionKeyError, self).__init__(
            'Missing encryption key: ({}, {})'.format(
                cls.__name__, pk))


class _CachedKeys(object):
    """
    A single instance of _CachedKeys is attached to the
    :class:`.EncryptionContext` class --- rather than modify itself, it should
    override itself in specific instance dictionaries.  "attrname" is the name
    it is attached with/the name to override.

    :note: Similar to something which could be implemented with
        ``@cached_property`` --- but that would not enable the current workaround
        for mutual recursion with get_user()...
    """
    def __init__(self, attrname):
        self.attrname = attrname

    def __get__(self, instance, owner):
        # "cache" immediately --- avoid recursion on potentially attempting to
        # decrypt on loading user on get_user() ...
        setattr(instance, self.attrname, {})
        user = get_user()
        if user is not None and not user.is_authenticated():
            # in the process of logging in/loading session data; the empty
            # result should not be "cached"...
            delattr(instance, self.attrname)
            return {}
        private_key = getattr(
            _store, settings.ENCRYPTION_EPHEMERAL_STORE_KEY, None) or \
            getattr(_store, settings.ENCRYPTION_STORE_KEY, None)
        if private_key is not None and user is not None and \
                user.is_authenticated():
            keys = user.decrypt_keys(private_key)
            setattr(instance, self.attrname, keys)
            return keys
        else:
            return {}


class EncryptionContext(object):
    """
    An encryption context holding keys for the user currently logged in.

    :ivar keys: A :class:`._CachedKeys` that per instance replaces itself with
        a dictionary mapping key ids to private keys entities that have
        entrusted these to the currently authenticated entity (the trusted
        entity, the user currently logged in).

        The trusted entity keeps private keys entrusted to it encrypted.  So
        upon initial read from the keys property these entrusted private keys
        are decrypted using private key of trusted entity.  Private key of
        entrusted entity is loaded from thread-local store using either
        :data:`settings.ENCRYPTION_EPHEMERAL_STORE_KEY` or
        :data:`settings.ENCRYPTION_STORE_KEY` as attribute name.
    """
    keys = _CachedKeys('keys')

    @classmethod
    def generate_iv(cls):
        """
        Generate a new encryption data initialization vector.
        """
        cipher_module = get_cipher_module()
        return cipher_module.generate_iv()

    def get_cipher(self, key_id, iv):
        """
        Get the cipher object (something that can encrypt and decrypt data) for
        given encryption key and encryption data initialization vector.

        :param key_id:  The id of the given encryption key.
        """
        try:
            key = self.keys[key_id]
            cipher_module = get_cipher_module()
            return cipher_module.symmetric_cipher(key, iv)
        except KeyError:
            raise MissingEncryptionKeyError(*key_id)
