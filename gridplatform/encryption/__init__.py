# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from .conf import settings

from .middleware import _store
from .testutils import NoEncryptionContext


def get_encryption_context():
    if settings.ENCRYPTION_TESTMODE:
        return NoEncryptionContext()
    return getattr(_store, settings.ENCRYPTION_CONTEXT_STORE_KEY, None)


def _set_ephemeral_private_key(key):
    setattr(_store, settings.ENCRYPTION_EPHEMERAL_STORE_KEY, key)
