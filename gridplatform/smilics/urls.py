# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

urlpatterns = patterns(
    'gridplatform.smilics.views',
    url(r'^receiver$',
        'wibeee_receiver',
        name='smillics-wibeee-reciver'),
    url(r'^receiverJSON$',
        'wibeee_receiver_json',
        name='smillics-wibeee-reciver-json'),
)
