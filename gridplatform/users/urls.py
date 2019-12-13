# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from gridplatform.users import views

urlpatterns = patterns(
    '',
    url(r'^profile/$', views.UserProfileView.as_view(), name='profile'),
)
