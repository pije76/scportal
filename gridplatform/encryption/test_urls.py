# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns
from django.http import HttpResponse, HttpResponseBadRequest
from django import template

from .conf import settings
from .tests import ModelWithSecrets
from .tests import TestModel
from .models import EncryptionKey
from .middleware import _store
from . import get_encryption_context


def simple_view(request):
    return HttpResponse()


def set_secret(request):
    secret = request.POST['secret']
    setattr(_store, settings.ENCRYPTION_STORE_KEY, secret)
    return HttpResponse()


def get_secret(request):
    secret = getattr(_store, settings.ENCRYPTION_STORE_KEY, None)
    if secret is not None:
        return HttpResponse(secret)
    else:
        return HttpResponseBadRequest()


def encryption_password_change(request):
    user = request.user
    old_password = request.POST['old_password']
    new_password = request.POST['new_password']
    user.update_private_key(old_password, new_password, save=True)
    return HttpResponse()


def read_context(request):
    t = template.Template('')
    c = template.Context({
        'encryption_context': getattr(_store, 'encryption_context', None)
    })
    return HttpResponse(t.render(c))


def after_login(request):
    password = request.POST['password']
    _store.private_key = request.user.decrypt_private_key(password)
    return read_context(request)


def generate_data_key(request):
    link_id = int(request.POST['link_id'])
    key_id = (TestModel, link_id)
    EncryptionKey.generate(key_id)
    return read_context(request)


def read_secret(request):
    obj_id = int(request.GET['id'])
    link_id = int(request.GET['link_id'])
    obj = ModelWithSecrets.objects.get(pk=obj_id)
    obj.mock_encryption_id = (TestModel, link_id)
    try:
        obj._decrypt(get_encryption_context())
    except UnicodeDecodeError:
        # Output from AES decryption was not valid UTF-8; wrong decryption
        # key...
        pass
    t = template.Template('')
    c = template.Context({
        'obj': obj,
    })
    return HttpResponse(t.render(c))


def store_secret(request):
    link_id = int(request.POST['link_id'])
    obj = ModelWithSecrets()
    obj.name_plain = request.POST['name']
    obj.other_plain = request.POST['other']
    obj.mock_encryption_id = (TestModel, link_id)
    obj.save()
    t = template.Template('')
    c = template.Context({
        'obj': obj,
    })
    return HttpResponse(t.render(c))


urlpatterns = patterns(
    '',
    (r'^$', simple_view),
    (r'^set_secret/$', set_secret),
    (r'^get_secret/$', get_secret),
    (r'^encryption_password_change/$', encryption_password_change),
    (r'^after_login/$', after_login),
    (r'^read_context/$', read_context),
    (r'^generate_data_key/$', generate_data_key),
    (r'^store_secret/$', store_secret),
    (r'^read_secret/$', read_secret),
)
