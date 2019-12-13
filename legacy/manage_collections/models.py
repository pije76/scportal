# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit

from gridplatform.encryption.models import EncryptedModel
from gridplatform.encryption.fields import EncryptedTextField
from legacy.measurementpoints.models import Collection
from gridplatform.customers.models import Customer
from gridplatform.trackuser import get_customer
from gridplatform.utils.models import StoreSubclass
from gridplatform.trackuser.managers import CustomerBoundManager
from gridplatform.trackuser.managers import StoredSubclassCustomerBoundManager


class CollectionCustomerBoundManager(CustomerBoundManager):
    _field = 'collection__customer'


class Floorplan(models.Model):
    collection = models.OneToOneField(Collection)
    image = ProcessedImageField(
        upload_to='floorplans',
        blank=False,
        processors=[ResizeToFit(900, 900, upscale=False)],
        format='JPEG')

    objects = CollectionCustomerBoundManager()

    def save(self, *args, **kwargs):
        assert self.image
        super(Floorplan, self).save(*args, **kwargs)


class FloorplanCollectionStoredSubclassCustomerBoundManager(
        StoredSubclassCustomerBoundManager):
    _field = 'floorplan__collection__customer'


class AbstractItem(StoreSubclass):
    objects = FloorplanCollectionStoredSubclassCustomerBoundManager()

    class Meta:
        abstract = True


class Item(AbstractItem):
    floorplan = models.ForeignKey(Floorplan)
    x = models.IntegerField()
    y = models.IntegerField()
    z = models.IntegerField()

    def has_collection(self):
        return self.subclass_instance._has_collection()

    def _has_collection(self):
        raise NotImplementedError(self.__class__)


class CollectionItem(Item):
    collection = models.ForeignKey(Collection)

    def _has_collection(self):
        return True


class InfoItem(Item, EncryptedModel):
    info = EncryptedTextField()

    def _has_collection(self):
        return False

    def get_encryption_id(self):
        if self.id:
            return (
                Customer,
                self.floorplan.collection.customer_id)
        else:
            return (Customer, get_customer().id)
