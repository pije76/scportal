# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'legacy.website.views',
    url(r'^$',
        'find_home',
        name='website-home'),
    url(r'^login/$', 'login', name='website-login'),
    url(r'^logout/$', 'logout', name='website-logout'),
    url(r'^legacy_task_status/$', 'task_status', name='website-task_status'),
    url(r'^cancel_task/$', 'cancel_task', name='website-cancel_task'),
    url(r'^json_task_result/$', 'json_task_result',
        name='website-json_task_result'),
)
