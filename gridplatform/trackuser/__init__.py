# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import functools
from threading import local


# Store members cannot be initialised statically as that would happen in one
# thread, thus getattr is used below.
_store = local()


def get_user():
    """
    The currently logged-in user, tracked through middleware.
    """
    return getattr(_store, 'user', None)


def _get_user_customer():
    """
    The customer of the currently logged in user, if any.  Used to filter data
    to only display what is related to this specific customer, and, where
    appliccable, as the default/selected customer on model object creation.
    Some models are entirely inaccessible when the user is associated with a
    customer.
    """
    return getattr(get_user(), 'customer', None)


# DEPRECATED
def _get_override_customer():
    """
    Access is limited as if this was the customer of the current user (unless
    the user has an explicit customer; then that takes precedence).  Used for
    the --- to be removed --- "log in as customer" feature.
    """
    return getattr(_store, 'override_customer', None)


def _get_selected_customer():
    """
    The "active" customer, selected on partner/provider parts of the
    GridPortal.  Used to filter customer-related data and as the
    default/selected customer on model object creation.  Unlike "user
    customer"/"override customer", the presence of a "selected customer" does
    not imply any filtering of the models *not* related to any customers.
    """
    return getattr(_store, 'selected_customer', None)


def get_customer():
    """
    The appropriate "default" customer for model object creation.  A user with
    an associated customer is limited to only accessing that customer; override
    has a similar effect; and otherwise a selected customer is used.
    """
    return _get_user_customer() or \
        _get_override_customer() or \
        _get_selected_customer()


def get_provider():
    """
    The provider of the currently logged-in user. Requires that the user has
    permission to decrypt provider.
    """
    return getattr(get_user(), 'provider', None) or \
        getattr(get_customer(), 'provider', None)


def get_provider_id():
    """
    The provider id of the currently logged-in user.  Used to filter data
    associated with providers.
    """
    return getattr(get_user(), 'provider_id', None) or \
        getattr(get_customer(), 'provider_id', None)


def get_timezone():
    """
    Get the timezone of the customer we are currently logged in as/working
    with.
    """
    return getattr(get_customer(), 'timezone', None)


def get_current_date():
    """
    Get the current date for the customer that we are currently logged in
    as/working with.
    """
    customer = get_customer()
    if customer is not None:
        return customer.now().date()
    else:
        return None


# DEPRECATED
def _set_user(user):
    # assert getattr(settings, 'TRACKUSER_TESTMODE', False)
    _store.user = user


# DEPRECATED
def _set_customer(customer):
    # assert getattr(settings, 'TRACKUSER_TESTMODE', False)
    _store.override_customer = customer


class _StoreOverride(object):
    def __init__(self, replacement, attr=None):
        self.attr = attr
        self.replacement = replacement
        self.old = None

    def __enter__(self):
        self.old = getattr(_store, self.attr, None)
        setattr(_store, self.attr, self.replacement)

    def __exit__(self, exc_type, exc_value, traceback):
        setattr(_store, self.attr, self.old)


replace_user = functools.partial(_StoreOverride, attr='user')
replace_override_customer = functools.partial(
    _StoreOverride, attr='override_customer')
replace_selected_customer = functools.partial(
    _StoreOverride, attr='selected_customer')

# DEPRECATED?
replace_customer = replace_override_customer
