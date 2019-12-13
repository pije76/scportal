# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import base64
import pickle

from django.core import signing

from .conf import settings

from .base import EncryptionContext
from .base import _store
from .base import get_cipher_module


def _will_refresh_session_cookie(request, response):
    """
    Determine whether the session cookie should be set/refreshed --- logic
    taken from django.contrib.sessions.middleware.SessionMiddleware.
    """
    try:
        modified = request.session.modified
    except AttributeError:
        return False
    return (modified or settings.SESSION_SAVE_EVERY_REQUEST) and \
        response.status_code != 500


def _session_cookie_max_age(request):
    """
    Determine appropriate max_age for cookie --- logic taken from
    django.contrib.sessions.middleware.SessionMiddleware.
    """
    # HttpResponse.set_cookie() will construct expires from max_age; including
    # the logic here is not necessary.
    if request.session.get_expire_at_browser_close():
        max_age = None
    else:
        max_age = request.session.get_expiry_age()
    return max_age




class EncryptionMiddleware(object):
    """
    Middleware to manage 'secret' data; storing an attribute of the request
    encrypted such that the server has the ciphertext (as a session variable)
    while the client has the key (in a cookie).  The data is decrypted with the
    received key on each request and encrypted and stored if changed on each
    response.

    Implementation notes:

    Encryption key is sent to browser in cookie.
    Ciphertext and initialisation vector is stored in session.

    The locations to store the key and ciphertext are obvious --- sending much
    data in cookies is problematic, so the ciphertext needs to stay on the
    server, and the key should then *not* be stored on the server.

    The choice of where to store the initialisation vector is less
    straightforward, though keeping it on the server greatly simplifies
    synchronisation between browser and server: On storing new data, we must
    generate a new initialisation vector, and keeping it on the server means
    that the current credentials known by the client are still valid, which
    saves us from various ugly edge cases...  (Our use might be a special case
    where reusing the initialisation vector is not as big a problem as it
    usually is --- but then again, it might not, and it's better to be safe
    than sorry...)

    If data has not changed, then we will *not* update the data stored for the
    session.  Checking for this adds some complexity, but reduces the database
    load --- depending on session configuration this may entirely avoid hitting
    the database --- and in particular, this avoids what could otherwise be
    some *really* stupid transaction errors in case of parallel requests that
    semantically should be read-only.
    """

    def process_request(self, request):
        if settings.ENCRYPTION_TESTMODE or request.META['PATH_INFO'] == '/Wibeee/receiver' or request.META['PATH_INFO'] == '/Wibeee/receiverJSON':
            return
        setattr(_store, settings.ENCRYPTION_STORE_KEY, None)
        setattr(_store, settings.ENCRYPTION_EPHEMERAL_STORE_KEY, None)
        setattr(_store, settings.ENCRYPTION_ORIGINAL_STORE_KEY, None)
        if 'encryption_context' in request.session:
            from django.contrib.auth import logout
            logout(request)
            return
        try:
            key_cookie = request.COOKIES[settings.ENCRYPTION_COOKIE_NAME]
            data = request.session[settings.ENCRYPTION_SESSION_KEY]
        except KeyError:
            # Cookie, data or both are missing; nothing to do.
            return
        b64_key = signing.loads(key_cookie, salt=settings.ENCRYPTION_SIGN_SALT)
        key = base64.b64decode(b64_key)
        iv, ciphertext = data
        cipher = get_cipher_module().symmetric_cipher(key, iv)
        plaintext = cipher.decrypt(ciphertext)
        data = pickle.loads(plaintext)
        setattr(_store, settings.ENCRYPTION_STORE_KEY, data)
        setattr(_store, settings.ENCRYPTION_ORIGINAL_STORE_KEY, data)

    def process_response(self, request, response):
        if settings.ENCRYPTION_TESTMODE:
            return
        if request.META['PATH_INFO'] == '/Wibeee/receiver' or request.META['PATH_INFO'] == '/Wibeee/receiverJSON':
            return response

        data = getattr(_store, settings.ENCRYPTION_STORE_KEY, None)
        original_data = getattr(
            _store, settings.ENCRYPTION_ORIGINAL_STORE_KEY, None)
        setattr(_store, settings.ENCRYPTION_STORE_KEY, None)
        setattr(_store, settings.ENCRYPTION_EPHEMERAL_STORE_KEY, None)
        setattr(_store, settings.ENCRYPTION_ORIGINAL_STORE_KEY, None)
        if not hasattr(request, 'session'):
            return response
        if data is None:
            # No data to store.  Cleanup just in case; data may have been
            # removed from request but still be present on our side...
            if settings.ENCRYPTION_COOKIE_NAME in request.COOKIES:
                # Don't "delete" the cookie if it doesn't exist; as "deleting"
                # it implies setting it to "something else"; here the empty
                # string and with a timeout in the past.
                response.delete_cookie(settings.ENCRYPTION_COOKIE_NAME)
            if settings.ENCRYPTION_SESSION_KEY in request.session:
                del request.session[settings.ENCRYPTION_SESSION_KEY]
            return response
        try:
            key_cookie = request.COOKIES[settings.ENCRYPTION_COOKIE_NAME]
            # Pretend cookie does not exist if empty --- a client might not
            # check the timeout and hand us the value we "deleted" it with; and
            # this should *not* lead to an error indicating that the cookie has
            # been modified on the client side...  (The Django test client acts
            # like that; i.e. this logic is necessary for convenient
            # testing...)
            if key_cookie == '':
                raise KeyError
            b64_key = signing.loads(
                key_cookie, salt=settings.ENCRYPTION_SIGN_SALT)
            key = base64.b64decode(b64_key)
        except KeyError:
            # Cookie does not exist.  If it exists but with an invalid value,
            # signing.loads would throw BadSignature, which we don't catch
            # here.
            key = get_cipher_module().generate_symmetric_key()
        # Check whether anything has changed --- if not, we don't want to
        # modify the session state.  (Also, if the backing RNG is based on
        # Linux /dev/urandom or something similar, then the supply of random
        # bytes is actually limited, and we need a new block of random bytes
        # for the initialisation vector each time we encrypt data.)
        data_changed = (data != original_data)
        if data_changed:
            # We use the newest/most efficient version of the pickle protocol;
            # we will not need to load data with an older version of
            # Python/pickle than the one running while "now", we store it...
            # (The latest version is currently compatible with Python 2.3 and
            # forward; Python 2.3 was released in 2003.)
            plaintext = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
            # Make a new initialisation vector, encrypt data, store.  "Reuse"
            # key; if session has an active key, that will be used; otherwise a
            # new key will have been generated...
            cipher_module = get_cipher_module()
            iv = cipher_module.generate_iv()
            cipher = cipher_module.symmetric_cipher(key, iv)
            ciphertext = cipher.encrypt(plaintext)
            request.session[settings.ENCRYPTION_SESSION_KEY] = (iv, ciphertext)
        if data_changed or _will_refresh_session_cookie(request, response):
            # Wrap key in cookie, hand to client.  This will "refresh" cookie
            # expiry if already present.  To avoid strange edge cases, we will
            # set the cookie on data change and on session cookie refresh...
            # (... data change implies a session cookie refresh anyway.)
            # If the encryption cookie expires before the session cookie, the
            # resulting behaviour may be somewhat confusing to users...
            b64_key = base64.b64encode(key)
            key_cookie = signing.dumps(
                b64_key, salt=settings.ENCRYPTION_SIGN_SALT, compress=True)
            max_age = _session_cookie_max_age(request)
            response.set_cookie(
                settings.ENCRYPTION_COOKIE_NAME, key_cookie,
                max_age=max_age, httponly=True)
        return response


class KeyLoaderMiddleware(object):
    """
    Ensures that the thread-local store has an request specific
    :class:`.EncryptionContext` for loading private keys entrusted to the
    entity performing the request.
    """
    def process_request(self, request):
        if settings.ENCRYPTION_TESTMODE or request.META['PATH_INFO'] == '/Wibeee/receiver' or request.META['PATH_INFO'] == '/Wibeee/receiverJSON':
            return
        setattr(
            _store, settings.ENCRYPTION_CONTEXT_STORE_KEY, EncryptionContext())

    def process_response(self, request, response):
        if settings.ENCRYPTION_TESTMODE or request.META['PATH_INFO'] == '/Wibeee/receiver' or request.META['PATH_INFO'] == '/Wibeee/receiverJSON':
            return response
        setattr(_store, settings.ENCRYPTION_CONTEXT_STORE_KEY, None)
        return response
