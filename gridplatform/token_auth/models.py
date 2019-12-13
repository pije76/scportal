# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import binascii
import hashlib
import hmac
import uuid

from django.db import models
from django.utils.encoding import force_bytes
from django.utils.translation import ugettext_lazy as _


from Crypto.Cipher import AES
from Crypto import Random

from .conf import settings

HMAC_HEX_LENGTH = 40
IV_LENGTH = AES.block_size

TOKEN_LENGTH = HMAC_HEX_LENGTH + IV_LENGTH * 2 + \
    settings.TOKEN_AUTH_USER_PASSWORD_LENGTH * 2


def create_token(user, password):
    """
    Construct a new authentication token for the specified user; assuming/using
    the specified login (and data decryption) password.
    """
    token_data, created = TokenData.objects.get_or_create(user=user)
    return token_data.provide_token(password)


class TokenData(models.Model):
    """
    Extra information necessary to provide API tokens for a specific `User`.

    Token users are assumed to not be normal login users, and to have passwords
    of length `settings.TOKEN_AUTH_USER_PASSWORD_LENGTH`.  (Passwords still
    necessary to support encryption system.)
    """
    key = models.CharField(
        _('token identifier'), max_length=HMAC_HEX_LENGTH, primary_key=True)
    user = models.OneToOneField('users.User', verbose_name=_('user'))
    cipher = models.BinaryField(_('cipher to decrypt tokens'))

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = hmac.new(
                uuid.uuid4().bytes, digestmod=hashlib.sha1).hexdigest()
        if not self.cipher:
            self.cipher = Random.new().read(settings.ENCRYPTION_AES_KEYLENGTH)
        return super(TokenData, self).save(*args, **kwargs)

    def provide_token(self, password):
        """
        Construct a token string for the specified `password`.

        :note: The password is not validated for the user; if invalid, the
            resulting token string will not be usable for API login.
        """
        password_bytes = force_bytes(password)
        assert len(password_bytes) == settings.TOKEN_AUTH_USER_PASSWORD_LENGTH
        iv = Random.new().read(IV_LENGTH)
        cipher = AES.new(self.cipher, AES.MODE_CFB, iv)
        encrypted_password = cipher.encrypt(password_bytes)
        return b''.join([
            force_bytes(self.key),
            binascii.hexlify(iv),
            binascii.hexlify(encrypted_password)])

    def decrypt_password(self, token):
        """
        Decrypt/extract the password part from the specified `token`.

        :note: Invalid tokens will still decrypt to something, if they have the
            appropriate form --- correct length and containing only valid
            hexadecimal characters.
        """
        assert len(token) == TOKEN_LENGTH, \
            b'Token {} wrong length'.format(token)
        non_key = token[HMAC_HEX_LENGTH:]
        iv = binascii.unhexlify(non_key[:IV_LENGTH * 2])
        encrypted_password = binascii.unhexlify(non_key[IV_LENGTH * 2:])
        cipher = AES.new(self.cipher, AES.MODE_CFB, iv)
        return cipher.decrypt(encrypted_password)

    @classmethod
    def lookup_token(cls, token):
        """
        Only part of a token string is actually saved (the _key_).  This method
        extracts the key from a given token and returns the corresponding
        :class:`.TokenData` instance.

        :rtype: :class:`.TokenData`

        :param token:  The given token string containing _key_.
        """
        assert len(token) == TOKEN_LENGTH, \
            b'Token {} wrong length'.format(token)
        key = token[:HMAC_HEX_LENGTH]
        return cls.objects.get(key=key)
