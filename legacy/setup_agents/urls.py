# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from gridplatform.users.decorators import admin_or_redirect


urlpatterns = patterns(
    'legacy.setup_agents.views',
    url(r'^$',
        admin_or_redirect(TemplateView.as_view(
            template_name='setup_agents/agent_list.html')),
        name='setup_agents-list'),
    url(r'^json/agent/$', 'agent_list_json', name='setup_agents-list-json'),
    url(r'^agent/form/$', 'agent_form', name="setup_agents-form"),
    url(r'^agent/form/(?P<pk>\d+)/$', 'agent_form', name="setup_agents-form"),
    url(r'^agent/update/$', 'agent_update', name="setup_agents-update"),
    url(r'^agent/update/(?P<pk>\d+)/$',
        'agent_update',
        name="setup_agents-update"),
    url(r'^agent/swupgrade/(?P<pk>\d+)/$',
        'agent_swupgrade',
        name="setup_agents-swupgrade"),
)
