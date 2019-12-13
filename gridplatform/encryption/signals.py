# -*- coding: utf-8 -*-
"""
Signals of the encryption app.

.. data:: encryption_key_created = Signal(providing_args=['key', 'key_id'])

    :class:`django.dispatch.Signal` signalled when an encryption key is
    created.  Can be used to grant the key to user currently logged in.

.. data:: encryption_user_created = Signal(providing_args=['user'])

    Creation of encryption users cannot reasonably be observed with model
    signals --- user must be created/saved to get ID, before being assigned
    private key and userprofile.  *Must* be explicitly sent by code creating
    users.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

from django.dispatch import Signal


encryption_key_created = Signal(providing_args=['key', 'key_id'])

encryption_user_created = Signal(providing_args=['user'])
