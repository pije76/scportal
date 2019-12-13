# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import pytz

from django.test import TestCase
from django.test.utils import override_settings

from gridplatform.customers.models import Customer
from gridplatform.providers.models import Provider
from gridplatform.trackuser import replace_customer
from gridplatform.trackuser import replace_user
from gridplatform.users.models import User
from gridplatform.customer_datasources.models import CustomerDataSource
from gridplatform.datasources.models import RawData

from .models import LedLightProject


@override_settings(ENCRYPTION_TESTMODE=True)
class LedLightProjectTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.user = User(provider=self.provider)
        self.customer = Customer(provider=self.provider)
        self.customer.save()

    def test_save_and_load(self):
        with replace_user(self.user), replace_customer(self.customer):
            project = LedLightProject.objects.create(
                name_plain='Office',
                previous_tube_count=32,
                previous_consumption_per_tube=45,
                led_tube_count=30,
                led_consumption_per_tube=20,
                price=2.4
            )

            loaded_project = LedLightProject.objects.get(
                id=project.id)

            self.assertEqual(
                project.name_plain,
                loaded_project.name_plain)

    def test_measured_price_without_datasource(self):
        with replace_user(self.user), replace_customer(self.customer):
            project = LedLightProject.objects.create(
                name_plain='Office',
                previous_tube_count=32,
                previous_consumption_per_tube=45,
                led_tube_count=30,
                led_consumption_per_tube=20,
                price=2.4
            )

            self.assertEqual(
                project.measured_price(),
                None)

    def test_measured_price_with_datasource_without_data(self):
        with replace_user(self.user), replace_customer(self.customer):
            data_source = CustomerDataSource.objects.create(
                name_plain='test name',
                unit='watt*hour')

            project = LedLightProject.objects.create(
                name_plain='Office',
                previous_tube_count=32,
                previous_consumption_per_tube=45,
                led_tube_count=30,
                led_consumption_per_tube=20,
                price=2.4,
                datasource=data_source
            )

            self.assertEqual(
                project.measured_price(),
                0)

    def test_measured_price(self):
        with replace_user(self.user), replace_customer(self.customer):
            data_source = CustomerDataSource.objects.create(
                name_plain='test name',
                unit='watt')

            project = LedLightProject.objects.create(
                name_plain='Office',
                previous_tube_count=32,
                previous_consumption_per_tube=45,
                led_tube_count=30,
                led_consumption_per_tube=20,
                price=2.4,
                datasource=data_source
            )

            timestamp = datetime.datetime(
                2015, 6, 2, 10, 0, 0, tzinfo=pytz.timezone('UTC'))
            startvalue = 0
            for x in xrange(1, 120):
                RawData.objects.create(
                    datasource=data_source,
                    value=10,
                    unit='milwatt*',
                    timestamp=timestamp
                )
                startvalue += 10
                timestamp += datetime.timedelta(minutes=1)

            self.assertEqual(
                project.measured_price(),
                1.44)

    def test_calculated_previous_price(self):
        with replace_user(self.user), replace_customer(self.customer):
            data_source = CustomerDataSource.objects.create(
                name_plain='test name',
                unit='watt*hour')

            project = LedLightProject.objects.create(
                name_plain='Office',
                previous_tube_count=32,
                previous_consumption_per_tube=45,
                led_tube_count=30,
                led_consumption_per_tube=20,
                price=2.4,
                datasource=data_source
            )

            timestamp = datetime.datetime(
                2015, 6, 2, 10, 0, 0, tzinfo=pytz.timezone('UTC'))
            startvalue = 0
            for x in xrange(1, 120):
                RawData.objects.create(
                    datasource=data_source,
                    value=startvalue,
                    unit='milwatt*hour',
                    timestamp=timestamp
                )
                startvalue += 10
                timestamp += datetime.timedelta(minutes=1)

            self.assertEqual(
                project.calculated_previous_price(),
                3.456)

    def test_calculate_savings(self):
        with replace_user(self.user), replace_customer(self.customer):
            data_source = CustomerDataSource.objects.create(
                name_plain='test name',
                unit='watt*hour')

            project = LedLightProject.objects.create(
                name_plain='Office',
                previous_tube_count=32,
                previous_consumption_per_tube=45,
                led_tube_count=30,
                led_consumption_per_tube=20,
                price=2.4,
                datasource=data_source
            )

            timestamp = datetime.datetime(
                2015, 6, 2, 10, 0, 0, tzinfo=pytz.timezone('UTC'))
            startvalue = 0
            for x in xrange(1, 120):
                RawData.objects.create(
                    datasource=data_source,
                    value=startvalue,
                    unit='milwatt*hour',
                    timestamp=timestamp
                )
                startvalue += 10
                timestamp += datetime.timedelta(minutes=1)

            self.assertEqual(
                project.calculate_savings(),
                2.016)
