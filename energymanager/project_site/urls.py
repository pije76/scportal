# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns
from django.conf.urls import url

from . import views

urlpatterns = patterns(
    'energymanager.project_site.views',
    url(r'^$',
        views.HomeView.as_view(),
        name='home'),
    url(r'^customer/(?P<customer_id>\d+)/$',
        views.CustomerView.as_view(),
        name='customer'),
    url(r'^choose-customer/$',
        views.ChooseCustomer.as_view(),
        name='choose-customer'),
    url(r'^project/(?P<customer_id>\d+)/$',
        views.EnergyProjectList.as_view(),
        name='project-list'),
    url(r'^project/content/(?P<customer_id>\d+)/$',
        views.EnergyProjectListContentView.as_view(),
        name='project-list-content'),
    url(r'^project/create/(?P<customer_id>\d+)/$',
        views.EnergyProjectCreateView.as_view(),
        name='project-create'),
    url(r'^project/update/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.EnergyProjectUpdateView.as_view(),
        name='project-update'),
    url(r'^project/delete/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.EnergyProjectDeleteView.as_view(),
        name='project-delete'),
    url(r'^project/overview/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.EnergyProjectDetailView.as_view(),
        name='project-detail'),

    url(r'^project/(?P<customer_id>\d+)/start_power/(?P<project_id>\d+)/$',  # noqa
        views.StartBaselineHourConsumptionUtilityBarChartView.as_view(),
        name='consumption-utility-bar-chart-start'),
    url(r'^project/(?P<customer_id>\d+)/start_time/(?P<project_id>\d+)/$',  # noqa
        views.StartBaselineDayliConsumptionUtilityBarChartView.as_view(),
        name='time-consumption-utility-bar-chart-start'),
    url(r'^project/(?P<customer_id>\d+)/finalize/$',
        views.FinalizeWeekUtilityBarChartView.as_view(),
        name='utility-bar-chart-finalize'),
)
