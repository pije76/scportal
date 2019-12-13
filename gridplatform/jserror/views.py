# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import json

from django.core.mail import mail_admins
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from gridplatform.trackuser import get_customer


@require_POST
def jserror(request):
    """
    Format an error from JavaScript and send it to settings.ADMINS --- where
    normal server errors are sent.

    Expects to receive a JSON dictionary with keys "errorMsg", "url" and
    "lineNumber" from the client.  "Invalid" requests --- non-JSON data,
    expected keys not present --- are ignored.
    """
    try:
        data = json.loads(request.body)
        context = {
            'message': data['message'],
            'url': data['url'],
            'line': data['line'],
            'location': data['location'],
            'customer': get_customer(),
            'user': request.user,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
    except (ValueError, KeyError):
        pass
    else:
        text = render_to_string('jserror/mail.txt', context)
        mail_admins('JS ERROR', text)
    return HttpResponse()
