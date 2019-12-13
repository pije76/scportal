# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings
from django.db.models.query import DateQuerySet
from django.db.models.query import DateTimeQuerySet
from django.db.models.query import ValuesListQuerySet
from django.db.models.query import ValuesQuerySet
from django.db.models.query_utils import Q
from django.utils import timezone
from mptt.managers import TreeManager

from gridplatform.encryption.managers import DecryptingQuerySet
from gridplatform.encryption.managers import DecryptingManager
from gridplatform.utils.models import StoredSubclassManager

from . import get_customer
from . import get_user
from . import get_provider_id
from . import _get_user_customer
from . import _get_override_customer


class FilteringQuerySetMixinBase(object):
    """
    Abstract queryset mixin that adds filtering when obtaining output.  To make
    a concrete queryset mixin, one must subclass and implement
    :meth:`~.FilteringQuerySetMixinBase._apply_filtering`.  The resulting mixin
    can then be mixed with actual queryset classes to define new filtering
    queryset classes.

    For instance, this abstract queryset mixin is subclassed by the queryset
    mixin :class:`.CustomerBoundQuerySetMixin` and mixed with the queryset
    class :class:`gridplatform.encryption.managers.DecryptingQuerySet` to form
    the new queryset class :class:`CustomerBoundManagerBase._QuerySet`.

    :ivar _filter_field: Field name delegated by :meth:`._clone` for
        specializations :meth:`~FilteringQuerySetMixinBase._apply_filtering`.
        See also :class:`.CustomerBoundManagerBase._field` and
        :class:`ProviderBoundManager._field`.
    :cvar _ValuesQuerySet: ``klass`` argument used by :meth:`._clone` in
        :meth:`.values`.
    :cvar _ValuesListQuerySet: ``klass`` argument used by :meth:`._clone` in
        :meth:`.values_list`.
    :cvar _DateQuerySet: ``klass`` argument used by :meth:`._clone` in
        :meth:`.dates`.
    :cvar _DateTimeQuerySet: ``klass`` argument used by :meth:`._clone` in
        :meth:`.datetimes`.
    """
    # __len__() -> _fetch_all() -> iterator()
    # __iter__() -> _fetch_all() -> iterator()
    # __nonzero__() -> _fetch_all() -> iterator()
    # __getitem__() -> _result_cache / __iter__() -> _fetch_all() -> iterator()
    # _fetch_all() -> iterator()
    # get() -> __len__() / __getitem__() -> ... -> iterator()
    # earliest() -> _earliest_or_latest() -> get() -> ... -> iterator()
    # latest() -> _earliest_or_latest() -> get() -> ... -> iterator()
    # first() -> __getitem__() -> ... -> iterator()
    # last() -> __getitem__() -> ... -> iterator()
    # in_bulk() -> __iter__() -> ... -> iterator()

    # create(), bulk_create() not specifically handled.
    # get_or_create() as get() for reading; as create() for create...
    # _raw_delete() is used by deletion.Collector; should have a clone with
    # query filtered by then...
    # _prefetch_related_objects() is called after _result_cache is filled,
    # i.e. after filtering was relevant and has been performed.

    # Methods that give new QuerySets use _clone() --- we ensure that the
    # filtering options are transferred; after which we're back to having to
    # ensure that filtering is performed on data access.

    def iterator(self):
        """
        Ensure filtering is applied for the ``iterator()`` of actual queryset
        class.

        Methods that read/return "normal" objects all use `iterator()`
        """
        self.__ensure_filtering_applied()
        return super(FilteringQuerySetMixinBase, self).iterator()

    def aggregate(self, *args, **kwargs):
        """
        Ensure filtering is applied for the ``aggregate()`` of actual queryset
        class.
        """
        self.__ensure_filtering_applied()
        return super(FilteringQuerySetMixinBase, self).aggregate(
            *args, **kwargs)

    def count(self):
        """
        Ensure filtering is applied for the ``count()`` of actual queryset
        class.
        """
        self.__ensure_filtering_applied()
        return super(FilteringQuerySetMixinBase, self).count()

    def delete(self):
        """
        Ensure filtering is applied for the ``delete()`` of actual queryset
        class.
        """
        self.__ensure_filtering_applied()
        return super(FilteringQuerySetMixinBase, self).delete()
    delete.alters_data = True

    def update(self, **kwargs):
        """
        Ensure filtering is applied for the ``update()`` of actual queryset
        class.
        """
        self.__ensure_filtering_applied()
        return super(FilteringQuerySetMixinBase, self).update(**kwargs)
    update.alters_data = True

    def _update(self, values):
        """
        Ensure filtering is applied for the ``_update()`` of actual queryset
        class.
        """
        self.__ensure_filtering_applied()
        return super(FilteringQuerySetMixinBase, self)._update(values)
    _update.alters_data = True

    def exists(self):
        """
        Ensure filtering is applied for the ``exists()`` of actual queryset
        class.
        """
        self.__ensure_filtering_applied()
        return super(FilteringQuerySetMixinBase, self).exists()

    def _clone(self, klass=None, setup=False, **kwargs):
        """
        Specialization of ``_clone()`` of actual queryset class that ensures
        that ``self._filter_field``, ``self._ValuesQuerySet``,
        ``self._ValuesListQuerySet``, ``self._DateQuerySet`` and
        ``self._DateTimeQuerySet`` are also transfered to the cloned queryset.
        """
        clone_args = {
            '_filter_field': self._filter_field,
            '_ValuesQuerySet': self._ValuesQuerySet,
            '_ValuesListQuerySet': self._ValuesListQuerySet,
            '_DateQuerySet': self._DateQuerySet,
            '_DateTimeQuerySet': self._DateTimeQuerySet,
        }
        clone_args.update(kwargs)
        return super(FilteringQuerySetMixinBase, self)._clone(
            klass=klass, setup=setup, **clone_args)

    def _merge_sanity_check(self, other):
        super(FilteringQuerySetMixinBase, self)._merge_sanity_check(other)

    _filter_field = None
    _ValuesQuerySet = None
    _ValuesListQuerySet = None
    _DateQuerySet = None
    _DateTimeQuerySet = None

    def values(self, *fields):
        """
        Override of ``values()`` of actual queryset class returning a clone of
        ``self`` with class ``self._ValuesQuerySet``.
        """
        # NOTE: Copy from django.db.models.query.QuerySet + custom class
        return self._clone(
            klass=self._ValuesQuerySet, setup=True, _fields=fields)

    def values_list(self, *fields, **kwargs):
        """
        Override of ``values_list()`` of actual queryset class returning a
        clone of ``self`` with class ``self._ValuesListQuerySet``.
        """
        # NOTE: Copy from django.db.models.query.QuerySet + custom class
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError(
                'Unexpected keyword arguments to values_list: %s' %
                (list(kwargs),))
        if flat and len(fields) > 1:
            raise TypeError(
                "'flat' is not valid when values_list is called with more "
                "than one field.")
        return self._clone(
            klass=self._ValuesListQuerySet, setup=True, flat=flat,
            _fields=fields)

    def dates(self, field_name, kind, order='ASC'):
        """
        Override of ``dates()`` of actual queryset class returning a clone of
        ``self`` with class ``self._DatesQuerySet``.
        """
        # NOTE: Copy from django.db.models.query.QuerySet + custom class
        assert kind in ("year", "month", "day"), \
            "'kind' must be one of 'year', 'month' or 'day'."
        assert order in ('ASC', 'DESC'), \
            "'order' must be either 'ASC' or 'DESC'."
        return self._clone(
            klass=self._DateQuerySet, setup=True,
            _field_name=field_name, _kind=kind, _order=order)

    def datetimes(self, field_name, kind, order='ASC', tzinfo=None):
        """
        Override of ``values()`` of actual queryset class returning a clone of
        ``self`` with class ``self._DateTimeQuerySet``.
        """
        # NOTE: Copy from django.db.models.query.QuerySet + custom class
        assert kind in ("year", "month", "day", "hour", "minute", "second"), \
            "'kind' must be one of 'year', 'month', 'day', " + \
            "'hour', 'minute' or 'second'."
        assert order in ('ASC', 'DESC'), \
            "'order' must be either 'ASC' or 'DESC'."
        if settings.USE_TZ:
            if tzinfo is None:
                tzinfo = timezone.get_current_timezone()
        else:
            tzinfo = None
        return self._clone(
            klass=self._DateTimeQuerySet, setup=True, _field_name=field_name,
            _kind=kind, _order=order, _tzinfo=tzinfo)

    def __ensure_filtering_applied(self):
        """
        Filtering is applied the first time a specific `QuerySet` is used to
        access the database --- further filtering on the same `QuerySet` after
        we've started reading from the database would make no sense.  (At best
        it's an expensive no-op; at worst it would introduce numerous edge
        cases.)
        """
        if not getattr(self, '_filtering_applied', False):
            self._apply_filtering()
            self._filtering_applied = True

    def _apply_filtering(self):
        """
        Implementations should have side effect on `self.query` and return
        `None`.

        Various edge cases break if this is not idempotent.  For normal use,
        this will be fulfilled with no specific effort, as adding the same
        `WHERE` clause twice will have no effect on what objects are matched
        --- but don't use `datetime.datetime.now()` or similar...

        NOTE: If/when we redefine this interface, check whether it will allow a
        better `_merge_sanity_check()`.
        """
        raise NotImplementedError()


