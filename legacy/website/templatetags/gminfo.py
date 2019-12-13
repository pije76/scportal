# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module defines Django template tags for showing versions.
"""

from django import template
from django.conf import settings


register = template.Library()


@register.simple_tag
def gridmanager_info():
    """
    Display GridManager information
    """
    return settings.GRIDMANAGER_ADDRESS.replace('\n', '<br>')
