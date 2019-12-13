# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import url
from django.core.urlresolvers import RegexURLPattern
from django.core.urlresolvers import RegexURLResolver
from django.core.urlresolvers import ResolverMatch

from .decorators import permission_required


class _ResolverPermissionMixin(object):
    _permission_decorator = None

    def resolve(self, path):
        assert self._permission_decorator is not None, \
            b'_permission_decorator attribute must be set before resolve call'
        match = super(_ResolverPermissionMixin, self).resolve(path)
        assert isinstance(match, ResolverMatch)
        match.func = self._permission_decorator(match.func)
        return match


class _PermissionURLPattern(_ResolverPermissionMixin, RegexURLPattern):
    pass


class _PermissionURLResolver(_ResolverPermissionMixin, RegexURLResolver):
    pass


def restricted_url(
        regex, view, kwargs=None, name=None,
        prefix='', permission=None, requires_is_staff=False,
        requires_provider=False):
    """
    Specialisation of the urlconf `url()` function, which wraps the view --- or
    the views resulting from an `include()` --- with `permission_required()`
    decorator with the specified `permission`.
    """
    assert permission or requires_is_staff or requires_provider

    base = url(regex, view, kwargs=None, name=None, prefix='')
    assert not isinstance(base, _ResolverPermissionMixin)

    # Metaprogramming hacks; we "just" want to inject the
    # _ResolverPermissionMixin resolve() method at the head of the MRO-chain.
    # This approach is less involved in implementation details of
    # RegexURLPattern/RegexURLResolver than reconstructing __init__()
    # parameters from the resulting objects...
    if isinstance(base, RegexURLPattern):
        base.__class__ = _PermissionURLPattern
        base._permission_decorator = permission_required(
            permission, requires_is_staff, requires_provider)
        return base
    elif isinstance(base, RegexURLResolver):
        base.__class__ = _PermissionURLResolver
        base._permission_decorator = permission_required(
            permission, requires_is_staff, requires_provider)
        return base
    else:
        raise Exception(
            b'base url() output not an instance of '
            b'RegexURLPattern or RegexURLResolver')
