# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.customers.models import Customer
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.fields import EncryptedTextField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.trackuser.managers import CustomerBoundManager


class Report(EncryptedModel):
    """
    Model for storing generated documents.

    :cvar DATA_FORMAT_CHOICES:  Data format choices (PDF or CSV).

    :ivar customer: A foreign key to the :class:`.Customer` for which
        this document is generated.
    :ivar title:
    :ivar generation_time: The generation time
    :ivar data_format: The data format of the generated document.  One
        of the choices in ``self.DATA_FORMAT_CHOICES``.
    :ivar data: The encrypted contents of the document.
    """
    PDF = 1
    CSV = 2

    DATA_FORMAT_CHOICES = (
        (PDF, 'application/pdf'),
        (CSV, 'text/csv'),
    )

    customer = models.ForeignKey(Customer, null=True, on_delete=models.PROTECT)
    title = EncryptedCharField(max_length=50)
    generation_time = models.DateTimeField()
    data_format = models.PositiveIntegerField(choices=DATA_FORMAT_CHOICES)
    data = EncryptedTextField()
    size = models.PositiveIntegerField()

    objects = CustomerBoundManager()

    class Meta:
        verbose_name = _('report')
        verbose_name_plural = _('reports')
        ordering = ['generation_time', 'data_format', 'id']

    def __unicode__(self):
        return unicode(self.title_plain)

    def get_encryption_id(self):
        return (Customer, self.customer_id)
