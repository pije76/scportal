# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext

from gridplatform.trackuser import get_customer
from gridplatform.utils import units
from gridplatform.utils.forms import HalfOpenTimePeriodModelForm
from gridplatform.utils.unitconversion import PhysicalQuantity

from . import models


class SubscriptionFeeFormLabelMixin(object):
    """
    Include customers currency in label of subscription fee field.
    """

    def __init__(self, *args, **kwargs):
        super(SubscriptionFeeFormLabelMixin, self).__init__(*args, **kwargs)
        self.fields['subscription_fee'].label = \
            ugettext('subscription fee ({currency})').format(
                currency=get_customer().get_currency_unit_display())


class FixedPricePeriodForm(
        SubscriptionFeeFormLabelMixin, HalfOpenTimePeriodModelForm):
    class Meta:
        model = models.FixedPricePeriod
        fields = (
            'value', 'unit', 'subscription_fee', 'subscription_period')
        localized_fields = ('subscription_fee',)


class SpotPricePeriodForm(
        SubscriptionFeeFormLabelMixin, HalfOpenTimePeriodModelForm):
    class Meta:
        model = models.SpotPricePeriod
        fields = (
            'subscription_fee', 'subscription_period', 'spotprice',
            'coefficient', 'unit_for_constant_and_ceiling',
            'constant', 'ceiling')
        localized_fields = (
            'subscription_fee', 'coefficient', 'constant', 'ceiling')

    def __init__(self, *args, **kwargs):
        # If a tariff is given to the constructor then the spot prices choices
        # are updated accordingly.

        tariff = kwargs.pop('tariff', None)
        super(SpotPricePeriodForm, self).__init__(*args, **kwargs)
        if tariff:
            compatible_spotprice_units = [
                unit for unit in units.TARIFF_BASE_UNITS
                if PhysicalQuantity.compatible_units(unit, tariff.unit)
            ]

            self.fields['spotprice'].queryset = \
                self.fields['spotprice'].queryset.filter(
                    unit__in=compatible_spotprice_units)

            compatible_tariff_choices = [
                (unit, label) for unit, label in units.TARIFF_CHOICES
                if PhysicalQuantity.compatible_units(unit, tariff.unit)
            ]
            self.fields['unit_for_constant_and_ceiling'] = \
                forms.ChoiceField(choices=compatible_tariff_choices)
