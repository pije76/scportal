# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import binascii
import mock
import os

from django.http import HttpRequest
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import force_bytes

from rest_framework.exceptions import AuthenticationFailed

from gridplatform.users.models import User
from gridplatform.customers.models import Customer
from gridplatform.providers.models import Provider
from gridplatform import trackuser
from gridplatform import encryption
from gridplatform.encryption.testutils import encryption_context

from .authentication import EncryptionTokenAuthentication
from .models import TOKEN_LENGTH
from .models import HMAC_HEX_LENGTH
from .models import TokenData
from .models import create_token


class TokenDataTestCase(TestCase):
    def setUp(self):
        with encryption_context():
            self.user = User.objects.create_user(
                'user', 'password',
                user_type=User.CUSTOMER_USER)

    def test_create_token_obscures_password(self):
        password = '0123456789abcdef'
        token_string = create_token(self.user, password)
        self.assertNotIn(password, token_string)
        token_bytes = binascii.unhexlify(token_string)
        self.assertNotIn(force_bytes(password), token_bytes)

    def test_decode_token(self):
        password = '0123456789abcdef'
        token_string = create_token(self.user, password)
        token_data = TokenData.lookup_token(token_string)
        self.assertEqual(token_data.user_id, self.user.id)
        self.assertEqual(token_data.user, self.user)
        decrypted = token_data.decrypt_password(token_string)
        self.assertEqual(decrypted, password)

    def test_user_multiple_tokens(self):
        self.assertEqual(len(TokenData.objects.all()), 0)
        password = '0123456789abcdef'
        token_a = create_token(self.user, password)
        token_b = create_token(self.user, password)
        self.assertEqual(len(TokenData.objects.all()), 1)
        self.assertNotEqual(token_a, token_b)
        decrypted_a = TokenData.lookup_token(token_a).decrypt_password(token_a)
        decrypted_b = TokenData.lookup_token(token_b).decrypt_password(token_b)
        self.assertEqual(decrypted_a, password)
        self.assertEqual(decrypted_b, password)

    def test_multiple_users(self):
        with encryption_context():
            other_user = User.objects.create_user(
                'other_user', 'some_password',
                user_type=User.CUSTOMER_USER)
        self.assertEqual(len(TokenData.objects.all()), 0)
        password_a = '0123456789abcdef'
        password_b = '0123456789abcdef'
        token_a = create_token(self.user, password_a)
        token_b = create_token(other_user, password_b)
        self.assertEqual(len(TokenData.objects.all()), 2)
        self.assertNotEqual(token_a, token_b)
        decrypted_a = TokenData.lookup_token(token_a).decrypt_password(token_a)
        decrypted_b = TokenData.lookup_token(token_b).decrypt_password(token_b)
        self.assertEqual(decrypted_a, password_a)
        self.assertEqual(decrypted_b, password_b)


@override_settings(SECURE_PROXY_SSL_HEADER=None)
class EncryptionTokenAuthenticationTestCase(TestCase):
    def setUp(self):
        self.unit = EncryptionTokenAuthentication()
        os.environ['HTTPS'] = 'on'

    def tearDown(self):
        trackuser._set_user(None)
        trackuser._set_customer(None)
        encryption._set_ephemeral_private_key(None)
        del os.environ['HTTPS']

    def test_header_not_https(self):
        os.environ['HTTPS'] = 'off'
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = 'Token'
        auth = self.unit.authenticate(request)
        self.assertIsNone(auth)
        # NOTE: "same" request, but *with* HTTPS, to demonstrate difference...
        os.environ['HTTPS'] = 'on'
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = 'Token'
        with self.assertRaises(AuthenticationFailed):
            self.unit.authenticate(request)

    def test_header_missing(self):
        request = HttpRequest()
        auth = self.unit.authenticate(request)
        self.assertIsNone(auth)

    def test_header_empty(self):
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = ''
        auth = self.unit.authenticate(request)
        self.assertIsNone(auth)

    def test_not_token(self):
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = 'stuff'
        auth = self.unit.authenticate(request)
        self.assertIsNone(auth)

    def test_empty(self):
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = 'Token'
        with self.assertRaises(AuthenticationFailed):
            self.unit.authenticate(request)

    def test_extra_parts(self):
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = 'Token password more'
        with self.assertRaises(AuthenticationFailed):
            self.unit.authenticate(request)

    def test_wrong_length(self):
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = 'Token tokenstring'
        with self.assertRaises(AuthenticationFailed):
            self.unit.authenticate(request)

    def test_non_existing(self):
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = 'Token ' + 'a' * TOKEN_LENGTH
        with self.assertRaises(AuthenticationFailed):
            self.unit.authenticate(request)

    def test_user_deactivated(self):
        with encryption_context():
            password = '0123456789abcdef'
            user = User.objects.create_user(
                'username',
                password,
                user_type=User.CUSTOMER_USER)
        token_string = create_token(user, password)
        user.is_active = False
        user.save()
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = b'Token ' + token_string
        with self.assertRaises(AuthenticationFailed):
            self.unit.authenticate(request)

    def test_non_hex(self):
        with encryption_context():
            password = '0123456789abcdef'
            user = User.objects.create_user(
                'username',
                password,
                user_type=User.CUSTOMER_USER)
        token_string = create_token(user, password)
        broken_token = token_string[:HMAC_HEX_LENGTH] + \
            (TOKEN_LENGTH - HMAC_HEX_LENGTH) * 'x'
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = b'Token ' + broken_token
        with self.assertRaises(AuthenticationFailed):
            self.unit.authenticate(request)

    def test_wrong_password(self):
        with encryption_context():
            password = '0123456789abcdef'
            user = User.objects.create_user(
                'username',
                password,
                user_type=User.CUSTOMER_USER)
        wrong_password = 'x' + password[1:]
        token_string = create_token(user, wrong_password)
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = b'Token ' + token_string
        with self.assertRaises(AuthenticationFailed):
            self.unit.authenticate(request)

    def test_success(self):
        with encryption_context():
            password = '0123456789abcdef'
            user = User.objects.create_user(
                'username',
                password,
                user_type=User.CUSTOMER_USER)
        token_string = create_token(user, password)
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = b'Token ' + token_string
        auth_user, auth = self.unit.authenticate(request)
        self.assertEqual(auth_user, user)

    def test_success_context(self):
        with encryption_context():
            Provider.objects.create()
            customer = Customer()
            customer.save()
            password = '0123456789abcdef'
            user = User.objects.create_user(
                'username',
                password,
                user_type=User.CUSTOMER_USER,
                customer=customer)
            user.set_password(password)
            user.save()
        token_string = create_token(user, password)
        request = HttpRequest()
        request.META['HTTP_AUTHORIZATION'] = b'Token ' + token_string
        with mock.patch('gridplatform.token_auth.authentication.'
                        '_set_ephemeral_private_key') as x:
            auth_user, auth = self.unit.authenticate(request)
            self.assertEqual(user, trackuser.get_user())
            self.assertEqual(customer, trackuser.get_customer())
            x.assert_called_with(user.decrypt_private_key(password))
