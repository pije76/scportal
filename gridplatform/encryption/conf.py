# -*- coding: utf-8 -*-
"""
.. data:: settings.ENCRYPTION_RSA_KEYLENGTH = 1024

    Key length for generated RSA keys; bits, multiple of 256, at least 1024.

.. data:: settings.ENCRYPTION_AES_KEYLENGTH = 16

    Key length for generated AES keys; bytes, 16, 24 or 32.

.. data:: settings.ENCRYPTION_COOKIE_NAME = 'gmkey'

    Cookie to store the session data decryption key in.

.. data:: settings.ENCRYPTION_SESSION_KEY = 'encryption_private_key'

    Key for session dictionary entry holding the encrypted private key (and the
    applied encryption data initialization vector) for the user with that
    session.  This encrypted private key is encrypted symmetrically using a key
    encoded into a cookie, named by :data:`settings.ENCRYPTION_COOKIE_NAME`.

.. data:: settings.ENCRYPTION_SIGN_SALT = 'gridmanager.encryption.middleware.'

    Salt used for converting cookie key value to symmetric key and back.  See
    also :class:`.EncryptionMiddleware`.

.. data:: settings.ENCRYPTION_STORE_KEY = 'private_key'

    Name of thread-local store attribute used to hold private key during
    processing of request (for normal session-based authentication).  See also
    :class:`.EncryptionContext`.

.. data:: settings.ENCRYPTION_EPHEMERAL_STORE_KEY = 'ephemeral_private_key'

    Name of thread-local store attribute used to hold private key during
    processing of request (when authenticating per request via token auth).
    See also :meth:`.EncryptionTokenAuthentication.authenticate_credentials`
    and :class:`.EncryptionContext`

.. data:: settings.ENCRYPTION_ORIGINAL_STORE_KEY = '_original_private_key'

    Name of thread-local store attribute used to detect if the thread-local
    store attribute named by :data:`settings.ENCRYPTION_STORE_KEY` has changed.
    See also :class:`.EncryptionMiddleware`.

.. data:: settings.ENCRYPTION_CONTEXT_STORE_KEY = 'encryption_context'

    The thread-local store attribute used to hold the
    :class:`.EncryptionContext` of this request.

.. data:: settings.ENCRYPTION_TESTMODE = False

    Set to ``True`` to disable encryption.  This is useful for unit testing
    were the subject under test is some kind of :class:`.EncryptedModel` but
    the purpose of the test is not to test encryption mechanisms.

.. data:: settings.ENCRYPTION_CIPHER_MODULE = 'gridplatform.encryption.cipher'

    Path to cipher module.  See also :mod:`gridplatform.encrytion.cipher`.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings

from appconf import AppConf


__all__ = ['settings', 'EncryptionConf']


class EncryptionConf(AppConf):
    RSA_KEYLENGTH = 1024
    AES_KEYLENGTH = 16
    # cookie to store the session data decryption key in
    COOKIE_NAME = 'gmkey'
    SESSION_KEY = 'encryption_private_key'
    SIGN_SALT = 'gridmanager.encryption.middleware.'

    STORE_KEY = 'private_key'
    EPHEMERAL_STORE_KEY = 'ephemeral_private_key'
    ORIGINAL_STORE_KEY = '_original_private_key'
    CONTEXT_STORE_KEY = 'encryption_context'

    TESTMODE = False
    CIPHER_MODULE = 'gridplatform.encryption.cipher'
