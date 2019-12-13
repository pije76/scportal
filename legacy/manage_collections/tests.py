# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from StringIO import StringIO

from django.test import TestCase
from django.test.utils import override_settings

from PIL import Image

from gridplatform import trackuser
from legacy.measurementpoints.models import Collection
from gridplatform.users.models import User
from gridplatform.encryption.shell import Request
from gridplatform.utils import utilitytypes

from .models import Floorplan


@override_settings(ENCRYPTION_TESTMODE=True)
class CollectionTestSetup(TestCase):
    fixtures = ["manage_indexes_test.json"]

    def setUp(self):
        self.client.post('/login/', {"username": "super",
                                     'password': "123"})

        self.customer = User.objects.get(
            id=self.client.session["_auth_user_id"]).customer
        trackuser._set_customer(self.customer)
        assert self.customer.id and self.customer == \
            trackuser.get_customer()

        self.request = Request('super', '123')

        self.group = Collection.objects.create(
            name_plain='Test group',
            role=Collection.GROUP,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)
        self.assertFalse(Floorplan.objects.filter(
            collection=self.group).exists())

    def tearDown(self):
        trackuser._set_customer(None)


class TestCollectionView(CollectionTestSetup):
    def test_group_form_success(self):
        """
        Test C{group_form} wizard view for adding a collection.
        """
        NAME = "Test collection"

        response = self.client.get("/groups/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            "/groups/form/")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/groups/update/",
            data={
                'name': NAME,
                'parent': ''
            })
        self.assertNotContains(response, 'error')

        # Verify JSON slide
        response = self.client.get(
            "/groups/json/groups/")
        self.assertContains(response, NAME)

        collection = Collection.objects.\
            subclass_only().order_by('-id')[0].subclass_instance

        # Verify model
        self.assertEqual(collection.name_plain, NAME)

        # # Verify edit form
        response = self.client.get(
            '/groups/form/%s' % collection.id)
        self.assertContains(response, NAME)

    def test_group_form_failed(self):
        """
        Test C{group_form} wizard view for adding a collection
        with faulty input.
        """
        response = self.client.post(
            "/groups/update/",
            data={
                'name': '',
                'parent': ''
            })
        self.assertContains(response, 'error')

    def test_group_edit_form_success(self):
        """
        Test C{group_form} wizard view for edition a collection group.
        """
        response = self.client.post(
            "/groups/update/%d" % self.group.id,
            data={
                'name': 'New name',
                'parent': ''
            })
        self.assertNotContains(response, 'error')

        # Verify model
        collection = Collection.objects.get(id=self.group.id)
        self.assertEqual(collection.name_plain, 'New name')

    def test_group_edit_form_failed(self):
        """
        Test C{group_form} wizard view for edition a collectin group
        with faulty input.
        """
        response = self.client.post(
            "/groups/update/%d" % self.group.id,
            data={
                'name': '',
                'parent': ''})
        self.assertContains(response, 'error')


@override_settings(ENCRYPTION_TESTMODE=True)
class TestFloorPlanView(CollectionTestSetup):
    """
    Test the L{floorplan} view.
    """
    fixtures = ["manage_indexes_test.json"]

    def setUp(self):
        self.client.post('/login/', {"username": "super",
                                     'password': "123"})

        self.customer = User.objects.get(
            id=self.client.session["_auth_user_id"]).customer
        trackuser._set_customer(self.customer)
        assert self.customer.id and self.customer == trackuser.get_customer()

        self.request = Request('super', '123')

        self.group = Collection.objects.create(
            name_plain='Test group',
            role=Collection.GROUP,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)
        self.assertFalse(Floorplan.objects.filter(
            collection=self.group).exists())

    def tearDown(self):
        trackuser._set_customer(None)

    def create_image(self, width, height, name):
        # http://janneke-janssen.blogspot.dk/2012/01/
        #     django-testing-imagefield-with-test.html
        file_obj = StringIO()
        image = Image.new("RGBA", size=(width, height), color=(256, 0, 0))
        image.save(file_obj, 'png')
        file_obj.name = '%s.png' % name
        file_obj.seek(0)
        return file_obj

    def test_show_new(self):
        response = self.client.get('/groups/floorplan/%d' % self.group.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Floorplan.objects.filter(
            collection=self.group).exists())

    def test_create_new_then_show_then_update_then_show(self):
        response = self.client.post(
            '/groups/floorplan/%d' % self.group.id,
            {'image': self.create_image(1200, 400, 'test1')})
        self.assertEqual(response.status_code, 200)

        floor_plan = Floorplan.objects.get(collection=self.group)
        self.assertEqual(floor_plan.image.width, 900)
        self.assertEqual(floor_plan.image.height, 300)

        response = self.client.get('/groups/floorplan/%d' % self.group.id)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            '/groups/floorplan/%d/image' % self.group.floorplan.id)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            '/groups/floorplan/%d' % self.group.id,
            {'image': self.create_image(400, 1200, 'test2')})
        self.assertEqual(response.status_code, 200)

        floor_plan = Floorplan.objects.get(collection=self.group)
        self.assertEqual(floor_plan.image.width, 300)
        self.assertEqual(floor_plan.image.height, 900)

        response = self.client.get(
            '/groups/floorplan/%d/image' % self.group.floorplan.id)
        self.assertEqual(response.status_code, 200)

    def test_create_new_with_errors(self):
        self.assertFalse(Floorplan.objects.filter(
            collection=self.group).exists())
        response = self.client.post(
            '/groups/floorplan/%d' % self.group.id,
            {'image': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'errorlist', response.content)

        self.assertFalse(Floorplan.objects.filter(
            collection=self.group).exists())
