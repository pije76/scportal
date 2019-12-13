# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from gridplatform.users.decorators import auth_or_redirect


urlpatterns = patterns(
    'legacy.manage_users.views',
    url(r'^$', auth_or_redirect(TemplateView.as_view(
        template_name='manage_users/list.html')),
        name='manage_users-list'),
    url(r'^json/users/$', 'list_json', name='manage_users-list-json'),
    url(r'^form/$', 'user_form', name='manage_users-form'),
    url(r'^form/(?P<pk>\d+)$', 'user_form', name='manage_users-form'),
    url(r'^update/$', 'user_update', name='manage_users-update'),
    url(r'^update/(?P<pk>\d+)$', 'user_update', name='manage_users-update'),
    url(r'^delete/$', 'user_delete', name='manage_users-delete'),
)
