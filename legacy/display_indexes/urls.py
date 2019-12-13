# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'legacy.display_indexes.views',
    url('^$', 'index',
        name='display_indexes-index'),
    url('^(?P<pk>\d+)/', 'detail',
        name='display_indexes-detail'),
    url('^graph/(?P<pk>\d+)/', 'graph',
        name='display_indexes-graph'),
    url('^async_graph/(?P<pk>\d+)/$', 'async_graph',
        name='display_indexes-async_graph'),
    url('^async_graph_last_24h/(?P<pk>\d+)/$', 'async_graph_last_24h',
        name='display_indexes-async_graph_last_24h'),
)
