# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'legacy.edit_userprofile.views',
    url(r'^(?P<pk>\d+)$', 'userprofile_form',
        name='edit_userprofile'),
    url(r'^update/(?P<pk>\d+)$', 'userprofile_update',
        name='edit_userprofile-update'),
)
