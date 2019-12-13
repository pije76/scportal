# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.views.generic import TemplateView, DetailView

from gridplatform.users.decorators import admin_or_redirect
from gridplatform.customers.models import Customer


urlpatterns = patterns(
    'legacy.manage_customers.views',
    url(r'^as_customer/(?P<pk>\d+)/$',
        'as_customer',
        name='manage_customers-as_customer'),
    url(r'^as_admin/$',
        'as_admin',
        name='manage_customers-as_admin'),
    # customers
    url(r'^$',
        admin_or_redirect(TemplateView.as_view(
            template_name='manage_customers/customer_list.html')),
        name='manage_customers-list'),
    url(r'^json/customer/$',
        'customer_list_json',
        name='manage_customers-list-json'),
    url(r'^customer/create/$',
        'customer_form',
        name='manage_customers-create'),
    url(r'^customer/form/(?P<pk>\d+)/$',
        'customer_form',
        name="manage_customers-form"),
    url(r'^customer/update/(?P<pk>\d+)/$',
        'customer_update',
        name="manage_customers-update"),
    url(r'^customer/update/$',
        'customer_update',
        name="manage_customers-update"),
    url(r'^customer/(?P<pk>\d+)/$',
        admin_or_redirect(DetailView.as_view(
            model=Customer,
            template_name='manage_customers/customer_detail.html')),
        name="manage_customers-detail"),
    # customer agents
    url(r'^customer/(?P<customer>\d+)/agent/$',
        'customer_agent_list',
        name="manage_customers-agent-list"),
    url(r'^customer/(?P<customer>\d+)/json/agent/$',
        'customer_agent_list_json',
        name="manage_customers-agent-list-json"),
    # customer meters
    url(r'^customer/(?P<customer>\d+)/meter/$',
        'customer_meter_list',
        name="manage_customers-meter-list"),
    url(r'^customer/(?P<customer>\d+)/json/meter/$',
        'customer_meter_list_json',
        name="manage_customers-meter-list-json"),
)
