# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals


class NestedMixin(object):
    """
    Mixin to be used by nested viewsets allowing them to simply overwrite
    :attr:`filter_by` to enable queryset filtering.

    :ivar filter_by: List of nesting parameter names used to filter queryset.
    """
    filter_by = None

    def get_queryset(self):
        qs = super(NestedMixin, self).get_queryset()
        filters = {
            key: value
            for key, value in self.kwargs.items()
            if key in self.filter_by
        }
        return qs.filter(**filters)
