# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from gridplatform import trackuser
from gridplatform.users.models import User


@override_settings(ENCRYPTION_TESTMODE=True)
class ManageUserTest(TestCase):
    """
    Test that super user can view and edit users.
    """
    fixtures = ["super_user_and_customer.json"]

    def setUp(self):
        self.client.post('/login/', {"username": "super",
                                     'password': "123"})
        self.user = User.objects.get(id=self.client.session["_auth_user_id"])
        self.customer = self.user.customer
        trackuser._set_customer(self.customer)
        assert self.customer is trackuser.get_customer()

    def tearDown(self):
        trackuser._set_customer(None)
        trackuser._set_user(None)

    def test_users_list(self):
        """
        Test that super user can view a list of users.
        """
        response = self.client.get('/users/json/users/')
        self.assertNotContains(response, 'XYZXYZXYZ')

    def test_user_create_form_get(self):
        """
        Test that super user can get create user view.
        """
        response = self.client.get('/users/form/')
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertNotContains(response, 'data-reason')
        self.assertContains(response, 'name="user_type"')
        self.assertContains(response, 'submit')

    def test_user_create_form_empty_fails(self):
        """
        Test that admin can't create an empty customer.
        """
        response = self.client.post('/users/update/')
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, 'errorlist', count=3)

    def test_user_create_form_success(self):
        """
        Test that super user can create new user.
        """
        response = self.client.post(
            '/users/update/',
            {
                'name': 'New test user',
                'e_mail': 'test@test.dk',
                'phone': '12345678',
                'mobile': '87654321'
            })
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertNotContains(response, 'errorlist')
        self.assertContains(response, 'New test user')

    def test_user_update_form_get(self):
        user = self.get_test_user()
        response = self.client.get('/users/form/%s' % user.id)
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, user.name_plain)
        self.assertContains(response, 'name="user_type"')
        self.assertContains(response, 'submit')

    def test_user_update_form_success(self):
        user = self.get_test_user()
        response = self.client.post(
            '/users/update/%s' % user.id,
            {
                'name': 'New test user',
                'e_mail': 'test@test.dk',
                'phone': '12345678',
                'mobile': '87654321'
            })
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, 'New test user')
        new_user = User.objects.latest('id')
        self.assertEqual(new_user.customer_id, self.user.customer_id)

    def test_user_update_form_empty_fail(self):
        user = self.get_test_user()
        response = self.client.post(
            '/users/update/%s' % user.id,
            {
                'name': '',
                'e_mail': '',
                'phone': '',
                'mobile': '',
                'user_type': '3'
            })
        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, 'errorlist', count=3)

    def test_user_cannot_edit_own_user_type(self):
        response = self.client.get('/users/form/%s' % self.user.id)
        self.assertContains(response, 'name="user_type" type="hidden"')

    def get_test_user(self):
        self.test_user_create_form_success()
        return User.objects.latest('id')
