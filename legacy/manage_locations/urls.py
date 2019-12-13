# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.views.generic import TemplateView, DetailView

from legacy.measurementpoints.models import Location
from gridplatform.users.decorators import auth_or_redirect


urlpatterns = patterns(
    'legacy.manage_locations.views',
    url(r'^$',
        auth_or_redirect(TemplateView.as_view(
            template_name='manage_locations/location_list.html')),
        name='manage-locations-list'),
    url(r'^form/$',
        'location_form',
        name='manage-locations-form'),
    url(r'^form/(?P<pk>\d+)$',
        'location_form',
        name='manage-locations-form'),
    url(r'^json/locations/$',
        'location_list_json',
        name='manage-locations-list-json'),
    url(r'^update/$',
        'location_update',
        name='manage-locations-update'),
    url(r'^update/(?P<pk>\d+)$',
        'location_update',
        name='manage-locations-update'),
    url(r'^delete/$',
        'location_delete',
        name='manage-locations-delete'),
    url(r'^(?P<pk>\d+)$',
        auth_or_redirect(DetailView.as_view(
            model=Location,
            template_name='manage_locations/location_details.html')),
        name='manage-locations-details'),
    url(r'^json/agent/(?P<location>\d+)$',
        'agent_list_json',
        name='manage-locations-agent-list-json'),
    url(r'^json/meter/(?P<location>\d+)$',
        'meter_list_json',
        name='manage-locations-meter-list-json'),
)
