# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import warnings

from django.forms import models as model_forms


class LocalizedModelFormMixin(object):
    """
    Mixin to inject ``localized_fields`` into parameters to
    ``modelform_factory()`` for Django create/update views.
    """
    localized_fields = '__all__'

    def get_form_class(self):
        """
        Copied from
        :meth:`django.views.generic.edit.ModelFormMixin.get_form_class()`;
        modified to provide ``localized_fields`` to
        ``modelform_factory()``
        """
        if self.form_class:
            return self.form_class
        else:
            if self.model is not None:
                model = self.model
            elif hasattr(self, 'object') and self.object is not None:
                model = self.object.__class__
            else:
                model = self.get_queryset().model
            if self.fields is None:
                warnings.warn(
                    "Using ModelFormMixin (base class of %s) without "
                    "the 'fields' attribute is deprecated." %
                    self.__class__.__name__,
                    PendingDeprecationWarning)
            return model_forms.modelform_factory(
                model,
                fields=self.fields,
                localized_fields=self.localized_fields)


class LocalizedModelFormSetMixin(object):
    """
    Mixin to inject ``localized_fields`` into parameters to
    ``modelformset_factory()`` for :mod:``extra_views`` formset views.
    """
    localized_fields = '__all__'

    def get_factory_kwargs(self):
        """
        inject ``localized_fields`` into kwargs
        """
        kwargs = super(LocalizedModelFormSetMixin, self).get_factory_kwargs()
        if 'localized_fields' not in kwargs:
            kwargs['localized_fields'] = self.localized_fields
        return kwargs


class LocalizedInlineFormSetMixin(object):
    """
    Mixin to inject ``localized_fields`` into parameters to
    ``inlineformset_factory()`` for :mod:`extra_views` inline views.
    """
    localized_fields = '__all__'

    def get_factory_kwargs(self):
        """
        inject ``localized_fields`` into kwargs
        """
        kwargs = super(LocalizedInlineFormSetMixin, self).get_factory_kwargs()
        if 'localized_fields' not in kwargs:
            kwargs['localized_fields'] = self.localized_fields
        return kwargs
