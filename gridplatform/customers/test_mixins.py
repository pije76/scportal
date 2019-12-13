# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from gridplatform.providers.models import Provider
from gridplatform.encryption.models import EncryptedModel
from gridplatform.encryption.fields import EncryptedCharField

from .models import Customer
from .mixins import EncryptionCustomerFieldMixin


class TestModel(EncryptionCustomerFieldMixin, EncryptedModel):
    name = EncryptedCharField('name', max_length=200)


class EncryptionCustomerFieldMixinTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()

    def test_encryption_id(self):
        instance = TestModel(
            customer=self.customer)
        self.assertEqual(
            (Customer, self.customer.id), instance.get_encryption_id())

    @override_settings(ENCRYPTION_TESTMODE=True)
    def test_encrypted_model_integration(self):
        instance = TestModel.objects.create(
            customer=self.customer, name_plain='pöp cørn')
        self.assertEqual(
            TestModel.objects.get(id=instance.id).name_plain, 'pöp cørn')
