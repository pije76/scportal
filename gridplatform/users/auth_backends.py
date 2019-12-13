# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.auth.backends import ModelBackend

from gridplatform import trackuser
from gridplatform import encryption

from .managers import hash_username
from .models import User


class HashedUsernameBackend(ModelBackend):
    """
    Custom authentication backend; uses hash of provided username rather than
    provided username directly.  This works with our custom UserManager which
    uses the same hash function on creating users.
    """
    def authenticate(self, username=None, password=None):
        try:
            user = User._all_users.get(username=hash_username(username))
            if user.check_password(password):
                trackuser._store.user = user
                encryption._store.private_key = user.decrypt_private_key(
                    password)
                return user
        except User.DoesNotExist:
            pass
        return None

    def get_user(self, user_id):
        try:
            return User._all_users.get(pk=user_id)
        except User.DoesNotExist:
            return None
