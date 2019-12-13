# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

import pytz
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _, ugettext

from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.tariffs.models import EnergyTariff
from gridplatform.trackuser.managers import CustomerBoundManager
from gridplatform.utils import PhysicalQuantity
from gridplatform.utils.preferredunits import PhysicalUnitConverter


class PriceRelayProject(
        EncryptionCustomerFieldMixin, EncryptedModel):
    name = EncryptedCharField(_('name'), max_length=50)
    look_ahead = models.PositiveIntegerField(
        _('Look ahead'), help_text=_('in hours'))
    relay_one_on_at = models.FloatField(
        _('Relay one on at'), help_text=_('kr'))
    relay_two_on_at = models.FloatField(
        _('Relay two on at'), help_text=_('kr'))
    relay_tree_on_at = models.FloatField(
        _('Relay tree on at'), help_text=_('kr'))
    relay_four_on_at = models.FloatField(
        _('Relay four on at'), help_text=_('kr'))
    relay_five_on_at = models.FloatField(
        _('Relay five on at'), help_text=_('kr'))
    relay_six_on_at = models.FloatField(
        _('Relay six on at'), help_text=_('kr'))
    relay_seven_on_at = models.FloatField(
        _('Relay seven on at'), help_text=_('kr'))
    relay_eight_on_at = models.FloatField(
        _('Relay eight on at'), help_text=_('kr'))
    tariff = models.ForeignKey(
        EnergyTariff,
        verbose_name=_('tariff'))

    objects = CustomerBoundManager()

    class Meta:
        verbose_name = _('Price relay project')
        verbose_name_plural = _('Price relay projects')

    def __unicode__(self):
        return unicode(self.name_plain)

    def clean(self):
        """
        :raises ValidationError: if ``self.relay_one_at`` value is gte ``self.relay_two_at``
        :raises ValidationError: if ``self.relay_two_at`` value is gte ``self.relay_tree_at``
        :raises ValidationError: if ``self.relay_tree_at`` value is gte ``self.relay_four_at``
        :raises ValidationError: if ``self.relay_four_at`` value is gte ``self.relay_five_at``
        :raises ValidationError: if ``self.relay_five_at`` value is gte ``self.relay_six_at``
        :raises ValidationError: if ``self.relay_six_at`` value is gte ``self.relay_seven_at``
        :raises ValidationError: if ``self.relay_seven_at`` value is gte ``self.relay_eight_at``

        """
        super(PriceRelayProject, self).clean()

        if self.relay_one_on_at >= self.relay_two_on_at:
            raise ValidationError(
                {
                    'relay_one_on_at': [
                        ugettext(
                            'Value must be lesser than Relay two value at')]})

        if self.relay_two_on_at >= self.relay_tree_on_at:
            raise ValidationError(
                {
                    'relay_two_on_at': [
                        ugettext(
                            'Value must be lesser than Relay tree value at')]})

        if self.relay_tree_on_at >= self.relay_four_on_at:
            raise ValidationError(
                {
                    'relay_tree_on_at': [
                        ugettext(
                            'Value must be lesser than Relay four value at')]})

        if self.relay_four_on_at >= self.relay_five_on_at:
            raise ValidationError(
                {
                    'relay_four_on_at': [
                        ugettext(
                            'Value must be lesser than Relay five value at')]})

        if self.relay_five_on_at >= self.relay_six_on_at:
            raise ValidationError(
                {
                    'relay_five_on_at': [
                        ugettext(
                            'Value must be lesser than Relay six value at')]})

        if self.relay_six_on_at >= self.relay_seven_on_at:
            raise ValidationError(
                {
                    'relay_six_on_at': [
                        ugettext(
                            'Value must be lesser than Relay seven value at')]})

        if self.relay_seven_on_at >= self.relay_eight_on_at:
            raise ValidationError(
                {
                    'relay_seven_on_at': [
                        ugettext(
                            'Value must be lesser than Relay eight value at')]})

    def _get_relay_number(self, price):
        if price < self.relay_one_on_at:
            return 0
        if self.relay_one_on_at <= price < self.relay_two_on_at:
            return 1
        elif self.relay_two_on_at <= price < self.relay_tree_on_at:
            return 2
        elif self.relay_tree_on_at <= price < self.relay_four_on_at:
            return 3
        elif self.relay_four_on_at <= price < self.relay_five_on_at:
            return 4
        elif self.relay_five_on_at <= price < self.relay_six_on_at:
            return 5
        elif self.relay_six_on_at <= price < self.relay_seven_on_at:
            return 6
        elif self.relay_seven_on_at <= price < self.relay_eight_on_at:
            return 7
        elif self.relay_eight_on_at <= price:
            return 8

    def calculate_relay_settings(self):
        settings = []
        now = datetime.datetime.now().replace(tzinfo=self.customer.timezone) - datetime.timedelta(hours=2)

        prices = list(self.tariff.period_set.value_sequence(now, now + datetime.timedelta(hours=24)))
        #print prices
        unit_converter = PhysicalUnitConverter(self.tariff.unit)
        print self.tariff.unit, self.tariff.pk
        for i in range(0, len(prices)):
            sample = prices[i]
            look_ahead_sample = None
            try:
                look_ahead_sample = prices[i+self.look_ahead]
            except IndexError:
                pass
            if look_ahead_sample:
                change = PhysicalQuantity(100) - (sample.physical_quantity / look_ahead_sample.physical_quantity * 100)
                relay_number = self._get_relay_number(float(unit_converter.extract_value(
                    look_ahead_sample.physical_quantity)))

                # todo fix pris delta

                settings.append(
                    {'sample': sample, 'look_ahead_sample': look_ahead_sample, 'change': change, 'relay': relay_number})
        
	return settings
