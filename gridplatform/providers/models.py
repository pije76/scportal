# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit

from django.db import models
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from gridplatform.customers.models import Customer
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.encryption.models import EncryptionKey
from gridplatform.encryption.signals import encryption_key_created
from gridplatform.users.models import User


class Provider(EncryptedModel):
    """
    Providers are entities facilitating the energy management system towards
    :class:`~gridplatform.customers.models.Customer`.

    :ivar name:
    :ivar address:
    :ivar zipcode: Zip code.
    :ivar city:
    :ivar cvr: VAT number (CVR is the Danish acronym that correspond to VAT).
    :ivar logo: An image containing the logo of the provider.

    :ivar thumbnail: File path to a 100x50 thumbnail of the logo.
    :ivar pdf_logo: File path to a 200x100 version of the logo suitable for
        inclusion in PDF-documents.
    """
    name = EncryptedCharField(_('name'), max_length=50)
    address = EncryptedCharField(_('address'), max_length=100)
    zipcode = EncryptedCharField(_('zipcode'), max_length=100)
    city = EncryptedCharField(_('city'), max_length=100)
    cvr = EncryptedCharField(_('cvr'), max_length=100)
    logo = models.ImageField(
        _('logo'), upload_to='logos', blank=True, null=True)

    class Meta:
        permissions = (
            ('provider_admin_group',
             _('Group can be used by providers')),
        )

    thumbnail = ImageSpecField(
        source='logo',
        processors=[ResizeToFit(100, 50)],
        format='JPEG',
        options={'quality': 90}
    )

    pdf_logo = ImageSpecField(
        source='logo',
        processors=[ResizeToFit(200, 100)],
        format='JPEG',
        options={'quality': 90}
    )

    def __unicode__(self):
        return self.name_plain

    def get_encryption_id(self):
        """
        Implementation of abstract method declared by
        :class:`gridplatform.encryption.models.EncryptedModel`.
        """
        return (Provider, self.id)

    def save(self, *args, **kwargs):
        """
        Implements necessary work-arounds for the encryption keys not being
        available upon initial save.
        """
        if not self.id:
            if self.name is None:
                # Save an instance without encrypted fields to generate the
                # encryption key
                tmp_provider = Provider()
                tmp_provider.name = ''
                tmp_provider.save()
                self.id = tmp_provider.id
                kwargs['force_update'] = True
                kwargs['force_insert'] = False
                super(Provider, self).save(*args, **kwargs)
            else:
                # Save without an existing encryption key only if there are
                # no encrypted fields.
                super(Provider, self).save(*args, **kwargs)
                # Then generate the key.
                EncryptionKey.generate((Provider, self.id))
            assert self.id
        else:
            super(Provider, self).save(*args, **kwargs)


@receiver(encryption_key_created, sender=User)
def auto_grant_provider_user_key(sender, key, key_id, **kwargs):
    """
    Whenever a customer user is created,an encryption key is created for him as
    well.  This signal handler grants that key to all provider users of the
    provider of the customer of the given user.
    """
    model_class, object_id = key_id
    assert sender is model_class
    key_user = model_class._all_users.get(id=object_id)
    if not key_user.customer:
        return
    provider_id = key_user.customer.provider_id
    provider_users = User._all_users.filter(
        provider_id=provider_id, customer__isnull=True)
    for provider_user in provider_users:
        provider_user.grant_key(key_id, key)


@receiver(encryption_key_created, sender=Customer)
def auto_grant_provider_customer_key(sender, key, key_id, **kwargs):
    """
    Whenever a customer is created, an encryption key is created for it as
    well.  This signal handler grants that key to all provider users of the
    provider of the given customer.
    """
    model_class, object_id = key_id
    assert sender is model_class
    key_customer = model_class.objects.get(id=object_id)
    provider_id = key_customer.provider_id
    provider_users = User._all_users.filter(
        provider_id=provider_id, customer__isnull=True)
    for provider_user in provider_users:
        provider_user.grant_key(key_id, key)
