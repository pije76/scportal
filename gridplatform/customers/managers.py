# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals


# from django.db.models.query import QuerySet
from django.db.models.query import DateQuerySet
from django.db.models.query import DateTimeQuerySet
from django.db.models.query import ValuesListQuerySet
from django.db.models.query import ValuesQuerySet
from django.db.models.query_utils import Q

from gridplatform.encryption.managers import DecryptingManager
from gridplatform.encryption.managers import DecryptingQuerySet
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_user
from gridplatform.trackuser import get_provider_id
from gridplatform.trackuser.managers import FilteringQuerySetMixinBase


class CustomerQuerySetMixin(FilteringQuerySetMixinBase):
    """
    Slightly modified variant of code from
    :class:`gridplatform.trackuser.managers.CustomerBoundQuerySetMixin`
    """
    def _apply_filtering(self):
        """
        Filters out customers different from the customer of a customer user or the
        selected customer for a provider user (if any is selected).  For these
        users inactive customers are also excluded.

        For provider users without any particular customer selected, only
        customers that belong to that provider will pass the filter.  For these
        provider users inactive customers are not excluded.
        """
        user = get_user()
        if user is None:
            return
        if not user.is_authenticated():
            self.query.set_empty()
            return
        customer = get_customer()
        if customer is not None:
            if not customer.is_active:
                self.query.set_empty()
                return
            id_field = 'id'
            kwargs = {id_field: customer.id}
            self.query.add_q(Q(**kwargs))
            return
        provider_id = get_provider_id()
        if provider_id:
            kwargs = {'provider_id': provider_id}
            self.query.add_q(Q(**kwargs))
            return
        assert user.is_staff, \
            'non-staff user {} without customer or provider; ' + \
            'should not exist'.format(user.id)
        return


class CustomerManager(DecryptingManager):
    """
    Manager for :class:`Customer` model ensuring that only customers that the
    user is supposed to see will be accessible.

    Querysets of this manager are mixed with the
    :class:`.CustomerQuerySetMixin`.
    """

    _field = None

    class _QuerySet(CustomerQuerySetMixin, DecryptingQuerySet):
        pass

    class _ValuesQuerySet(CustomerQuerySetMixin, ValuesQuerySet):
        pass

    class _ValuesListQuerySet(CustomerQuerySetMixin, ValuesListQuerySet):
        pass

    class _DateQuerySet(CustomerQuerySetMixin, DateQuerySet):
        pass

    class _DateTimeQuerySet(CustomerQuerySetMixin, DateTimeQuerySet):
        pass

    def get_queryset(self):
        qs = super(CustomerManager, self).get_queryset()
        kwargs = {
            'klass': self._QuerySet,
            '_filter_field': self._field,
            '_ValuesQuerySet': self._ValuesQuerySet,
            '_ValuesListQuerySet': self._ValuesListQuerySet,
            '_DateQuerySet': self._DateQuerySet,
            '_DateTimeQuerySet': self._DateTimeQuerySet,
        }
        return qs._clone(**kwargs)
