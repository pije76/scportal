# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from contextlib import contextmanager

from gridplatform.encryption import _store as encryption_store
from gridplatform.trackuser import _store as trackuser_store


@contextmanager
def global_context(user=None, customer=None, encryption=None):
    """
    Context manager for global context.

    :keyword user: The :class:`~gridplatform.users.models.User` to use
        inside the context.

    :keyword customer: The
        :class:`~gridplatform.customers.models.Customer` to use inside
        the context.

    :keyword encryption: The encryption context to use inside the
        context.

    :see: :func:`gridplatform.trackuser.get_user`,
        :func:`gridplatform.trackuser.get_customer` and
        :func:`gridplatform.encryption.get_encryption_context`.
    """
    # save old values
    old_encryption = encryption_store.encryption_context
    old_user = trackuser_store.user
    old_customer = trackuser_store.customer
    # set new
    encryption_store.encryption_context = encryption
    trackuser_store.user = user
    trackuser_store.customer = customer
    yield
    # restore old
    encryption_store.encryption_context = old_encryption
    trackuser_store.user = old_user
    trackuser_store.customer = old_customer
