# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from functools import wraps

from django.utils.decorators import available_attrs
from django.http import HttpResponseForbidden
from django.contrib.auth.views import redirect_to_login

from gridplatform.trackuser import get_user


def admin_or_error(view_func):
    """
    Decorator for views that checks that the current user has admin privileges,
    and returns a HTTP Forbidden if not.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrapper(request, *args, **kwargs):
        user = get_user()
        if user is not None and user.is_authenticated() and user.is_admin:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()
    return wrapper


def admin_or_redirect(view_func):
    """
    Decorator for views that checks that the current user has admin privileges,
    and redirects to the login page if not.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrapper(request, *args, **kwargs):
        user = get_user()
        if user is not None and user.is_authenticated() and user.is_admin:
            return view_func(request, *args, **kwargs)
        else:
            return redirect_to_login(request.get_full_path())
    return wrapper


def auth_or_error(view_func):
    """
    Decorator for views that checks that the current user is logged in, and
    returns a HTTP Forbidden if not.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrapper(request, *args, **kwargs):
        user = get_user()
        if user is not None and user.is_authenticated():
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()
    return wrapper


def auth_or_redirect(view_func):
    """
    Decorator for views that checks that the current user is logged in, and
    redirects to the login page if not.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrapper(request, *args, **kwargs):
        user = get_user()
        if user is not None and user.is_authenticated():
            return view_func(request, *args, **kwargs)
        else:
            return redirect_to_login(request.get_full_path())
    return wrapper


def customer_admin_or_error(view_func):
    """
    Decorator for views that checks that the current user has administrative
    privileges for the current customer, and returns a HTTP Forbidden if not.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrapper(request, *args, **kwargs):
        user = get_user()
        if user is not None and user.is_authenticated() and \
            (user.is_customer_superuser or
             (user.is_admin and
              getattr(request, 'customer', None) is not None)):
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()
    return wrapper


def customer_admin_or_admin_or_error(view_func):
    """
    Decorator for views that checks that the current user has administrative
    privileges or administrative privileges for the current customer,
    and returns a HTTP Forbidden if not.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrapper(request, *args, **kwargs):
        user = get_user()
        if user is not None and user.is_authenticated() and \
                (user.is_customer_superuser or user.is_admin):
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()
    return wrapper
