# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import pytz

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.trackuser.managers import CustomerBoundManager
from gridplatform.consumptions.models import Consumption
from gridplatform.utils import DATETIME_MIN, PhysicalQuantity

PHASE_ONE = 1
PHASE_TWO = 2
PHASE_TREE = 3

ENERGY_PROJECT_PHASES = {
    PHASE_ONE: _('Phase 1'),
    PHASE_TWO: _('Phase 2'),
    PHASE_TREE: _('Phase 3'),
}


class EnergyProject(EncryptionCustomerFieldMixin, EncryptedModel):
    name = EncryptedCharField(_('name'), max_length=50)

    baseline_from_date = models.DateField(_('Baseline start date'))
    baseline_to_date = models.DateField(_('Baseline end date'))

    time_datasource = models.ForeignKey(
        Consumption,
        verbose_name=_('time datasource'),
        null=True, blank=True,
        related_name='energyproject_time_set'
    )

    datasource = models.ForeignKey(
        Consumption,
        verbose_name=_('datasource'),
        null=True, blank=True,
        related_name='energyproject_set'
    )

    result_from_date = models.DateField(_('Result start date'), blank=True, null=True)
    result_to_date = models.DateField(_('Result end date'), blank=True, null=True)

    objects = CustomerBoundManager()

    class Meta:
        verbose_name = _('Energy project')
        verbose_name_plural = _('Energy projects')

    def __unicode__(self):
        return unicode(self.name_plain)

    def clean(self):
        """
        :raise ValidationError: If baseline timestamp range is empty.
        """
        super(EnergyProject, self).clean()
        if self.baseline_from_date and self.baseline_to_date and \
                self.baseline_from_date > self.baseline_to_date:
            raise ValidationError(_('Baseline period must be non-empty.'))

        if self.datasource_id and not PhysicalQuantity.compatible_units(
                    self.datasource.unit, 'joule'):
            raise ValidationError(_('Datasource must be an energy datasource'))

        if self.time_datasource_id and not PhysicalQuantity.compatible_units(
                    self.time_datasource.unit, 'second'):
            raise ValidationError(_('Datasource must be a time datasource'))

    def project_phase(self):
        now = datetime.date.today()
        if now <= self.baseline_to_date:
            return PHASE_ONE
        elif now > self.baseline_to_date and now < self.result_from_date:
            return PHASE_TWO
        else:
            return PHASE_TREE

    def baseline_timestamps(self):
        return (
            datetime.datetime.combine(
                self.baseline_from_date,
                datetime.time(0, 0).replace(tzinfo=self.customer.timezone)),
            datetime.datetime.combine(
                self.baseline_to_date,
                datetime.time(23, 0).replace(tzinfo=self.customer.timezone))
        )

    def total_baseline_consumption(self):
        if not self.datasource:
            return None

        timestamps = self.baseline_timestamps()
        return self.datasource.energy_sum(timestamps[0], timestamps[1]).convert('kilowatt*hour')

    def total_baseline_time_consumption(self):
        if not self.time_datasource:
            return None

        timestamps = self.baseline_timestamps()
        return self.time_datasource.energy_sum(timestamps[0], timestamps[1]).convert('hour')


class LedLightProject(
        EncryptionCustomerFieldMixin, EncryptedModel):
    name = EncryptedCharField(_('name'), max_length=50)
    previous_tube_count = models.IntegerField(_('previous tube count'))
    previous_consumption_per_tube = models.IntegerField(
        _('previous consumption per tube in W/h'))

    led_tube_count = models.IntegerField(_('LED tube count'))
    led_consumption_per_tube = models.IntegerField(
        _('consumption per LED tube in W/h'))

    price = models.FloatField(_('price per kw/h'))

    datasource = models.ForeignKey(
        Consumption,
        verbose_name=_('datasource'),
        null=True, blank=True)

    objects = CustomerBoundManager()

    class Meta:
        verbose_name = _('LED light project')
        verbose_name_plural = _('LED light projects')

    def __unicode__(self):
        return unicode(self.name_plain)

    def calculate_previous_consumption(self):
        return self.previous_tube_count * self.previous_consumption_per_tube

    def measured_consumption(self, from_timestamp, to_timestamp):
        if not from_timestamp:
            from_timestamp = DATETIME_MIN
        if not to_timestamp:
            to_timestamp = datetime.datetime(
                9998, 12, 30, 23, 0, 0).replace(tzinfo=pytz.utc)

        return self.datasource.energy_sum(from_timestamp, to_timestamp)

    def calculate_previous_price_per_hour(self):
        return self.calculate_previous_consumption() / 1000.0 * self.price

    def calculate_savings(self, from_time=None, to_time=None):
        '''
            Returns the savings
        '''
        if not self.datasource:
            return None

        return self.calculated_previous_price(
            from_time, to_time) - self.measured_price(
            from_time, to_time)

    def calculate_burn_hours(self, from_time=None, to_time=None):
        if self.datasource:
            consumption = self.measured_consumption(
                from_time, to_time).convert('watt*hour')

            calculated_consumption = self.led_tube_count \
                * self.led_consumption_per_tube
            return consumption / calculated_consumption
        else:
            return None

    def calculated_previous_price(
            self, from_time=None, to_time=None):
        if self.datasource:
            return self.calculate_burn_hours(
                from_time, to_time) * self.calculate_previous_price_per_hour()
        else:
            return None

    def measured_price(self, from_time=None, to_time=None):
        if self.datasource:

            return self.measured_consumption(
                from_time, to_time).convert('kilowatt*hour') * self.price
        else:
            return None
