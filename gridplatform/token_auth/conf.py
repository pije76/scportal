# -*- coding: utf-8 -*-
"""
.. py:data:: settings.TOKEN_AUTH_USER_PASSWORD_LENGTH

    The password length used for token auth users.  Defaults to 16.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.encryption.conf import settings

from appconf import AppConf


__all__ = ['settings', 'TokenAuthConf']


class TokenAuthConf(AppConf):
    USER_PASSWORD_LENGTH = 16
