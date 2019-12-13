# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'legacy.display_widgets.views',
    url(r'^$', 'dashboard',
        name='display_widgets-dashboard'),
    url(r'^fullscreen/$', 'dashboard_fullscreen',
        name='display_widgets-dashboard-fullscreen'),
    url(r'^remove/$',
        'remove_from_dashboard',
        name='display_widgets-remove-from-dashboard'),
    url(r'^add/(?P<pk>\d+)/(?P<widget_type>\d+)$',
        'add_to_dashboard',
        name='display_widgets-add-to-dashboard'),
    url(r'^remove_specific/(?P<pk>\d+)/(?P<widget_type>\d+)$',
        'remove_specific_widget',
        name='display_widgets-remove-specific-widget'),
    url(r'^update_order/$',
        'update_order',
        name='display_widgets-update-order'),
    url('^async_gague/(?P<pk>\d+)/$', 'async_gauge',
        name='display_widgets-async_gauge'),
)
