# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def tab_li(context, text, urlname, *args, **kwargs):
    """
    Construct list-item code for a tab --- marking any tab linking to the
    current URL as active.

    Usage::

        {% trans 'Meters' as meters %}
        <ul class="tabs">
          {% tab_li meters 'manage_devices-meter-list' %}
          ...
        </ul>

    @note: Text/title translation is not done by C{tab_li} --- a lot of effort
    would have to be spent on integrating it with the code for extracting
    strings to be translated from Django templates...
    """
    url = reverse(urlname, args=args, kwargs=kwargs)
    request = context['request']
    if url == request.path:
        return '<li class="selected"><a href="%s">%s</a></li>' % (
            url, text)
    else:
        return '<li><a href="%s">%s</a></li>' % (
            url, text)
