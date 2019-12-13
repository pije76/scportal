# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns
from django.conf.urls import url

from . import views

urlpatterns = patterns(
    'energymanager.led_light_view.views',
    url(r'^project/(?P<customer_id>\d+)/$',
        views.LedLightProjectList.as_view(),
        name='led-light-project-list'),
    url(r'^project/content/(?P<customer_id>\d+)/$',
        views.LedLightProjectListContentView.as_view(),
        name='led-light-project-list-content'),
    url(r'^project/create/(?P<customer_id>\d+)/$',
        views.LedLightProjectCreateView.as_view(),
        name='led-light-project-create'),
    url(r'^project/update/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.LedLightProjectUpdateView.as_view(),
        name='led-light-project-update'),
    url(r'^project/delete/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.LedLightProjectDeleteView.as_view(),
        name='led-light-project-delete'),
    url(r'^(?P<customer_id>\d+)/dashboard_burn/$',
        views.DashboardBurnDetailView.as_view(),
        name='dashboard_burn'),
)
