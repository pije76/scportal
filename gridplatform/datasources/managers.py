# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db.models.query import QuerySet
from django.db import models
from django.db.models.query import DateQuerySet
from django.db.models.query import DateTimeQuerySet
from django.db.models.query import ValuesListQuerySet
from django.db.models.query import ValuesQuerySet

from gridplatform.trackuser.managers import FilteringQuerySetMixinBase
from gridplatform.trackuser import get_user
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_provider_id
from gridplatform.utils.models import StoredSubclassManager


class DataSourceQuerySetMixinBase(FilteringQuerySetMixinBase):
    """
    Help ensuring that only DataSources that should be visible are visible.
    """

    def _apply_filtering(self):
        """
        Implementation of :meth:`FilteringQuerySetMixinBase._apply_filtering`.

        If no user is logged in, no filtering is applied (for shell command).
        For unauthenticated users the queryset is emptied.

        If user is limited to only one
        :class:`~gridplatform.customers.models.Customer` (at this time) and
        that customer is inactive, the queryset is emptied, if the customer is
        active, further filtering is delegated to
        :meth:`.DataSourceQuerySetMixinBase._apply_customer_filtering`.

        If user is a provider user and not limited to a particular customer at
        this time, further filtering is delegated to
        :meth:`.DataSourceQuerySetMixinBase._apply_provider_filtering`.

        Finally, if user is neither customer user nor provider user, he must be
        admin, and no filtering is applied.
        """
        user = get_user()
        if user is None:
            return
        if not user.is_authenticated():
            self.query.set_empty()
            return
        # user customer or override customer or selected customer
        customer = get_customer()
        if customer is not None:
            if not customer.is_active:
                self.query.set_empty()
                return
            self._apply_customer_filtering(customer.id)
            return
        provider_id = get_provider_id()
        if provider_id:
            self._apply_provider_filtering(provider_id)
            return
        assert user.is_staff, \
            'non-staff user {} without customer or provider; ' + \
            'should not exist'.format(user.id)
        return

    def _apply_customer_filtering(self, customer_id):
        """
        Abstract method for filtering on a given customer.
        """
        raise NotImplementedError(self.__class__)

    def _apply_provider_filtering(self, provider_id):
        """
        Abstract method for filtering on a given provider.
        """
        raise NotImplementedError(self.__class__)


class DataSourceQuerySetMixin(DataSourceQuerySetMixinBase):
    """
    Ensures that only DataSources that should be visible are visible.  In
    particular DataSources that are CustomerDataSources may only be seen by
    users that are authorized to see that particular customer.
    """

    def _apply_customer_filtering(self, customer_id):
        """
        Rows that represent :class:`.CustomerDataSource` must belong to given :class:`.Customer`.

        Rows that represent :class:`.ProviderDataSource` must belong to the
        :class:`.Provider` of the given :class:`.Customer`.

        :param customer_id:  The id of the given :class:`.Customer`.
        """
        self.query.add_q(
            models.Q(customerdatasource__customer__id=customer_id) |
            models.Q(customerdatasource__isnull=True))
        self.query.add_q(
            models.Q(providerdatasource__provider__customer__id=customer_id) |
            models.Q(providerdatasource__isnull=True))

    def _apply_provider_filtering(self, provider_id):
        """
        Rows that represent :class:`.CustomerDataSource` must belong to a
        :class:`.Customer` of the given :class:`.Provider`.

        Rows that represent :class:`.ProviderDataSource` must belong to the
        given :class:`.Provider`.

        :param provider_id:  The id of the given :class:`.Provider`.
        """
        self.query.add_q(
            models.Q(
                customerdatasource__customer__provider_id=provider_id) |
            models.Q(customerdatasource__isnull=True))
        self.query.add_q(
            models.Q(
                providerdatasource__provider_id=provider_id) |
            models.Q(providerdatasource__isnull=True))


class DataSourceManagerBase(models.Manager):
    """
    A manager that mixes :class:`.DataSourceQuerySetMixin` into all its
    queryset classes.
    """
    class _QuerySet(DataSourceQuerySetMixin, QuerySet):
        pass

    class _ValuesQuerySet(DataSourceQuerySetMixin, ValuesQuerySet):
        pass

    class _ValuesListQuerySet(DataSourceQuerySetMixin, ValuesListQuerySet):
        pass

    class _DateQuerySet(DataSourceQuerySetMixin, DateQuerySet):
        pass

    class _DateTimeQuerySet(DataSourceQuerySetMixin, DateTimeQuerySet):
        pass

    def get_queryset(self):
        qs = super(DataSourceManagerBase, self).get_queryset()
        kwargs = {
            'klass': self._QuerySet,
            '_ValuesQuerySet': self._ValuesQuerySet,
            '_ValuesListQuerySet': self._ValuesListQuerySet,
            '_DateQuerySet': self._DateQuerySet,
            '_DateTimeQuerySet': self._DateTimeQuerySet,
        }
        return qs._clone(**kwargs)


class DataSourceManager(
        StoredSubclassManager, DataSourceManagerBase):
    """
    A manager that is both a :class:`.StoredSubclassManager` and a
    :class:`DataSourceManagerBase`.
    """
    use_for_related_fields = False
