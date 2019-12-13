# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'legacy.display_measurementpoints.views',
    url('^$', 'index',
        name='display_measurementpoints-index'),
    url('^(?P<pk>\d+)/$', 'group',
        name='display_measurementpoints-group'),
    url('^fullscreen/(?P<pk>\d+)/$', 'fullscreen_floorplan',
        name='display_measurementpoints-fullscreen_floorplan'),
    url('^async_graph/(?P<pk>\d+)/$', 'async_graph',
        name='display_measurementpoints-async_graph'),
    url('^async_graph_last_24h/(?P<pk>\d+)/$', 'async_graph_last_24h',
        name='display_measurementpoints-async_graph_last_24h'),
    url('^floorplan_values/(?P<pk>\d+)/$', 'floorplan_values',
        name='display_measurementpoints-floorplan-values'),
)
