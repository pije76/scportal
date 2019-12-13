# -*- coding: utf-8 -*-
"""
Pagination framework for resources grouped by date rather than
pages.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from rest_framework.exceptions import APIException
from rest_framework import status
from django.http import Http404


def parse_date(date_string):
    """
    Parse date from a string.

    :param date_string:  The string to parse.

    :see: :func:`.parse_date_or_404` for a version suitable for
        parsing date strings in URLs.
    """
    if isinstance(date_string, datetime.date):
        return date_string
    else:
        return datetime.datetime.strptime(date_string, '%Y-%m-%d').date()


class Http404ApiException(Http404, APIException):
    """
    Causes an HTTP 404 response for normal django views, and the same but with
    error detail message for REST views.
    """
    status_code = status.HTTP_404_NOT_FOUND


def parse_date_or_404(date_string):
    """
    Parse date from a string.

    :param date_string:  The string to parse.

    :raise Http404ApiException: if no date could be parsed.
    """
    try:
        return parse_date(date_string)
    except ValueError:
        raise Http404ApiException(
            detail='invalid date string "%s"' % date_string)
