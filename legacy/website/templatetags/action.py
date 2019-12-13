# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag
def action(urlname, instance, *args, **kwargs):
    """
    Returnes the url for the action based on wether it's a create or update

    @ivar urlname: The name of the view.

    @ivar instance: An instance

    Usage: {% action 'manage-groups-update' form.instance pk=group.id %}
    """
    if instance.id is not None:
        url = reverse(urlname, args=args, kwargs=kwargs)
    else:
        url = reverse(urlname)

    return url
