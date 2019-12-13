# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

from . import views

urlpatterns = patterns(
    '',
    url(r'^$',
        RedirectView.as_view(
            url=reverse_lazy('provider_site:customer-list')),
        name='home'),
    url(r'^customers/$',
        views.CustomerListView.as_view(),
        name='customer-list'),
    url(r'^customers/content$',
        views.CustomerListContentView.as_view(),
        name='customer-list-content'),
    url(r'^customers/create$',
        views.CustomerCreateView.as_view(),
        name='customer-create'),
    url(r'^customers/update/(?P<pk>\d+)/$',
        views.CustomerUpdateView.as_view(),
        name='customer-update'),

    url(r'^users/$',
        views.UserListView.as_view(),
        name='user-list'),
    url(r'^users/content$',
        views.UserListContentView.as_view(),
        name='user-list-content'),
    url(r'^users/create$',
        views.UserCreateView.as_view(),
        name='user-create'),
    url(r'^users/update/(?P<pk>\d+)/$',
        views.UserUpdateView.as_view(),
        name='user-update'),

    url(r'^api_users/$',
        views.APIUserListView.as_view(),
        name='apiuser-list'),
    url(r'^api_users/content$',
        views.APIUserListContentView.as_view(),
        name='apiuser-list-content'),
    url(r'^api_users/create$',
        views.APIUserCreateView.as_view(),
        name='apiuser-create'),
    url(r'^api_users/update/(?P<pk>\d+)/$',
        views.APIUserUpdateView.as_view(),
        name='apiuser-update'),
)
