# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.db.models import ProtectedError

from gridplatform import trackuser
from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.models import CollectionConstraint
from gridplatform.customers.models import Customer
from gridplatform.encryption.testutils import no_encryption
from gridplatform.providers.models import Provider

from .models import User


class TestUser(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_dependency(self):
        customer = self.customer
        assert customer is trackuser.get_customer()

        with no_encryption():
            collection = Collection.objects.create(
                name='test collection',
                customer=customer,
                role=Collection.GROUP,
                utility_type=0)

            user = User.objects.create_user(
                'test@gridmanager.dk',
                'totallyrandompassword',
                user_type=0)

            CollectionConstraint.objects.create(
                collection_id=collection.id,
                userprofile=user.userprofile)

            assert list(user.userprofile.collections.all()) == [collection]

            self.assertRaises(ProtectedError, lambda: collection.delete())
