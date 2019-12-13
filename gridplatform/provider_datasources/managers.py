# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db.models.query import QuerySet
from django.db import models
from django.db.models.query import DateQuerySet
from django.db.models.query import DateTimeQuerySet
from django.db.models.query import ValuesListQuerySet
from django.db.models.query import ValuesQuerySet

from gridplatform.utils.models import StoredSubclassManager
from gridplatform.datasources.managers import DataSourceQuerySetMixinBase


class ProviderDataSourceQuerySetMixin(DataSourceQuerySetMixinBase):
    """
    Ensures that only ProviderDataSources that should be visible are visible.

    ProviderDataSources are visible to users that belong directly to the
    provider and users that belong to a customer of that provider.
    """

    def _apply_customer_filtering(self, customer_id):
        """
        Rows must belong to the :class:`.Provider` of the given :class:`.Customer`.

        :param customer_id:  The id of the given :class:`.Customer`.
        """
        self.query.add_q(models.Q(provider__customer__id=customer_id))

    def _apply_provider_filtering(self, provider_id):
        """
        Rows must belong to the given :class:`.Provider`.

        :param provider_id: The id of the given :class:`.Provider`.
        """
        self.query.add_q(models.Q(provider_id=provider_id))


class ProviderDataSourceManagerBase(models.Manager):
    """
    Base class for model managers for the :class:`.ProviderDataSource` model,
    all whose querysets have been mixed with the
    :class:`.ProviderDataSourceQyerySetMixin` to ensure visibility only to
    intended audience.
    """
    class _QuerySet(ProviderDataSourceQuerySetMixin, QuerySet):
        pass

    class _ValuesQuerySet(ProviderDataSourceQuerySetMixin, ValuesQuerySet):
        pass

    class _ValuesListQuerySet(
            ProviderDataSourceQuerySetMixin, ValuesListQuerySet):
        pass

    class _DateQuerySet(ProviderDataSourceQuerySetMixin, DateQuerySet):
        pass

    class _DateTimeQuerySet(ProviderDataSourceQuerySetMixin, DateTimeQuerySet):
        pass

    def get_queryset(self):
        qs = super(ProviderDataSourceManagerBase, self).get_queryset()
        kwargs = {
            'klass': self._QuerySet,
            '_ValuesQuerySet': self._ValuesQuerySet,
            '_ValuesListQuerySet': self._ValuesListQuerySet,
            '_DateQuerySet': self._DateQuerySet,
            '_DateTimeQuerySet': self._DateTimeQuerySet,
        }
        return qs._clone(**kwargs)


class ProviderDataSourceManager(
        StoredSubclassManager, ProviderDataSourceManagerBase):
    """
    A model manager that is both a :class:`.StoredSubclassManager` and a
    :class:`.ProviderDataSourceManagerBase`.
    """
    use_for_related_fields = False
