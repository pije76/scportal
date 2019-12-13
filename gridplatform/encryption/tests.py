# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pickle

from django.test import TestCase
from django.test import SimpleTestCase
from django.test import RequestFactory
from django.http import HttpResponse
from django.db import models
from django.contrib.sessions.middleware import SessionMiddleware
from django.forms.models import modelform_factory
from django.test.utils import override_settings

from gridplatform.users.models import User

from .base import EncryptionContext
from .base import _store
from .conf import settings
from .fields import EncryptedCharField
from .middleware import EncryptionMiddleware
from .models import EncryptedModel
from .testutils import encryption_context


class TestModel(models.Model):
    pass


# simple/"raw" tests
@override_settings(
    MIDDLEWARE_CLASSES=[
        x for x in settings.MIDDLEWARE_CLASSES
        if x != 'gridplatform.encryption.middleware.KeyLoaderMiddleware'])
class MiddlewareTest(TestCase):
    def setUp(self):
        self.session = SessionMiddleware()
        self.encryption = EncryptionMiddleware()

    def test_no_data(self):
        request = RequestFactory().get('/')

        self.session.process_request(request)
        self.encryption.process_request(request)
        self.assertNotIn(settings.ENCRYPTION_SESSION_KEY, request.session)

    def test_store_load(self):
        secret_text = 'secret secret'

        # simulate an incoming request
        request = RequestFactory().get('/')
        self.session.process_request(request)
        self.encryption.process_request(request)
        # add the secret data to the request "somewhere in the handling"
        _store.private_key = secret_text

        # simulate the response in this context
        response = HttpResponse()
        response = self.encryption.process_response(request, response)
        self.assertTrue(request.session.modified)
        response = self.session.process_response(request, response)
        # we have store "something" in the session --- can't really check that
        # it is securely encrypted...
        self.assertIn('encryption_private_key', request.session)
        self.assertNotEqual(
            request.session['encryption_private_key'], secret_text)
        # we have put something in the expected cookie
        self.assertIn(settings.ENCRYPTION_COOKIE_NAME, response.cookies)

        # set up context; received cookies must be used in next request
        request_factory = RequestFactory()
        request_factory.cookies = response.cookies

        # simulate next request
        request = request_factory.get('/')
        # sanity check, the secret data is *not* present on the request
        self.assertIsNone(getattr(_store, 'private_key'))
        self.session.process_request(request)
        self.encryption.process_request(request)
        # the secret data should be available now
        self.assertEqual(_store.private_key, secret_text)

    def test_repeated_store(self):
        secret_text = 'secret secret'

        request = RequestFactory().get('/')
        self.session.process_request(request)
        self.encryption.process_request(request)
        setattr(_store, settings.ENCRYPTION_STORE_KEY, secret_text)

        response = HttpResponse()
        response = self.encryption.process_response(request, response)
        response = self.session.process_response(request, response)

        request_factory = RequestFactory()
        request_factory.cookies = response.cookies

        request = request_factory.get('/')
        self.session.process_request(request)
        self.encryption.process_request(request)

        # same value, i.e. should not lead to session modified
        setattr(_store, settings.ENCRYPTION_STORE_KEY, secret_text)
        response = HttpResponse()
        response = self.encryption.process_response(request, response)
        response = self.session.process_response(request, response)
        self.assertFalse(request.session.modified)

        # same factory; cookies kept...
        request = request_factory.get('/')
        self.session.process_request(request)
        self.encryption.process_request(request)
        self.assertEqual(
            getattr(_store, settings.ENCRYPTION_STORE_KEY), secret_text)

        # new data
        setattr(_store, settings.ENCRYPTION_STORE_KEY, secret_text + 'x')
        response = HttpResponse()
        response = self.encryption.process_response(request, response)
        response = self.session.process_response(request, response)
        self.assertTrue(request.session.modified)

        # new data replaced old...
        request = request_factory.get('/')
        self.session.process_request(request)
        self.encryption.process_request(request)
        self.assertEqual(
            getattr(_store, settings.ENCRYPTION_STORE_KEY), secret_text + 'x')


# Using the simulated client --- it keeps track of client state wrt. cookies,
# but this test requires more setup...
@override_settings(
    MIDDLEWARE_CLASSES=[
        x for x in settings.MIDDLEWARE_CLASSES
        if x != 'gridplatform.encryption.middleware.KeyLoaderMiddleware'])
class MiddlewareClientTest(TestCase):
    urls = 'gridplatform.encryption.test_urls'

    def test_client(self):
        with encryption_context():
            User.objects.create_user(
                username='testuser', password='testpassword',
                user_type=0)

        # no secret present
        response = self.client.get('/get_secret/')
        self.assertEqual(response.status_code, 400)

        # save, read
        self.client.login(username='testuser', password='testpassword')
        self.client.post('/set_secret/', {'secret': 'my secret string'})
        response = self.client.get('/get_secret/')
        self.assertEqual(response.content, 'my secret string')

        # cleared on logout
        self.client.logout()
        response = self.client.get('/get_secret/')
        self.assertEqual(response.status_code, 400)

        # not reinstated on login
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get('/get_secret/')
        self.assertEqual(response.status_code, 400)

        # set, overwrite...
        self.client.post('/set_secret/', {'secret': 'secret 1'})
        response = self.client.get('/get_secret/')
        self.assertEqual(response.content, 'secret 1')
        self.client.post('/set_secret/', {'secret': 'secret 2'})
        response = self.client.get('/get_secret/')
        self.assertEqual(response.content, 'secret 2')


