# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.db import models

from gridplatform.trackuser import get_customer

from .models import Customer


class EncryptionCustomerFieldMixin(models.Model):
    customer = models.ForeignKey(
        Customer, editable=False, verbose_name=_('customer'),
        default=get_customer)

    class Meta:
        abstract = True

    def get_encryption_id(self):
        return (Customer, self.customer_id)
