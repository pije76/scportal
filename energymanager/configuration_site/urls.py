# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns
from django.conf.urls import url
from django.conf.urls import include

from gridplatform.utils.urls import restricted_url

from . import views

urlpatterns = patterns(
    'energymanager.configuration_site_view.views',
    url(r'^$',
        views.HomeView.as_view(),
        name='home'),
    url(r'^customer/(?P<customer_id>\d+)/$',
        views.CustomerView.as_view(),
        name='customer'),
    url(r'^choose-customer/$',
        views.ChooseCustomer.as_view(),
        name='choose-customer'),

    url(r'^customerdatasource/(?P<customer_id>\d+)/$',
        views.CustomerDataSourceList.as_view(),
        name='customer-datasource-list'),
    url(r'^customerdatasource/content/(?P<customer_id>\d+)/$',
        views.CustomerDataSourceListContentView.as_view(),
        name='customer-datasource-list-content'),
    url(r'^customerdatasource/create/(?P<customer_id>\d+)/$',
        views.CustomerDataSourceCreateView.as_view(),
        name='customer-datasource-create'),
        url(r'^customerdatasource/update/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.CustomerDataSourceUpdateView.as_view(),
        name='customer-datasource-update'),
    url(r'^customerdatasource/delete/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.CustomerDataSourceDeleteView.as_view(),
        name='customer-datasource-delete'),

    url(r'^consumption/(?P<customer_id>\d+)/$',
        views.ConsumptionList.as_view(),
        name='consumption-list'),
    url(r'^consumption/content/(?P<customer_id>\d+)/$',
        views.ConsumptionListContentView.as_view(),
        name='consumption-list-content'),
    url(r'^consumption/detail/(?P<customer_id>\d+)/'
        r'(?P<pk>\d+)/$',
        views.ConsumptionDetailView.as_view(),
        name='consumption-detail'),
    url(r'^consumption/create/(?P<customer_id>\d+)/$',
        views.ConsumptionCreateView.as_view(),
        name='consumption-create'),
    url(r'^consumption/update/(?P<customer_id>\d+)/'
        r'(?P<pk>\d+)/$',
        views.ConsumptionUpdateView.as_view(),
        name='consumption-update'),
    url(r'^consumption/delete/(?P<customer_id>\d+)/'
        r'(?P<pk>\d+)/$',
        views.ConsumptionDeleteView.as_view(),
        name='consumption-delete'),

    url(r'^consumption/(?P<customer_id>\d+)/'
        r'(?P<datasequence_id>\d+)/nonpulseperiod/create/$',
        views.ConsumptionNonpulsePeriodCreateView.as_view(),
        name='consumptionnonpulseperiod-create'),
    url(r'^consumption/(?P<customer_id>\d+)/'
        r'(?P<datasequence_id>\d+)/nonpulseperiod/update/'
        r'(?P<pk>\d+)/$',
        views.ConsumptionNonpulsePeriodUpdateView.as_view(),
        name='consumptionnonpulseperiod-update'),
    url(r'^nonpulseperiod/(?P<customer_id>\d+)/delete/'
        r'(?P<pk>\d+)/$',
        views.ConsumptionNonpulsePeriodDeleteView.as_view(),
        name='consumptionnonpulseperiod-delete'),

    url(r'^consumption/(?P<customer_id>\d+)/start/(?P<consumption_id>\d+)/$',  # noqa
        views.StartWeekConsumptionUtilityBarChartView.as_view(),
        name='consumption-utility-bar-chart-start'),
    url(r'^consumption/(?P<customer_id>\d+)/finalize/$',
        views.FinalizeWeekUtilityBarChartView.as_view(),
        name='utility-bar-chart-finalize'),

    url(r'^tariff/(?P<customer_id>\d+)/$',
        views.TariffList.as_view(),
        name='tariff-list'),
    url(r'^tariff/content/(?P<customer_id>\d+)/$',
        views.TariffListContentView.as_view(),
        name='tariff-list-content'),
    url(r'^tariff/create/(?P<customer_id>\d+)/$',
        views.TariffCreateView.as_view(),
        name='tariff-create'),
    url(r'^tariff/update/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.TariffUpdateView.as_view(),
        name='tariff-update'),

    url(r'^agent/(?P<customer_id>\d+)/$',
        views.AgentList.as_view(),
        name='agent-list'),
    url(r'^agent/content/(?P<customer_id>\d+)/$',
        views.AgentListContentView.as_view(),
        name='agent-list-content'),
    url(r'^agent/create/(?P<customer_id>\d+)/$',
        views.AgentCreateView.as_view(),
        name='agent-create'),
    url(r'^agent/update/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.AgentUpdateView.as_view(),
        name='agent-update'),

    url(r'^meter/(?P<customer_id>\d+)/$',
        views.MeterList.as_view(),
        name='meter-list'),
    url(r'^meter/content/(?P<customer_id>\d+)/$',
        views.MeterListContentView.as_view(),
        name='meter-list-content'),
    url(r'^meter/create/(?P<customer_id>\d+)/$',
        views.MeterCreateView.as_view(),
        name='meter-create'),
    url(r'^meter/update/(?P<customer_id>\d+)/(?P<pk>\d+)/$',
        views.MeterUpdateView.as_view(),
        name='meter-update'),
)
