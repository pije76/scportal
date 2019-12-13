# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import warnings

from django.contrib.auth import hashers
from django.contrib.auth.models import User as DjangoUser
from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save

from gridplatform.customers.models import Customer
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.fields import EncryptedEmailField
from gridplatform.encryption.fields import EncryptedField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.encryption.models import EncryptionKey
from gridplatform.encryption.models import EncryptionUser
from gridplatform.encryption.signals import encryption_key_created
from gridplatform.encryption.signals import encryption_user_created
from gridplatform.trackuser import get_user

from .managers import BoundUserManager
from .managers import UserManager
from .managers import hash_username


class User(DjangoUser, EncryptionUser, EncryptedModel):
    """
    GridPlatform user.  Includes encrypted replacement fields for several of
    Djangos built-in User fields.

    :ivar user_type:  One of :py:attr:`USER_TYPE_CHOICES`.
    :ivar e_mail:  Email.
    :ivar phone:
    :ivar mobile: cell phone
    :ivar name:
    :ivar customer: A foreign key to
        :py:class:`gridplatform.customers.models.Customer`.  If set this user
        belongs to this customer.  This field may not be updated.  If
        ``self.provider`` is set, this field must be ``None``.
    :ivar provider: A foreign key to
        :py:class:`gridplatform.providers.models.Provider`.  If set this user
        belongs to this provider.  This field may not be updated.  If
        ``self.customer`` is set, this field must be ``None``.
    """
    ADMIN = 1
    CUSTOMER_SUPERUSER = 2
    CUSTOMER_USER = 3
    API_USER = 4
    USER_TYPE_CHOICES = (
        (ADMIN, _('Admin')),
        (CUSTOMER_SUPERUSER, _('Super User')),
        (CUSTOMER_USER, _('User')),
        (API_USER, _('Api User')),
    )
    user_type = models.IntegerField(
        choices=USER_TYPE_CHOICES, blank=True, null=True)

    # normal email property of Django User not encrypted
    e_mail = EncryptedEmailField(_('e-mail address'))
    phone = EncryptedCharField(_('phone'), max_length=20)
    mobile = EncryptedCharField(_('mobile'), max_length=20, blank=True)
    # normal first_name/last_name of Django User not encrypted
    name = EncryptedCharField(_('name'), max_length=60)

    customer = models.ForeignKey(
        'customers.Customer', verbose_name=_('customer'),
        blank=True, null=True, editable=False)
    provider = models.ForeignKey(
        'providers.Provider', verbose_name=_('provider'),
        blank=True, null=True, editable=False)

    objects = BoundUserManager()
    _all_users = UserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['user_type', 'name', 'id']
        permissions = (
            ('access_provider_site',
             _('Can access the provider site')),
            ('access_led_light_site',
             _('Can access the led light site')),
            ('access_led_light_site_dashboard',
             _('Can access the led light site dashboard')),
            ('access_led_light_site_projects',
             _('Can access the led light site projects')),
            ('access_project_site',
             _('Can access the ESCo Lite site')),
            ('access_price_relay_site',
             _('Can access the Price Relay site')),
            ('access_datahub_site',
             _('Can access the Datahub site')),
        )

    def __unicode__(self):
        return unicode(self.name_plain or self.name)

    def clean_fields(self, exclude=None):
        """
        :raise ValidationError: if ``self.is_staff`` and ``self.customer`` or
            ``self.provider`` is set.
        :raise ValidationError: If both ``self.customer`` and ``self.provider``
            are set, or both are not set.
        """
        if self.is_staff and (self.customer or self.provider):
            raise ValidationError('Staff users can neither be bound to '
                                  'customer nor provider')
        elif (not exclude or ('customer' not in exclude and
                              'provider' not in exclude)):
            # unreachable code, as bot customer and provider are not editable.
            if bool(self.customer) == bool(self.provider):
                raise ValidationError('Provider or customer must be set and '
                                      'both cannot be set at the same time')
        super(User, self).clean_fields(exclude=exclude)

    def save(self, *args, **kwargs):
        """
        Derives hashed ``self.username`` from unencrypted email field.

        Implements necessary work-arounds for encryption key needed for
        initially encrypting this instance does not exist before the instance
        has been saved.
        """
        assert not self.customer_id or not self.provider_id, \
            'User cannot be bound to both customer and provider'
        if not self.username:
            self.username = hash_username(self.e_mail_plain)

        if not self.id:
            encrypted_field_names = [
                field.name
                for field in self._meta.fields
                if isinstance(field, EncryptedField)
            ]
            if any(getattr(self, '{}_plain'.format(name))
                   for name in encrypted_field_names):
                tmp_user = User(
                    username=self.username,
                    encryption_public_key=self.encryption_public_key,
                    customer_id=self.customer_id,
                    provider_id=self.provider_id,
                )
                tmp_user.save(force_insert=True, force_update=False)
                self.id = tmp_user.id
                opts = kwargs.copy()
                opts.update({'force_insert': False, 'force_update': True})
                super(User, self).save(*args, **kwargs)
                encryption_user_created.send(sender=User, user=self)
                return
        super(User, self).save(*args, **kwargs)

    def _decrypt(self, encryption_context):
        key_id = self.get_encryption_id()
        if key_id not in encryption_context.keys:
            return
        super(User, self)._decrypt(encryption_context)

    def get_username(self):
        """
        The username is the decrypted email.
        """
        return self.e_mail_plain

    def set_password(self, raw_password, old_password=None):
        """
        Updates private keys upon password change.
        """
        if not raw_password:
            raise ValueError('The given password must be set')
        if self.encryption_private_key:
            if not old_password:
                # On Django 1.5 -> 1.6 upgrade, the default password hashing
                # algorithm was changed.
                # ... when that happens, users passwords are "set" to the
                # current entered password on a successful login, in order to
                # have it stored with the updated hash...
                warnings.warn(
                    'old password not provided; will not update encryption')
            else:
                if not self.check_password(old_password):
                    raise ValueError('Incorrect old password')
                self.update_private_key(old_password, raw_password)
            self.password = hashers.make_password(raw_password)
        else:
            self.password = hashers.make_password(raw_password)
            self.generate_private_key(raw_password)

    def reset_password(self, request, raw_password):
        """
        To be run by admin/other with permission to access/share relevant keys.

        User will need a new private key.  (The private key can't be preserved
        unless old_password is provided; set_password will report an error if
        we try.)
        """
        self.encryption_private_key = bytearray()
        self.set_password(raw_password)
        # Remove and re-grant all currently known keys.

        old_keys = set([key.key_id() for key in self.encryptionkey_set.all()])
        EncryptionKey.objects.filter(user=self).delete()
        for key in old_keys:
            EncryptionKey.share(key, self)

    @property
    def is_admin(self):
        """
        for easier checks in template code
        """
        return self.user_type == self.ADMIN

    @property
    def is_customer_superuser(self):
        """
        for easier checks in template code
        """
        return self.user_type == self.CUSTOMER_SUPERUSER

    def get_encryption_id(self):
        """
        Implementation of abstract method declared by
        :class:`gridplatform.encryption.models.EncryptedModel`.
        """
        return (User, self.id)

    def satisfies_search(self, search):
        """
        Implementation of interface required by
        :py:func:`gridplatform.utils.views.json_list_response` view function
        decorator.

        :param search:  A string to search for.

        :return: True if the ``search`` argument is found in any relevant
            property of this customer.
        """
        elems = [
            self.name_plain,
            self.e_mail_plain
        ]
        search = search.lower()
        return any([search in unicode(elem).lower() for elem in elems])


