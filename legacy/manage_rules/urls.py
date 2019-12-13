# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.views.generic import TemplateView


urlpatterns = patterns(
    'legacy.manage_rules.views',
    url(r'^$', TemplateView.as_view(
        template_name='manage_rules/rule_list.html'),
        name='manage_rules-list'),
    url(r'^json/rule/$',
        'rule_list_json',
        name='manage_rules-list-json'),
    url(r'^form/(?P<pk>\d+)$',
        'form',
        name='manage_rules-form'),
    url(r'^minimizerule/$',
        'minimizerule_form',
        name='manage_rules-minimizerule_form'),
    url(r'^minimizerule/(?P<pk>\d+)$',
        'minimizerule_form',
        name='manage_rules-minimizerule_form'),
    url(r'^triggeredrule/$',
        'triggeredrule_form',
        name='manage_rules-triggeredrule_form'),
    url(r'^triggeredrule/(?P<pk>\d+)$',
        'triggeredrule_form',
        name='manage_rules-triggeredrule_form'),
    url(r'^delete/$',
        'delete',
        name='manage_rules-delete'),
)
