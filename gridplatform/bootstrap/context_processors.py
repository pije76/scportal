# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from .conf import settings


def bootstrap(request):
    """
    Provide template context variable boostrap_template for identifying what
    theme is currently being used. This is needed in boostrap/base.html to load
    the correct js and css files.
    """
    return {
        'bootstrap_theme': settings.BOOTSTRAP_THEME,
    }
