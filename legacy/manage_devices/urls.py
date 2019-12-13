# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    'legacy.manage_devices.views',
    url(r'^$',
        'agent_list',
        name='manage_devices-list'),
    url(r'^meters/$',
        'meter_list',
        name='manage_devices-meter-list'),
    url(r'^json/agent/$',
        'agent_list_json',
        name='manage_devices-agent-list-json'),
    url(r'^agent/form/(?P<pk>\d+)/$',
        'agent_form',
        name='manage_devices-agent-form'),
    url(r'^agent/update/(?P<pk>\d+)/$',
        'agent_update',
        name='manage_devices-agent-update'),
    url(r'^json/meter/$',
        'meter_list_json',
        name='manage_devices-meter-list-json'),
    url(r'^meter/update/(?P<pk>\d+)/$',
        views.MeterUpdateView.as_view(),
        name='manage_devices-meter-update'),
    url(r'^meter/(?P<meter>\d+)/input/(?P<pk>\d+)/update$',
        views.pulseconversion_update,
        name='manage_devices-pulseconversion-update'),
    url(r'^meter/(?P<meter>\d+)/input/(?P<physicalinput>\d+)/electricity$',
        views.ElectricityConsumptionCreateView.as_view(),
        name='manage_devices-pulseconversion-electricity-create'),
    url(r'^meter/(?P<meter>\d+)/input/(?P<pk>\d+)/electricity/update$',
        views.ElectricityConsumptionUpdateView.as_view(),
        name='manage_devices-pulseconversion-electricity-update'),

    url(r'^meter/(?P<meter>\d+)/input/(?P<physicalinput>\d+)/water$',
        views.WaterConsumptionCreateView.as_view(),
        name='manage_devices-pulseconversion-water-create'),
    url(r'^meter/(?P<meter>\d+)/input/(?P<pk>\d+)/water/update$',
        views.WaterConsumptionUpdateView.as_view(),
        name='manage_devices-pulseconversion-water-update'),

    url(r'^meter/(?P<meter>\d+)/input/(?P<physicalinput>\d+)/district_heating$',  # noqa
        views.DistrictHeatingConsumptionCreateView.as_view(),
        name='manage_devices-pulseconversion-district_heating-create'),
    url(r'^meter/(?P<meter>\d+)/input/(?P<pk>\d+)/district_heating/update$',
        views.DistrictHeatingConsumptionUpdateView.as_view(),
        name='manage_devices-pulseconversion-district_heating-update'),

    url(r'^meter/(?P<meter>\d+)/input/(?P<physicalinput>\d+)/gas$',
        views.GasConsumptionCreateView.as_view(),
        name='manage_devices-pulseconversion-gas-create'),
    url(r'^meter/(?P<meter>\d+)/input/(?P<pk>\d+)/gas/update$',
        views.GasConsumptionUpdateView.as_view(),
        name='manage_devices-pulseconversion-gas-update'),

    url(r'^meter/(?P<meter>\d+)/input/(?P<physicalinput>\d+)/oil$',
        views.OilConsumptionCreateView.as_view(),
        name='manage_devices-pulseconversion-oil-create'),
    url(r'^meter/(?P<meter>\d+)/input/(?P<pk>\d+)/oil/update$',
        views.OilConsumptionUpdateView.as_view(),
        name='manage_devices-pulseconversion-oil-update'),

    url(r'^meter/(?P<meter>\d+)/input/(?P<physicalinput>\d+)/(?P<production_unit>production_[a-z])$',  # noqa
        views.ProductionCreateView.as_view(),
        name='manage_devices-pulseconversion-production-create'),
    url(r'^meter/(?P<meter>\d+)/input/(?P<pk>\d+)/production/update$',
        views.ProductionUpdateView.as_view(),
        name='manage_devices-pulseconversion-production-update'),

    url(r'^meter/switch_relay/(?P<pk>\d+)/$',
        'meter_relay',
        name='manage_devices-meter-relay'),
    url(r'^meter/switch_relay/(?P<pk>\d+)/(?P<action>on|off)/$',
        'meter_relay_toggle',
        name='manage_devices-meter-relay-toggle'),
    url(r'^meter/relay_state/(?P<pk>\d+)/$',
        'meter_relay_state',
        name='manage_devices-meter-relay-state'),
)
