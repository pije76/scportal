# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.db import models

from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from gridplatform.datasources.models import DataSource
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.trackuser.managers import StoredSubclassCustomerBoundManager


# NOTE: only managers defined on abstract base classes are inherited.  So this
# is a trick to make sure all CustomerDataSource specializations by default
# will have StoredSubclassCustomerBoundManager as their objects.
class CustomerDataSourceManagerMixin(models.Model):
    objects = StoredSubclassCustomerBoundManager()

    class Meta:
        abstract = True


class CustomerDataSource(
        CustomerDataSourceManagerMixin, EncryptionCustomerFieldMixin,
        EncryptedModel, DataSource):
    """
    Specialization of :class:`~gridplatform.datasources.models.DataSource` that
    is owned by :class:`~gridplatform.providers.models.Customer`.

    :ivar customer: The owning
        :class:`~gridplatform.customers.models.Customer`.
    :ivar name: The name.

    :cvar objects: The manager of :class:`.CustomerDataSource` is a
        :class:`.StoredSubclassCustomerBoundManager`.  Care has been taken to
        make sure that subclasses inherit this manager.
    """

    name = EncryptedCharField(_('name'), max_length=50, blank=False)

    class Meta:
        verbose_name = _('customer data source')
        verbose_name_plural = _('customer data sources')

    def __unicode__(self):
        return self.name_plain or self.hardware_id
