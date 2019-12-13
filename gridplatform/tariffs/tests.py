# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from decimal import Decimal

from django.test import TestCase
from django.test.utils import override_settings
from django.core.exceptions import ValidationError
import pytz

from gridplatform import trackuser
import gridplatform.customers.models
import gridplatform.global_datasources.models
import gridplatform.providers.models
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.customers.models import Customer
from gridplatform.providers.models import Provider
from gridplatform.utils import units
from gridplatform.utils.samples import Sample
from gridplatform.datasources.models import RawData

from . import forms
from .models import SubscriptionMixin
from .models import EnergyTariff
from .models import VolumeTariff
from .models import FixedPricePeriod
from .models import SpotPricePeriod


@override_settings(ENCRYPTION_TESTMODE=True)
class SpotPricePeriodFormTest(TestCase):
    def setUp(self):
        self.provider = gridplatform.providers.models.Provider.objects.create()
        self.customer = gridplatform.customers.models.Customer.objects.create(
            provider=self.provider,
            timezone='Europe/Copenhagen'
        )
        self.tariff = EnergyTariff.objects.create(
            customer=self.customer,
            name_plain='test tariff'
        )
        self.spotprice = gridplatform.global_datasources.models. \
            GlobalDataSource.objects.create(
                name='test spot price',
                app_label='nordpool',
                codename='test',
                country='DK',
                unit='currency_dkk*gigawatt^-1*hour^-1',
            )

    def test_creation(self):
        with trackuser.replace_selected_customer(self.customer):
            forms.SpotPricePeriodForm(tariff=self.tariff)

    def test_spot_price_choices(self):
        with trackuser.replace_selected_customer(self.customer):
            form = forms.SpotPricePeriodForm(tariff=self.tariff)
            spotpricechoices = list(form.fields['spotprice'].choices)
            self.assertTrue(
                any(value == self.spotprice.id
                    for value, display in spotpricechoices))


class SubscriptionMock(SubscriptionMixin):
    currency_unit = 'currency_dkk'


@override_settings(ENCRYPTION_TESTMODE=True)
class SubscriptionMixinTest(TestCase):
    def test_time_quantity_monthly(self):
        self.assertEqual(
            SubscriptionMixin.time_quantity(
                SubscriptionMixin.SUBSCRIPTION_PERIODS.monthly),
            PhysicalQuantity(1, 'month'))

    def test_time_quantity_quarterly(self):
        self.assertEqual(
            SubscriptionMixin.time_quantity(
                SubscriptionMixin.SUBSCRIPTION_PERIODS.quarterly),
            PhysicalQuantity(1, 'quarteryear'))

    def test_time_quantity_year(self):
        self.assertEqual(
            SubscriptionMixin.time_quantity(
                SubscriptionMixin.SUBSCRIPTION_PERIODS.yearly),
            PhysicalQuantity(1, 'year'))

    def test_subscription_cost_sum(self):
        timezone = pytz.timezone('Europe/Copenhagen')
        from_timestamp = timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = timezone.localize(datetime.datetime(2015, 1, 1))

        subscription = SubscriptionMock(
            subscription_fee=Decimal('1234.5678'),
            subscription_period=(
                SubscriptionMixin.SUBSCRIPTION_PERIODS.quarterly))

        self.assertEqual(
            PhysicalQuantity(4) *
            PhysicalQuantity('1234.5678', 'currency_dkk'),
            subscription._subscription_cost_sum(
                from_timestamp,
                to_timestamp))


@override_settings(ENCRYPTION_TESTMODE=True)
class EnergyTariffTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            currency_unit='currency_dkk')
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.tariff = EnergyTariff.objects.create(
            customer=self.customer)

    def test_unit(self):
        self.assertTrue(PhysicalQuantity.compatible_units(
            self.tariff.unit, 'currency_dkk*joule^-1'))
        self.assertIn(self.tariff.unit, units.UNIT_DISPLAY_NAMES)

    def test_subscription_cost_sum_no_periods(self):
        from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(
            datetime.datetime(2015, 1, 1))

        self.assertIsNone(
            self.tariff.period_set.subscription_cost_sum(
                from_timestamp, to_timestamp))

    def test_subscription_cost_sum(self):
        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2013, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 1)),
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=self.tariff,
            subscription_fee=100,
            subscription_period=SubscriptionMixin.SUBSCRIPTION_PERIODS.yearly)

        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=self.tariff,
            subscription_fee=42,
            subscription_period=SubscriptionMixin.SUBSCRIPTION_PERIODS.yearly)

        self.assertEqual(
            PhysicalQuantity(142, 'currency_dkk'),
            self.tariff.period_set.subscription_cost_sum(
                self.timezone.localize(datetime.datetime(2012, 1, 1)),
                self.timezone.localize(datetime.datetime(2015, 1, 1))))