class CustomerBoundQuerySetMixin(FilteringQuerySetMixinBase):
    """
    QuerySet mixin limiting result set to rows belonging to the
    :class:`~gridplatform.customers.models.Customer` set whose data the current
    user is authorized to access.
    """
    def _apply_filtering(self):
        """
        Implementation of :meth:`FilteringQuerySetMixinBase._apply_filtering`.

        If no user is logged in, no filtering is applied (for shell command).
        For unauthenticated users the queryset is emptied.

        If user is limited to only one
        :class:`~gridplatform.customers.models.Customer` (at this time) and
        that customer is inactive, the queryset is emptied, if the customer is
        active, the queryset is filtered according to ``self._filter_field``
        which must equal the customer.

        If user is a provider user and not limited to a particular customer at
        this time, ``self._filter_field`` must equal one of the customers
        having the same :class:`~gridplatform.providers.models.Provider`.

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
            id_field = '{}_id'.format(self._filter_field)
            kwargs = {id_field: customer.id}
            self.query.add_q(Q(**kwargs))
            return
        provider_id = get_provider_id()
        if provider_id:
            provider_id_field = '{}__provider_id'.format(self._filter_field)
            kwargs = {provider_id_field: provider_id}
            self.query.add_q(Q(**kwargs))
            return
        assert user.is_staff, \
            'non-staff user {} without customer or provider; ' + \
            'should not exist'.format(user.id)
        return


class ProviderBoundQuerySetMixin(FilteringQuerySetMixinBase):
    """
    QuerySet mixin limiting result set to rows belonging to the
    :class:`~gridplatform.providers.models.Provider` whose data the current
    user is authorized to access.
    """
    def _apply_filtering(self):
        """
        Implementation of :meth:`FilteringQuerySetMixinBase._apply_filtering`.

        If no user is logged in, no filtering is applied (for shell command).
        For unauthenticated users the queryset is emptied.

        If user is limited to only one
        :class:`~gridplatform.customers.models.Customer` (at this time) the
        queryset is emptied.

        If user is a provider user and not limited to a particular customer at
        this time, ``self._filter_field`` must equal the same
        :class:`~gridplatform.providers.models.Provider`.

        Finally, if user is neither customer user nor provider user, he must be
        admin, and no filtering is applied.
        """
        user = get_user()
        if user is None:
            return
        if not user.is_authenticated():
            self.query.set_empty()
            return
        if _get_user_customer() is not None or \
                _get_override_customer() is not None:
            self.query.set_empty()
            return
        provider_id = get_provider_id()
        if provider_id:
            provider_id_field = '{}_id'.format(self._filter_field)
            kwargs = {provider_id_field: provider_id}
            self.query.add_q(Q(**kwargs))
            return
        assert user.is_staff, \
            'non-staff user {} without customer or provider; ' + \
            'should not exist'.format(user.id)
        return


class CustomerBoundManagerBase(DecryptingManager):
    """
    Base class for managers that limit their querysets to rows belonging to the
    :class:`~gridplatform.customers.models.Customer` set whose data the current
    user is authorized to access.

    :cvar _field: The name of the lookup field that points to the owning
        :class:`~gridplatform.customers.models.Customer`.  The default value is
        ``'customer'``.
    """
    _field = 'customer'

    class _QuerySet(CustomerBoundQuerySetMixin, DecryptingQuerySet):
        pass

    class _ValuesQuerySet(CustomerBoundQuerySetMixin, ValuesQuerySet):
        pass

    class _ValuesListQuerySet(CustomerBoundQuerySetMixin, ValuesListQuerySet):
        pass

    class _DateQuerySet(CustomerBoundQuerySetMixin, DateQuerySet):
        pass

    class _DateTimeQuerySet(CustomerBoundQuerySetMixin, DateTimeQuerySet):
        pass

    def get_queryset(self):
        qs = super(CustomerBoundManagerBase, self).get_queryset()
        kwargs = {
            'klass': self._QuerySet,
            '_filter_field': self._field,
            '_ValuesQuerySet': self._ValuesQuerySet,
            '_ValuesListQuerySet': self._ValuesListQuerySet,
            '_DateQuerySet': self._DateQuerySet,
            '_DateTimeQuerySet': self._DateTimeQuerySet,
        }
        return qs._clone(**kwargs)


class CustomerBoundManager(CustomerBoundManagerBase):
    """
    A :class:`.CustomerBoundManagerBase` specialization that is used for
    related fields too.

    The ``use_for_related_fields`` being ``True`` ensures that reverse
    relations also will apply the customer-bound filtering.  This could be
    useful when inspecting global resources used by different customers.  Since
    many models use the :class:`.StoredSubclassCustomerBoundManager`, this
    functionality will seem only sporadically available, and relying on it
    could be a bad idea.
    """
    use_for_related_fields = True


class TreeCustomerBoundManager(TreeManager, CustomerBoundManager):
    """
    A manager that is both a :class:`mptt.managers.TreeManager` and
    a :class:`.CustomerBoundManager`.
    """
    pass


class StoredSubclassCustomerBoundManager(
        StoredSubclassManager, CustomerBoundManagerBase):
    """
    A manager that is both a :class:`.StoredSubclassManager` and a
    :class:`CustomerBoundManagerBase`.

    Since :class:`.StoredSubclassManager` should not be used in reverse
    relations, neither can :class:`.StoredSubclassCustomerBoundManager`.
    """
    use_for_related_fields = False


class StoredSubclassTreeCustomerBoundManager(
        StoredSubclassManager, TreeManager, CustomerBoundManagerBase):
    """
    A manager that is both a :class:`.StoredSubclassManager`, a
    :class:`mptt.managers.TreeManager` and a :class:`.CustomerBoundManager`.

    Since :class:`.StoredSubclassManager` should not be used in reverse
    relations, neither can :class:`.StoredSubclassTreeCustomerBoundManager`.
    """
    use_for_related_fields = False


class ProviderBoundManager(DecryptingManager):
    """
    Base class for managers that limit their querysets to rows belonging to the
    :class:`~gridplatform.providers.models.Provider` whose data the current
    user is authorized to access.

    :cvar _field: The name of the lookup field that points to the owning
        :class:`~gridplatform.providers.models.Provider`.  The default value is
        ``'provider'``.
    """
    _field = 'provider'
    use_for_related_fields = True

    class _QuerySet(ProviderBoundQuerySetMixin, DecryptingQuerySet):
        pass

    class _ValuesQuerySet(ProviderBoundQuerySetMixin, ValuesQuerySet):
        pass

    class _ValuesListQuerySet(ProviderBoundQuerySetMixin, ValuesListQuerySet):
        pass

    class _DateQuerySet(ProviderBoundQuerySetMixin, DateQuerySet):
        pass

    class _DateTimeQuerySet(ProviderBoundQuerySetMixin, DateTimeQuerySet):
        pass

    def get_queryset(self):
        qs = super(ProviderBoundManager, self).get_queryset()
        kwargs = {
            'klass': self._QuerySet,
            '_filter_field': self._field,
            '_ValuesQuerySet': self._ValuesQuerySet,
            '_ValuesListQuerySet': self._ValuesListQuerySet,
            '_DateQuerySet': self._DateQuerySet,
            '_DateTimeQuerySet': self._DateTimeQuerySet,
        }
        return qs._clone(**kwargs)
