# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns
from django.conf.urls import url

from . import views

urlpatterns = patterns(
    'energymanager.price_relay_site.views',
    url(r'^$',
        views.HomeView.as_view(),
        name='home'),
    url(r'^customer/(?P<customer_id>\d+)/$',
        views.CustomerView.as_view(),
        name='customer'),
    url(r'^choose-customer/$',
        views.ChooseCustomer.as_view(),
        name='choose-customer'),
    url(r'^connection/(?P<customer_id>\d+)/$',
        views.DatahubConnectionList.as_view(),
        name='connection-list'),
    url(r'^project/content/(?P<customer_id>\d+)/$',
        views.DatahubConnectionListContentView.as_view(),
        name='connection-list-content'),
    url(r'^connection/create/(?P<customer_id>\d+)/$',
        views.DatahubConnectionCreateView.as_view(),
        name='connection-create'),
    url(r'^connection/update/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.DatahubConnectionUpdateView.as_view(),
        name='connection-update'),
    url(r'^authorizations/',
        views.datahub_authorization_view,
        name='authorizations-view'),
)
