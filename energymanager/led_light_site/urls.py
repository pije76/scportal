# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns
from django.conf.urls import url
from django.conf.urls import include

from gridplatform.utils.urls import restricted_url

from . import views

urlpatterns = patterns(
    'energymanager.led_light_view.views',
    url(r'^$',
        views.HomeView.as_view(),
        name='home'),
    url(r'^customer/(?P<customer_id>\d+)/$',
        views.CustomerView.as_view(),
        name='customer'),
    url(r'^choose-customer/$',
        views.ChooseCustomer.as_view(),
        name='choose-customer'),
    url(r'^(?P<customer_id>\d+)/dashboard/$',
        views.DashboardDetailView.as_view(),
        name='dashboard'),
)
