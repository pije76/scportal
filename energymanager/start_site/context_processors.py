# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.trackuser import get_user

from .views import applist


def app_selection(request):
    """
    Provide template context variable app_selection to make the list of apps
    that the current user has access to avaiable in all templates.
    """
    return {
        'app_selection': applist(request, get_user()),
    }
