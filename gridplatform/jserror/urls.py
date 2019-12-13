# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from .views import jserror


urlpatterns = patterns(
    '',
    url('^$', jserror, name='jserror-jserror')
)
