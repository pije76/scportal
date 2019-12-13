# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'gridplatform.reports.views',
    url(r'^status/$',
        'status',
        name='reports-status'),
    url(r'^(?P<id>\d+)/(?P<title>.*)$',
        'serve',
        name='reports-serve'),
)
