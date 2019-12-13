# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from energymanager.start_site import views

urlpatterns = patterns(
    'legacy.website.views',
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    url(r'^apps/$', views.AppsView.as_view(), name='apps'),
)
