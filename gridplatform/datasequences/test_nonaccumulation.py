# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings
from django.core.exceptions import ValidationError

from gridplatform.providers.models import Provider
from gridplatform.customers.models import Customer

from .models import NonaccumulationDataSequence


@override_settings(ENCRYPTION_TESTMODE=True)
class NonaccumulationDataSequenceTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()

    def test_clean_happy(self):
        nonaccumulation = NonaccumulationDataSequence.objects.create(
            customer=self.customer,
            unit='milliwatt')
        nonaccumulation.clean()

    def test_clean_prevents_updating_unit(self):
        nonaccumulation = NonaccumulationDataSequence.objects.create(
            customer=self.customer,
            unit='milliwatt')

        nonaccumulation.unit = 'millikelvin'

        with self.assertRaises(ValidationError) as ctx:
            nonaccumulation.clean()

        self.assertIn('unit', ctx.exception.message_dict)