@override_settings(ENCRYPTION_TESTMODE=True)
class VolumeTariffTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            currency_unit='currency_eur')
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.tariff = VolumeTariff.objects.create(
            customer=self.customer)

    def test_unit(self):
        self.assertTrue(PhysicalQuantity.compatible_units(
            self.tariff.unit, 'currency_eur*meter^-3'))
        self.assertIn(self.tariff.unit, units.UNIT_DISPLAY_NAMES)

    def test_subscription_cost_sum_no_periods(self):
        from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(
            datetime.datetime(2015, 1, 1))

        self.assertIsNone(
            self.tariff.period_set.subscription_cost_sum(
                from_timestamp, to_timestamp))

    def test_subscription_cost_sum(self):
        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2013, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 1)),
            value=10,
            unit='currency_eur*meter^-3',
            datasequence=self.tariff,
            subscription_fee=100,
            subscription_period=SubscriptionMixin.SUBSCRIPTION_PERIODS.yearly)

        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            value=10,
            unit='currency_eur*meter^-3',
            datasequence=self.tariff,
            subscription_fee=42,
            subscription_period=SubscriptionMixin.SUBSCRIPTION_PERIODS.yearly)

        self.assertEqual(
            PhysicalQuantity(142, 'currency_eur'),
            self.tariff.period_set.subscription_cost_sum(
                self.timezone.localize(datetime.datetime(2012, 1, 1)),
                self.timezone.localize(datetime.datetime(2015, 1, 1))))


@override_settings(ENCRYPTION_TESTMODE=True)
class SpotPricePeriodTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')

        self.tariff = EnergyTariff.objects.create(
            customer=self.customer)

        self.spotprice = gridplatform.global_datasources.models. \
            GlobalDataSource.objects.create(
                name='test spot price',
                app_label='nordpool',
                codename='test',
                country='DK',
                unit='currency_dkk*gigawatt^-1*hour^-1',
            )

    def test_clean_good_units(self):
        period = SpotPricePeriod(
            datasequence=self.tariff,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2015, 1, 1)),
            spotprice=self.spotprice,
            coefficient='123.456',
            unit_for_constant_and_ceiling='currency_dkk*kilowatt^-1*hour^-1',
            constant='123.456',
            ceiling='123.456')
        period.clean()

    def test_clean_bad_tariff_unit(self):
        self.tariff.unit = 'currency_dkk*meter^-3'
        self.tariff.save()
        period = SpotPricePeriod(
            datasequence=self.tariff,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2015, 1, 1)),
            spotprice=self.spotprice,
            coefficient='123.456',
            unit_for_constant_and_ceiling='currency_dkk*kilowatt^-1*hour^-1',
            constant='123.456',
            ceiling='123.456')
        with self.assertRaises(ValidationError):
            period.clean()

    def test_clean_bad_spot_unit(self):
        self.spotprice.unit = 'currency_dkk*meter^-3'
        self.spotprice.save()
        period = SpotPricePeriod(
            datasequence=self.tariff,
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2015, 1, 1)),
            spotprice=self.spotprice,
            coefficient='123.456',
            unit_for_constant_and_ceiling='currency_dkk*kilowatt^-1*hour^-1',
            constant='123.456',
            ceiling='123.456')
        with self.assertRaises(ValidationError):
            period.clean()

    def test_value_sequence_with_ceiling(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        SpotPricePeriod.objects.create(
            datasequence=self.tariff,
            from_timestamp=from_timestamp,
            to_timestamp=self.timezone.localize(datetime.datetime(2015, 1, 1)),
            spotprice=self.spotprice,
            subscription_fee=500,
            subscription_period=SpotPricePeriod.SUBSCRIPTION_PERIODS.yearly,
            coefficient=2,
            unit_for_constant_and_ceiling='currency_dkk*kilowatt^-1*hour^-1',
            constant=3,
            ceiling=7)

        self.spotprice.rawdata_set.bulk_create(
            [
                RawData(
                    datasource=self.spotprice,
                    timestamp=from_timestamp + datetime.timedelta(
                        hours=h),
                    value=1000000 * (h % 10))
                for h in range(12)])

        self.assertEqual(
            [
                Sample(
                    from_timestamp + datetime.timedelta(hours=h),
                    from_timestamp + datetime.timedelta(hours=h + 1),
                    PhysicalQuantity(
                        min(2 * (h % 10) + 3, 7),
                        'currency_dkk*kilowatt^-1*hour^-1',),
                    False, False)
                for h in range(12)
            ],
            list(
                self.tariff.period_set.value_sequence(
                    from_timestamp,
                    from_timestamp + datetime.timedelta(days=1))))

    def test_value_sequence_without_ceiling(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        SpotPricePeriod.objects.create(
            datasequence=self.tariff,
            from_timestamp=from_timestamp,
            to_timestamp=self.timezone.localize(datetime.datetime(2015, 1, 1)),
            spotprice=self.spotprice,
            subscription_fee=500,
            subscription_period=SpotPricePeriod.SUBSCRIPTION_PERIODS.yearly,
            coefficient=2,
            unit_for_constant_and_ceiling='currency_dkk*kilowatt^-1*hour^-1',
            constant=3)

        self.spotprice.rawdata_set.bulk_create(
            [
                RawData(
                    datasource=self.spotprice,
                    timestamp=from_timestamp + datetime.timedelta(
                        hours=h),
                    value=1000000 * (h % 10))
                for h in range(12)])

        self.assertEqual(
            [
                Sample(
                    from_timestamp + datetime.timedelta(hours=h),
                    from_timestamp + datetime.timedelta(hours=h + 1),
                    PhysicalQuantity(
                        2 * (h % 10) + 3,
                        'currency_dkk*kilowatt^-1*hour^-1',),
                    False, False)
                for h in range(12)
            ],
            list(
                self.tariff.period_set.value_sequence(
                    from_timestamp,
                    from_timestamp + datetime.timedelta(days=1))))
