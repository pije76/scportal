# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from . import get_user, get_customer


def trackuser(request):
    """
    Provide template context variables for the current user and customer,
    obtained from the global context/user-tracking.

    With user impersonation, this user may be different from request.user.
    """
    return {
        'current_user': get_user(),
        'current_customer': get_customer(),
    }
