# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.trackuser.managers import CustomerBoundManager

from legacy.devices.models import Meter, PhysicalInput


class DatahubConnection(EncryptionCustomerFieldMixin, EncryptedModel):
    meter = models.ForeignKey(Meter, verbose_name=_('Meter'), on_delete=models.PROTECT)
    input = models.ForeignKey(PhysicalInput, editable=False,
                              on_delete=models.PROTECT)

    customer_meter_number = models.CharField(
        _('Meter Number'), max_length=50)
    authorization_id = models.CharField(
        _('authorization_id'), max_length=10, blank=True, null=True)

    start_date = models.DateField(_('Start date'), blank=True, null=True)
    end_date = models.DateField(_('End date'), blank=True, null=True)

    unit = models.CharField(
        _('Unit'), max_length=50, blank=True)

    objects = CustomerBoundManager()

    class Meta:
        verbose_name = _('Datahub connection')
        verbose_name_plural = _('Datahub connections')

    def __unicode__(self):
        return unicode(self.customer_meter_number)
