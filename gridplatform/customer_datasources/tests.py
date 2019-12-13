# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from gridplatform.providers.models import Provider
from gridplatform.customers.models import Customer
from gridplatform.trackuser import replace_customer

from .models import CustomerDataSource


@override_settings(
    ENCRYPTION_TESTMODE=True)
class CustomerDataSourceEncryptionTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()

    def test_name(self):
        with replace_customer(self.customer):
            pk = CustomerDataSource.objects.create(
                name_plain='test name',
                unit='milliwatt*hour').id

        self.assertEqual(
            CustomerDataSource.objects.get(id=pk).name_plain,
            'test name')

    def test_blank_name(self):
        with replace_customer(self.customer):
            pk = CustomerDataSource.objects.create(
                unit='milliwatt*hour').id

        self.assertEqual(
            CustomerDataSource.objects.get(id=pk).name_plain, '')
