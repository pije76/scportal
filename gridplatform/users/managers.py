# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.auth import hashers
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db.models.query import DateQuerySet
from django.db.models.query import DateTimeQuerySet
from django.db.models.query import ValuesListQuerySet
from django.db.models.query import ValuesQuerySet
from django.db.models.query_utils import Q
from django.utils import timezone
from django.utils.encoding import smart_str

from gridplatform.encryption.managers import DecryptingManager
from gridplatform.encryption.managers import DecryptingQuerySet
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_user
from gridplatform.trackuser import get_provider_id
from gridplatform.trackuser.managers import FilteringQuerySetMixinBase


def hash_username(username):
    """
    Hash the username, to get uniform 30-character "username" strings.
    The salt is hardcoded, to allow us to make lookups based on provided
    "plain" usernames.

    (A salt per entry, as is common for passwords, only works when we otherwise
    know which entry to check and thus which salt to use when hashing the
    comparison string.)

    This *does* make brute-force attacks on usernames "easier", as each
    potential username may be hashed and then checked against all existing
    usernames...
    """
    algorithm = 'pbkdf2_sha1'
    iterations = 10000
    salt = 'qXopipOboNOG'
    hasher = hashers.get_hasher(algorithm)
    username = smart_str(username)
    encoded = hasher.encode(username.lower(), salt, iterations)
    algorithm_, iterations_, salt_, hashed = encoded.split('$')
    assert algorithm_ == algorithm
    assert iterations_ == str(iterations)
    assert salt_ == salt
    return hashed[:30]


class UserManager(DecryptingManager, DjangoUserManager):
    """
    Base user manager without filtering --- implementing a variant of the user
    creation interface from the ``django.contrib.auth`` ``UserManager``.

    Provided separately from the manager applying filtering, as implementing
    ``create_user()`` and providing filtering is separate concerns, and
    besides, the ``User`` class in particular needs a non-filtering manager for
    the login-page and for collision-checks on creation.
    """
    def _create_user(self, *args, **kwargs):
        raise NotImplementedError(
            b'Encrypted users cannot be created with "_create_user()"')

    def create(self, *args, **kwargs):
        raise NotImplementedError(
            b'Encrypted users cannot be created with "create()"')

    def create_user(
            self, username, password, user_type,
            customer=None, provider=None, groups=None):
        """
        Creates and saves a User with the given username and password.
        """
        now = timezone.now()
        if not username:
            raise ValueError('The given username must be set')
        if not password:
            raise ValueError('The given password must be set')
        hashed_username = hash_username(username)
        # Using self.model._all_users to allow the bound manager subclass to
        # still check against unfiltered here...
        if self.model._all_users.filter(username=hashed_username).exists():
            raise ValueError('The given username already exists')

        user = self.model(
            username=hashed_username,
            is_staff=False, is_superuser=False,
            last_login=now, date_joined=now,
            customer=customer, provider=provider,
            user_type=user_type)
        user.set_password(password)
        # self.model should be User --- avoiding circular import...
        user.e_mail_plain = username
        user.name_plain = ''
        user.phone_plain = ''
        user.mobile_plain = ''
        user.save(using=self._db)
        if groups:
            user.groups = groups
            user.save(using=self._db)
        return user


class UserQuerySetMixin(FilteringQuerySetMixinBase):
    """
    Slightly modified variant of code from
    :class:`gridplatform.trackuser.managers.CustomerBoundQuerySetMixin`
    """
    def _apply_filtering(self):
        """
        Ensures that only User objects that the currently logged in user should
        have access to can be queried.

        The current user must be authenticated, or the empty queryset is
        returned.

        For customer users, and provider users who has selected a customer, the
        customer must be active or the empty queryset is returned.  If the
        customer is active, users belonging to that customer and to the
        provider related to the customer are visible.

        For provider users without a selected customer all users related to the
        same provider or related with a customer associated with the same
        provider are visible.
        """
        user = get_user()
        customer = get_customer()
        provider_id = get_provider_id()

        if user is None:
            pass
        elif not user.is_authenticated():
            self.query.set_empty()
        elif customer is not None:
            if not customer.is_active:
                self.query.set_empty()
            else:
                self.query.add_q(
                    Q(customer_id=customer.id) | Q(provider_id=provider_id))
        elif provider_id:
            self.query.add_q(
                Q(provider_id=provider_id) |
                Q(customer__provider_id=provider_id))
        else:
            assert user.is_staff, \
                'non-staff user {} without customer or provider; ' + \
                'should not exist'.format(user.id)
            pass


class BoundUserManager(UserManager):
    """
    Manager that mixes :class:`.UserQuerySetMixin` into all the querysets it
    works with.
    """
    _field = None

    class _QuerySet(UserQuerySetMixin, DecryptingQuerySet):
        pass

    class _ValuesQuerySet(UserQuerySetMixin, ValuesQuerySet):
        pass

    class _ValuesListQuerySet(UserQuerySetMixin, ValuesListQuerySet):
        pass

    class _DateQuerySet(UserQuerySetMixin, DateQuerySet):
        pass

    class _DateTimeQuerySet(UserQuerySetMixin, DateTimeQuerySet):
        pass

    def get_queryset(self):
        qs = super(UserManager, self).get_queryset()
        kwargs = {
            'klass': self._QuerySet,
            '_filter_field': self._field,
            '_ValuesQuerySet': self._ValuesQuerySet,
            '_ValuesListQuerySet': self._ValuesListQuerySet,
            '_DateQuerySet': self._DateQuerySet,
            '_DateTimeQuerySet': self._DateTimeQuerySet,
        }
        return qs._clone(**kwargs)