@receiver(post_save, sender=User)
def create_user_key(sender, instance, created, raw, **kwargs):
    """
    Signal handler generating encryption keys for freshly created users.
    """
    if raw:
        return
    if created:
        EncryptionKey.generate((sender, instance.id))


@receiver(encryption_key_created)
def auto_grant_to_admins(sender, key, key_id, **kwargs):
    """
    Signal handler granting any created encryption keys to admin users.
    """
    admins = User._all_users.filter(user_type=User.ADMIN)
    user = get_user()
    for admin in admins:
        # already shared to current user, so avoid repeating it...
        if admin != user:
            admin.grant_key(key_id, key)


@receiver(encryption_key_created, sender=User)
def auto_grant_user_self_key(sender, key, key_id, **kwargs):
    """
    Signal handler granting key with user identifier to that user.
    """
    model_class, object_id = key_id
    assert sender is model_class
    user = model_class._all_users.get(id=object_id)
    user.grant_key(key_id, key)


@receiver(encryption_key_created, sender=User)
def auto_grant_user_key_to_superusers(sender, key, key_id, **kwargs):
    """
    If key created for user on customer, find all the superuser for that
    customer and shares the key to them.
    """
    model_class, object_id = key_id
    assert sender is model_class
    user = model_class._all_users.get(id=object_id)
    if user.customer:
        customer = user.customer
        superusers = customer.user_set.filter(
            user_type=User.CUSTOMER_SUPERUSER)
        for superuser in superusers:
            superuser.grant_key(key_id, key)


@receiver(encryption_user_created)
def auto_grant_customer_key(sender, user, **kwargs):
    """
    Provide key from customer that user is associated with.
    """
    if user.customer_id:
        key_id = (Customer, user.customer_id)
        EncryptionKey.share(key_id, user)


@receiver(encryption_user_created)
def auto_grant_customer_superuser_user_keys(sender, user, **kwargs):
    """
    If the new user is a superuser, then give access to keys for user
    information for users on same customer.
    """
    if user.customer and user.user_type == User.CUSTOMER_SUPERUSER:
        customer = user.customer
        users = customer.user_set.all()
        for otheruser in users:
            EncryptionKey.share((User, otheruser.id), user)


@receiver(encryption_user_created)
def auto_grant_provideruser_provider_key(sender, user, **kwargs):
    """
    Signal handler granting new provider users the encryption key for the same
    provider.
    """
    from gridplatform.providers.models import Provider
    if user.provider:
        assert not user.customer
        EncryptionKey.share((Provider, user.provider_id), user)


@receiver(encryption_user_created)
def auto_grant_provideruser_customer_keys(sender, user, **kwargs):
    """
    Signal handler granting new provider users the encryption keys for all
    customers of the same provider.
    """
    if user.provider:
        assert not user.customer
        for customer in user.provider.customer_set.all():
            EncryptionKey.share((Customer, customer.id), user)


@receiver(encryption_user_created)
def auto_grant_provideruser_customeruser_keys(sender, user, **kwargs):
    """
    Signal handler granting new provider users the encryption key for each user
    of all customers of the same provider.
    """
    if user.provider:
        assert not user.customer
        for customeruser in User._all_users.filter(
                customer__provider_id=user.provider_id):
            EncryptionKey.share((User, customeruser.id), user)


@receiver(encryption_user_created)
def auto_grant_provideruser_provideruser_keys(sender, user, **kwargs):
    """
    Signal handler granting new provider users the encryption key for each user
    of the same provider.
    """
    if user.provider:
        assert not user.customer
        for provideruser in User._all_users.filter(
                provider_id=user.provider_id):
            EncryptionKey.share((User, provideruser.id), user)
