# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from gridplatform.customers.models import Customer
from gridplatform.providers.models import Provider
from gridplatform.customer_datasources.models import CustomerDataSource
from gridplatform.trackuser import replace_customer
from gridplatform.trackuser import replace_user
from gridplatform.users.models import User

from .models import DataSource


@override_settings(ENCRYPTION_TESTMODE=True)
class DataSourceManagerTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer1 = Customer.objects.create()
        self.customer2 = Customer.objects.create()
        self.user = User(customer=self.customer1)
        self.user.is_authenticated = lambda: True

    def test_customerdatasources_visible_to_console(self):
        datasource1 = CustomerDataSource.objects.create(
            customer=self.customer1,
            unit='milliwatt*hour')
        datasource2 = CustomerDataSource.objects.create(
            customer=self.customer2,
            unit='milliwatt*hour')

        self.assertTrue(DataSource.objects.filter(id=datasource1.id).exists())
        self.assertTrue(DataSource.objects.filter(id=datasource2.id).exists())

    def test_filtered_customerdatasource(self):
        datasource = CustomerDataSource.objects.create(
            customer=self.customer1,
            unit='milliwatt*hour')
        with replace_customer(self.customer1), replace_user(self.user):
            self.assertTrue(
                DataSource.objects.filter(id=datasource.id).exists())

    def test_excluded_customerdatasource(self):
        datasource = CustomerDataSource.objects.create(
            customer=self.customer2,
            unit='milliwatt*hour')
        with replace_customer(self.customer1), replace_user(self.user):
            self.assertFalse(
                DataSource.objects.filter(id=datasource.id).exists())

    def test_filtered_datasource(self):
        datasource = DataSource.objects.create(
            unit='milliwatt*hour')
        with replace_customer(self.customer1), replace_user(self.user):
            self.assertTrue(
                DataSource.objects.filter(id=datasource.id).exists())
