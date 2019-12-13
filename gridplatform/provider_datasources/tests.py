# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from gridplatform.providers.models import Provider
from gridplatform.customers.models import Customer
from gridplatform.trackuser import replace_customer
from gridplatform.trackuser import replace_user
from gridplatform.datasources.models import DataSource
from gridplatform.users.models import User

from .models import ProviderDataSource


@override_settings(ENCRYPTION_TESTMODE=True)
class ProviderDataSourceTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.datasource = ProviderDataSource.objects.create(
            provider=self.provider,
            unit='currency_eur*gigawatt^-1*hour^-1',
            hardware_id='provider tariff',
        )

    def test_unicode(self):
        unicode(self.datasource)


@override_settings(ENCRYPTION_TESTMODE=True)
class DataSourceManagerProviderTest(TestCase):
    def setUp(self):
        self.provider1 = Provider.objects.create()
        self.provider2 = Provider.objects.create()

        self.customer1 = Customer.objects.create(
            provider=self.provider1)
        self.customer2 = Customer.objects.create(
            provider=self.provider2)

        self.datasource = ProviderDataSource.objects.create(
            provider=self.provider1)

        self.user = User()
        self.user.is_authenticated = lambda: True

    def test_customer_can_see_own_providers_datasources(self):
        with replace_user(self.user), replace_customer(self.customer1):
            self.assertTrue(
                DataSource.objects.filter(
                    id=self.datasource.id).exists())

    def test_customer_cannot_see_other_providers_datasources(self):
        with replace_user(self.user), replace_customer(self.customer2):
            self.assertFalse(
                DataSource.objects.filter(
                    id=self.datasource.id).exists())

    def test_provider_can_see_own_datasources(self):
        self.user.provider = self.provider1
        with replace_user(self.user):
            self.assertTrue(
                DataSource.objects.filter(
                    id=self.datasource.id).exists())

    def test_provider_cannot_see_other_datasources(self):
        self.user.provider = self.provider2
        with replace_user(self.user):
            self.assertFalse(
                DataSource.objects.filter(
                    id=self.datasource.id).exists())


@override_settings(ENCRYPTION_TESTMODE=True)
class ProviderDataSourceManagerTest(TestCase):
    def setUp(self):
        self.provider1 = Provider.objects.create()
        self.provider2 = Provider.objects.create()

        self.customer1 = Customer.objects.create(
            provider=self.provider1)
        self.customer2 = Customer.objects.create(
            provider=self.provider2)

        self.datasource = ProviderDataSource.objects.create(
            provider=self.provider1)

        self.user = User()
        self.user.is_authenticated = lambda: True

    def test_customer_can_see_own_providers_datasources(self):
        with replace_user(self.user), replace_customer(self.customer1):
            self.assertTrue(
                ProviderDataSource.objects.filter(
                    id=self.datasource.id).exists())

    def test_customer_cannot_see_other_providers_datasources(self):
        with replace_user(self.user), replace_customer(self.customer2):
            self.assertFalse(
                ProviderDataSource.objects.filter(
                    id=self.datasource.id).exists())

    def test_provider_can_see_own_datasources(self):
        self.user.provider = self.provider1
        with replace_user(self.user):
            self.assertTrue(
                ProviderDataSource.objects.filter(
                    id=self.datasource.id).exists())

    def test_provider_cannot_see_other_datasources(self):
        self.user.provider = self.provider2
        with replace_user(self.user):
            self.assertFalse(
                ProviderDataSource.objects.filter(
                    id=self.datasource.id).exists())
