# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse

from gridplatform import trackuser
from gridplatform.customers.models import Customer


@override_settings(ENCRYPTION_TESTMODE=True)
class ManageCustomerTest(TestCase):
    """
    Test that admin user can view and edit customers.
    """
    fixtures = ["super_user_and_customer.json"]

    def setUp(self):
        self.customer = Customer(name_plain='Test customer')
        self.customer.save()
        trackuser._set_customer(self.customer)
        assert self.customer is trackuser.get_customer()

        self.client.post('/login/', {'username': 'root',
                                     'password': 'feet'})

    def tearDown(self):
        trackuser._set_customer(None)

    def test_customer_list(self):
        """
        Test that admin can view a list of customers.
        """
        response = self.client.get(reverse('manage_customers-list-json'))
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, self.customer.name_plain)

    def test_customer_create_form_get(self):
        """
        Test that admin can get create customer view.
        """
        response = self.client.get(reverse('manage_customers-create'))
        self.assertContains(response, 'submit')

    def test_customer_create_form_empty_fails(self):
        """
        Test that admin can't create an empty customer.
        """
        response = self.client.post(reverse('manage_customers-update'))
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, 'errorlist')

    def test_customer_create_form_success(self):
        """
        Test that admin can create new customer.
        """
        response = self.client.post(
            reverse('manage_customers-update'),
            {
                'name': 'New test customer',
                'address': '',
                'timezone': 'Europe/Copenhagen',
                'currency_unit': 'currency_dkk',
                'postal_code': '',
                'country_code': '',
                'electricity_instantaneou': 'watt',
                'electricity_consumption': 'kilowatt*hour',
                'gas_instantaneous': 'liter*second^-1',
                'gas_consumption': 'meter*meter*meter',
                'water_instantaneous': 'meter*meter*meter*hour^-1',
                'water_consumption': 'meter*meter*meter',
                'heat_instantaneous': 'watt',
                'heat_consumption': 'kilowatt*hour',
                'oil_instantaneous': 'meter*meter*meter*hour^-1',
                'oil_consumption': 'meter*meter*meter',
                'temperature': 'celsius',
            })
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertNotContains(response, 'errorlist')
        self.assertContains(response, 'New test customer')

    def test_customer_update_form_get(self):
        """
        Test that admin can view customer.
        """
        response = self.client.get(
            reverse('manage_customers-form', kwargs={'pk': self.customer.id}))
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, self.customer.name_plain)

        for field in ('address', 'postal_code', 'country_code',
                      'timezone', 'currency_unit',
                      'electricity_instantaneous', 'electricity_consumption',
                      'gas_instantaneous', 'gas_consumption',
                      'water_instantaneous', 'water_consumption',
                      'heat_instantaneous', 'heat_consumption',
                      'oil_instantaneous', 'oil_consumption',
                      'temperature'):
            self.assertContains(response, field)

    def test_customer_update_form_success(self):
        """
        Test that admin can edit customer.
        """
        response = self.client.post(
            reverse('manage_customers-update',
                    kwargs={'pk': self.customer.id}),
            {
                'name': 'New name',
                'timezone': 'Europe/Copenhagen',
                'currency_unit': 'currency_dkk',
                'electricity_instantaneous': 'watt',
                'electricity_consumption': 'kilowatt*hour',
                'gas_instantaneous': 'liter*second^-1',
                'gas_consumption': 'meter*meter*meter',
                'water_instantaneous': 'meter*meter*meter*hour^-1',
                'water_consumption': 'meter*meter*meter',
                'heat_instantaneous': 'watt',
                'heat_consumption': 'kilowatt*hour',
                'oil_instantaneous': 'meter*meter*meter*hour^-1',
                'oil_consumption': 'meter*meter*meter',
                'temperature': 'celsius',
            })
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertNotContains(response, 'errorlist')
        self.assertContains(response, 'New name')

    def test_customer_update_form_empty_fail(self):
        """
        Test that admin can edit customer.
        """
        response = self.client.post(
            reverse('manage_customers-update',
                    kwargs={'pk': self.customer.id}),
            {
                'name': '',
                'timezone': '',
            })
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, 'errorlist')
