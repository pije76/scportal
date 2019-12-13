# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from functools import wraps
from exceptions import DeprecationWarning
import warnings
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test

from gridplatform.trackuser import get_provider_id


def deprecated(message_or_function):
    """
    Decorator to raise a deprecation warning on method call.

    Can be used either as ``@deprecated(message)`` or just
    ``@deprecated`` --- in the second form, the message will be
    constructed as ``"'method name' is deprecated"``
    """
    def wrap_function(f, message):
        @wraps(f)
        def wrapper(*args, **kwargs):
            warnings.warn(message,
                          DeprecationWarning, stacklevel=2)
            return f(*args, **kwargs)
        return wrapper
    if callable(message_or_function):
        f = message_or_function
        message = '%s is deprecated' % (f.__name__,)
        return wrap_function(f, message)
    else:
        message = message_or_function
        return lambda f: wrap_function(f, message)


def virtual(f):
    """
    Helper for delegating methods to ``subclass_instance`` from classes based
    on ``StoreSubclass``.

    Use on the base class method to have it delegate to the subclass.  The
    implementation of the base class will still be used if the subclass does
    not override it --- though it will then be run with the subclass instance
    as ``self``.  This can be used to implement pure virtual methods; e.g.::

        @virtual
        def __unicode__(self):
            raise NotImplementedError(self.__class__)

    where ``self.__class__`` in the exception will indicate the concrete
    subclass.
    """
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if self.__class__ != self.subclass.model_class():
            return getattr(self.subclass_instance, f.__name__)(*args, **kwargs)
        else:
            return f(self, *args, **kwargs)
    return wrapper


def permission_required(
        perm=None, requires_is_staff=False, requires_provider=False,
        login_url=None, raise_exception=False):
    """
    Extended version of
    :func:`django.contrib.auth.decorators.permission_required`, to
    include ``requires_is_staff`` and ``requires_provider`` checks.
    """
    def check_perms(user):
        passes = True
        if requires_is_staff and not user.is_staff:
            passes = False
        if requires_provider and \
                not (user.is_authenticated() and get_provider_id()):
            passes = False
        if perm is not None and not user.has_perm(perm):
            passes = False
        if passes:
            return True
        # In case the 403 handler should be called raise the exception
        if raise_exception:
            raise PermissionDenied
        # As the last resort, show the login form
        return False
    return user_passes_test(check_perms, login_url=login_url)
