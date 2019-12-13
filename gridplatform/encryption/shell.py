# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.auth import authenticate

from gridplatform import trackuser

from .base import _store
from .base import EncryptionContext


class Request(object):
    """
    Class for emulating request from shell.  Sets up current user, private key
    and encryption context upon construction.
    """
    def __init__(self, username, password):
        """
        Authenticates with given user name and password.

        :param username: Given user name.
        :param password: Given password.
        """
        self.user = authenticate(username=username, password=password)
        trackuser._store.user = self.user
        _store.private_key = self.user.decrypt_private_key(password)
        _store.encryption_context = EncryptionContext()

    def __unicode__(self):
        """
        The text representation are the keys held by current encryption context.
        """
        return unicode(self.encryption_context.keys())
