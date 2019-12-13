# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns
from django.conf.urls import url

from . import views

urlpatterns = patterns(
    'energymanager.price_relay_site.views',
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
        views.PriceRelayProjectList.as_view(),
        name='price-relay-project-list'),
    url(r'^project/content/(?P<customer_id>\d+)/$',
        views.PriceRelayProjectListContentView.as_view(),
        name='price-relay-project-list-content'),
    url(r'^project/create/(?P<customer_id>\d+)/$',
        views.PriceRelayProjectCreateView.as_view(),
        name='price-relay-project-create'),
    url(r'^project/update/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.PriceRelayProjectUpdateView.as_view(),
        name='price-relay-project-update'),
    url(r'^(?P<customer_id>\d+)/dashboard/$',
        views.PriceRelayProjectDashboardCustomerDetailView.as_view(),
        name='dashboard'),

    url(r'^project/(?P<customer_id>\d+)/start/(?P<project_id>\d+)/$',  # noqa
        views.StartTariffHourlyLineChartView.as_view(),
        name='forecast-chart-start'),
    url(r'^project/(?P<customer_id>\d+)/finalize/$',
        views.FinalizeTariffHourlyLineChartView.as_view(),
        name='forecast-chart-finalize'),
)
