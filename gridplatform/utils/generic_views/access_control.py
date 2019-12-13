# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals


import braces.views

from gridplatform.trackuser import replace_selected_customer


def _get_permission_name(action, opts):
    return '%s.%s_%s' % (opts.app_label, action, opts.object_name.lower())


class CheckAJAXMixin(object):
    """
    Set ``self.raise_exception = True`` on AJAX requests, to have
    access control return "403 Forbidden" rather than redirect to
    login page on permission denied for those.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.is_ajax():
            self.raise_exception = True
        return super(CheckAJAXMixin, self).dispatch(request, *args, **kwargs)


class LoginRequiredMixin(CheckAJAXMixin, braces.views.LoginRequiredMixin):
    """
    Mixin to check that user is logged in.
    """
    pass


class ModelPermissionRequiredMixin(
        CheckAJAXMixin, braces.views.PermissionRequiredMixin):
    """
    Mixin to simplify specifying a required model permission for a specific
    model --- where the generic view specifies the permission as "add",
    "change" or "delete"; and this will then be combined with the name of the
    concrete model in use for the concrete permission name.
    """
    model_permission = None

    @property
    def permission_required(self):
        model = self.model or self.get_queryset().model
        return _get_permission_name(self.model_permission, model._meta)


class MultipleModelPermissionsRequiredMixin(
        CheckAJAXMixin, braces.views.MultiplePermissionsRequiredMixin):
    """
    Mixin to simplify specifying a required set of permissions for a set of
    models --- generic views specify model permissions and *how* to obtain the
    list of relevant models from whatever configuration of models, formsets and
    inline-models are relevant for the view type.  (Permissions for the more
    advanced viwes from `extra_views` cannot be expressed with
    :class:`.ModelPermissionRequiredMixin`.)
    """
    model_permissions = None

    def get_permissions_models(self):
        raise NotImplementedError('not implemented by %r' % self.__class__)

    @property
    def permissions(self):
        models = self.get_permissions_models()
        return {
            'all': list({
                _get_permission_name(perm, model._meta)
                for model in models
                for perm in self.model_permissions
            })
        }


class CustomerBoundMixin(object):
    """
    Expects ``_customer`` to exist on the view using this mixin.
    """
    def dispatch(self, request, *args, **kwargs):
        with replace_selected_customer(self._customer):
            res = super(CustomerBoundMixin, self).dispatch(
                request, *args, **kwargs)
            if hasattr(res, 'render'):
                res.render()
        return res