class ModelWithSecrets(EncryptedModel):
    name = EncryptedCharField(max_length=8)
    other = models.CharField(max_length=5)

    mock_encryption_id = None

    def get_encryption_id(self):
        return self.mock_encryption_id


class MockEncryptionContext(EncryptionContext):
    def __init__(self, keys):
        self.keys = keys


class LoginTest(TestCase):
    urls = 'gridplatform.encryption.test_urls'

    def test_decrypt(self):
        with encryption_context():
            password = 'testpassword'
            User.objects.create_user(
                username='logintestuser', password=password,
                user_type=0)

        self.client.login(username='logintestuser', password=password)
        # loading private key, constructing context "works" --- though we have
        # no actual data in the context now...
        response = self.client.post('/after_login/', {'password': password})
        self.assertEqual(response.context['encryption_context'].keys, {})

        self.client.post('/encryption_password_change/', {
            'old_password': password,
            'new_password': password + 'x',
        })
        # changing password used for encryption should fail if the old password
        # is not the right encryption key (semi-white-box testing; for this
        # error, the exception raised is known to be ValueError...)
        self.assertRaises(ValueError, lambda: self.client.post(
            '/encryption_password_change/', {
                'old_password': password,
                'new_password': password + 'y',
            }))
        # the previous "failure" should not lead to further errors
        self.client.post('/encryption_password_change/', {
            'old_password': password + 'x',
            'new_password': password,
        })

        # put data in context --- in current context; stored...
        response = self.client.post('/generate_data_key/', {'link_id': 3})
        secret = response.context['encryption_context'].keys[(TestModel, 3)]

        # logging out removes context
        self.client.logout()
        response = self.client.get('/read_context/')
        self.assertEqual(response.context['encryption_context'].keys, {})

        # logging in does not add context before after_login
        self.client.login(username='logintestuser', password=password)
        response = self.client.get('/read_context/')
        self.assertEqual(response.context['encryption_context'].keys, {})

        # with after_login, the private key is loaded into the session
        response = self.client.post('/after_login/', {'password': password})
        self.assertEqual(response.context['encryption_context'].keys, {})
        # ... and used by middleware on the *next* request (doing it
        # immediately is not worth the bother; the login-page will redirect on
        # success anyway...)
        response = self.client.get('/read_context/')
        self.assertEqual(
            response.context['encryption_context'].keys[
                (TestModel, 3)], secret)

        # the context is still present...
        response = self.client.get('/read_context/')
        self.assertEqual(
            response.context['encryption_context'].keys[
                (TestModel, 3)], secret)

        # store some encrypted data...
        response = self.client.post('/store_secret/', {
            'link_id': 3,
            'name': 'hello',
            'other': 'world',
        })
        secret_obj = response.context['obj']

        response = self.client.get('/read_secret/', {
            'id': secret_obj.id,
            'link_id': 3,
        })
        other_obj = response.context['obj']
        self.assertEqual(secret_obj.name, other_obj.name)
        self.assertEqual(secret_obj.other, other_obj.other)

        # add key to context...
        response = self.client.post('/generate_data_key/', {'link_id': 5})
        # other_secret = response.context['encryption_context'][5]

        # does not mess with existing key
        response = self.client.get('/read_secret/', {
            'id': secret_obj.id,
            'link_id': 3,
        })
        other_obj = response.context['obj']
        self.assertEqual(secret_obj.name, other_obj.name)
        self.assertEqual(secret_obj.other, other_obj.other)

        # new key won't work for object bound to other...
        response = self.client.get('/read_secret/', {
            'id': secret_obj.id,
            'link_id': 5,
        })
        other_obj = response.context['obj']
        # ... though the failure is that the "decrypted" data is garbage...
        self.assertNotEqual(secret_obj.name_plain, other_obj.name_plain)
        self.assertEqual(secret_obj.other, other_obj.other)

        # make/save secret object through modelform...
        form_class = modelform_factory(ModelWithSecrets)
        form = form_class({'name': u'testingå', 'other': 'more'})
        # note: is_valid() has side effects...
        self.assertTrue(form.is_valid())
        obj = form.save(commit=False)
        # self.assertRaises(Exception, obj.save)
        obj.mock_encryption_id = (TestModel, 3)
        mock_encryption_context = \
            MockEncryptionContext({(TestModel, 3): secret})
        setattr(
            _store,
            settings.ENCRYPTION_CONTEXT_STORE_KEY,
            mock_encryption_context)
        obj.save()
        setattr(_store, settings.ENCRYPTION_CONTEXT_STORE_KEY, None)

        # read/check the data stored through modelform
        response = self.client.get('/read_secret/', {
            'id': obj.id,
            'link_id': 3,
        })
        self.assertEqual(response.context['obj'].name, obj.name)
        self.assertEqual(response.context['obj'].other, 'more')
        self.assertEqual(response.context['obj'].name_plain, u'testingå')


class EncryptedModelTest(TestCase):
    """
    Test L{EncryptedModel}.
    """

    def test_broken(self):
        """
        Test that EncryptedField reports error on use with model without
        encryption support.
        """
        def define_broken_class():
            class BrokenModel(models.Model):
                name = EncryptedCharField(max_length=20)
        self.assertRaises(AssertionError, define_broken_class)


class PickleFail(SimpleTestCase):
    def test_legal(self):
        obj = ModelWithSecrets()
        obj.name = 'testing'
        obj_copy = pickle.loads(pickle.dumps(obj))
        self.assertEqual(obj, obj_copy)

    def test_illegal(self):
        obj = ModelWithSecrets()
        obj.name_plain = 'testing'
        with self.assertRaises(ValueError):
            pickle.dumps(obj)
