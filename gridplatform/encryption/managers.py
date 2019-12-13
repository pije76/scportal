# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from functools import cmp_to_key

from django.db.models.query import QuerySet
from django.db import models


def cross_relation_getattr(obj, attr_path):
    """
    Get attribute by Django ORM style dunder
    (``cross__relation__path__to_attribute``) path (but on python objects
    rather than on database relations).  This is useful when the attributes are
    not part of the ORM.
    """
    if attr_path == '':
        return obj
    paths = attr_path.split('__')
    try:
        for path in paths:
            obj = getattr(obj, path)
        return obj
    except AttributeError:
        return ''


class DecryptingOrderingMixin(object):
    """
    Mixes :meth:`.DecryptingOrderingMixin.decrypting_order_by` and
    :meth:`.DecryptingOrderingMixin.iterator` into a :class:`.QuerySet` class,
    to enable ordering according to values on encrypted fields.
    """
    _decrypt_ordering = []

    def decrypting_order_by(self, *field_names):
        """
        Return a clone of this QuerySet ordering according to the given field
        names.

        :param field_names: The given field names.  E.g. if ``name`` is an
            encrypted field, use ``'name_plain'``.  Field names may be ORM
            style cross relation paths.  See :func:`.cross_relation_getattr`.
        """
        obj = self._clone()
        obj.query.clear_ordering(force_empty=False)
        obj._decrypt_ordering = field_names
        return obj

    def iterator(self):
        """
        Iterate objects in decrypted order.
        """
        objects = super(DecryptingOrderingMixin, self).iterator()
        if self._decrypt_ordering:
            return sorted(objects, key=cmp_to_key(self._decrypt_compare))
        return objects

    def _decrypt_compare(self, x, y):
        for field_name in self._decrypt_ordering:
            if field_name.startswith('-'):
                field_name = field_name[1:]
                return cmp(
                    unicode(cross_relation_getattr(y, field_name)).lower(),
                    unicode(cross_relation_getattr(x, field_name)).lower())
            else:
                return cmp(
                    unicode(cross_relation_getattr(x, field_name)).lower(),
                    unicode(cross_relation_getattr(y, field_name)).lower())

    def _clone(self, *args, **kwargs):
        c = super(DecryptingOrderingMixin, self)._clone(*args, **kwargs)
        c._decrypt_ordering = self._decrypt_ordering
        return c

    def __getitem__(self, k):
        if self._decrypt_ordering:
            return list(self)[k]
        else:
            return super(DecryptingOrderingMixin, self).__getitem__(k)


class DecryptingFilteringMixin(object):
    """
    Mixes :meth:`.DecryptingFilteringMixin.decrypting_search` and
    :meth:`.DecryptingFilteringMixin.iterator` into a :class:`.QuerySet` class,
    to enable filtering according to plaintext values of encrypted fields.
    """
    _decrypting_search_parameters = ()

    def decrypting_search(self, needle, field_names):
        """
        Search for needle in given fields.

        :param needle: The needle to search for.
        :param field_names: The attribute names to search among.  E.g. if
            ``name`` is an encrypted field, use ``'name_plain'``.  Field names
            may be ORM style cross relation paths.  See
            :func:`.cross_relation_getattr`.
        """
        obj = self._clone()
        obj._decrypting_search_parameters = \
            self._decrypting_search_parameters + \
            ((unicode(needle).lower(), field_names),)
        return obj

    def iterator(self):
        objects = super(DecryptingFilteringMixin, self).iterator()
        if self._decrypting_search_parameters:
            for needle, field_names in self._decrypting_search_parameters:
                objects = [obj for obj in objects if self._satifies_search(
                    obj, needle, field_names)]
        return objects

    @staticmethod
    def _satifies_search(obj, needle, field_names):
        for field_name in field_names:
            if needle in unicode(
                    cross_relation_getattr(obj, field_name)).lower():
                return True
        return False

    def _clone(self, *args, **kwargs):
        c = super(DecryptingFilteringMixin, self)._clone(*args, **kwargs)
        c._decrypting_search_parameters = self._decrypting_search_parameters
        return c

    def __getitem__(self, k):
        if self._decrypting_search_parameters:
            return list(self)[k]
        else:
            return super(DecryptingFilteringMixin, self).__getitem__(k)


class DecryptingQuerySet(
        DecryptingOrderingMixin, DecryptingFilteringMixin, QuerySet):
    """
    A :class:`.QuerySet` that has both :class:`.DecryptingOrderingMixin` and
    :class:`.DecryptingFilteringMixin` mixed into it.
    """
    pass


class DecryptingManager(models.Manager):
    """
    A :class:`django.db.models.Manager` specialization that uses
    :class:`.DecryptingQuerySet` for its querysets, and provides manager level
    versions of :meth:`.DecryptingOrderingMixin.decrypting_order_by` and
    :meth:`.DecryptingFilteringMixin.decrypting_search`.
    """
    def get_queryset(self):
        qs = super(DecryptingManager, self).get_queryset()
        return qs._clone(klass=DecryptingQuerySet)

    def decrypting_search(self, *args, **kwargs):
        return self.get_queryset().decrypting_search(*args, **kwargs)

    def decrypting_order_by(self, *args, **kwargs):
        return self.get_queryset().decrypting_order_by(*args, **kwargs)
