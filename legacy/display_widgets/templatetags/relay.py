# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static

register = template.Library()


@register.simple_tag
def relay_image(meter):
    if meter:
        agent = meter.agent
        if not agent.online:
            return '<img src="' + static('images/relay_offline.png') + \
                '" height="16" width="16" class="relayStatus">'
        state = 'relay_off.png'
        if meter.relay_on:
            state = 'relay_on.png'
        return '<img src="' + static('images/' + state) + \
            '" height="16" width="16" class="relayStatus">'
    else:
        return '<img src="' + static('images/transparent.png') + \
            '" height="16" width="16" class="relayStatus">'
