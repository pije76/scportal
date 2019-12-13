# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import binascii

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from gridplatform.encryption import _set_ephemeral_private_key
from gridplatform.trackuser import _set_user
from gridplatform.trackuser import _set_customer

from .models import TokenData
from .models import TOKEN_LENGTH


class EncryptionTokenAuthentication(BaseAuthentication):
    """
    :class:`rest_framework.authentication.BaseAuthentication` specialization,
    replacing :class:`rest_framework.authentication.TokenAuthentication` using
    :class:`.TokenData`.
    """

    def authenticate(self, request):
        """
        Similar to
        :meth:`rest_framework.authentication.TokenAuthentication.authenticate`
        but with the addition that if the request is not being made using HTTPS
        while settings are not set to ``DEBUG``, the authentication fails.
        """
        if not request.is_secure() and not settings.DEBUG:
            return None
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b'token':
            return None
        if len(auth) == 1:
            raise AuthenticationFailed(
                'Invalid token header. No credentials provided.')
        elif len(auth) > 2:
            raise AuthenticationFailed(
                'Invalid token header. '
                'Token string should not contain spaces.')

        return self.authenticate_credentials(auth[1])

    def authenticate_credentials(self, key):
        """
        Similar to
        :meth:`rest_framework.authentication.TokenAuthentication.authenticate_credentials`,
        except ``key`` isn't really key, rather its a token from which key is
        to be extracted.

        Also global encryption context and user tracking is set according to
        the authenticated user if credentials were authentic.

        :see: :meth:`.TokenData.lookup_token`.
        """
        assert isinstance(key, bytes)
        if len(key) != TOKEN_LENGTH:
            raise AuthenticationFailed('Invalid token')
        try:
            binascii.unhexlify(key)
        except TypeError:
            raise AuthenticationFailed('Invalid token')
        try:
            token_data = TokenData.lookup_token(key)
        except TokenData.DoesNotExist:
            raise AuthenticationFailed('Invalid token')
        user = token_data.user
        if not user.is_active:
            raise AuthenticationFailed('User inactive or deleted')
        password = token_data.decrypt_password(key)
        if not user.check_password(password):
            raise AuthenticationFailed('Invalid token')
        _set_user(user)
        _set_ephemeral_private_key(user.decrypt_private_key(password))
        _set_customer(user.customer)
        return (user, None)

    def authenticate_header(self, request):
        return 'Token'
