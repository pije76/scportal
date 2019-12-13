# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module contains tests for classes defined in the trackuser package.
"""

from mock import patch

from django.test import TestCase
from django.test.utils import override_settings

from celery import Task
from celery import shared_task

from gridplatform.customers.models import Customer
from gridplatform.users.models import User
from gridplatform.providers.models import Provider

from .tasks import trackuser_task
from . import replace_user
from . import replace_customer
from . import get_user
from . import get_customer


@trackuser_task
@shared_task(ignore_result=True)
class TrackUserTaskShunt(Task):
    def run(self, test_case):
        test_case.assertIsNotNone(get_user())
        test_case.assertIsNotNone(get_customer())
        test_case.assertEquals(test_case.user, get_user())
        test_case.assertEqual(test_case.customer, get_customer())


@trackuser_task
@shared_task(ignore_result=True)
def trackuser_task_shunt(test_case):
    test_case.assertIsNotNone(get_user())
    test_case.assertIsNotNone(get_customer())
    test_case.assertEquals(test_case.user, get_user())
    test_case.assertEqual(test_case.customer, get_customer())


@override_settings(
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    CELERY_ALWAYS_EAGER=True,
    BROKER_BACKEND='memory',
    ENCRYPTION_TESTMODE=True)
class TrackUserTaskTest(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.user = User.objects.create_user(
            'username', 'password', user_type=User.CUSTOMER_USER,
            customer=self.customer)
        self.customer_context = replace_customer(self.customer)
        self.user_context = replace_user(self.user)

    def test_task_class_run_in_trackuser_context(self):
        self.assertIsNone(get_user())
        self.assertIsNone(get_customer())
        TrackUserTaskShunt.run(
            self, _user_id=self.user.id, _customer_id=self.customer.id)

    def test_task_function_run_in_trackuser_context(self):
        self.assertIsNone(get_user())
        self.assertIsNone(get_customer())
        trackuser_task_shunt.run(
            self, _user_id=self.user.id, _customer_id=self.customer.id)

    def test_task_class_call_in_trackuser_context(self):
        TrackUserTaskShunt(
            self, _user_id=self.user.id, _customer_id=self.customer.id)

    def test_task_function_call_in_trackuser_context(self):
        trackuser_task_shunt(
            self, _user_id=self.user.id, _customer_id=self.customer.id)

    def test_delay_delegates_context_to_run(self):
        with self.customer_context, self.user_context:
            with patch.object(TrackUserTaskShunt, 'run') as mock:
                TrackUserTaskShunt.delay('foo', bar='baz')

        mock.assert_called_with(
            'foo', bar='baz', _user_id=self.user.id,
            _customer_id=self.customer.id)

    def test_apply_async_noargs_delegates_context_to_run(self):
        with self.customer_context, self.user_context:
            with patch.object(TrackUserTaskShunt, 'run') as mock:
                TrackUserTaskShunt.apply_async()
        mock.assert_called_with(
            _user_id=self.user.id, _customer_id=self.customer.id)
