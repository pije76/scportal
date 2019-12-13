# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.trackuser import get_customer, get_user
from django.utils import timezone


class ExceptionRemoveInfoMiddleware(object):
    """
    Remove cookies from error mails, as these contain decryption information.
    """

    def process_exception(self, request, exception):
        request.META.pop('HTTP_COOKIE', None)


class ExceptionAddInfoMiddleware(object):
    """
    Adds current user and customer to exception mail.
    """

    def process_exception(self, request, exception):
        request.META['Customer'] = get_customer()
        request.META['User'] = unicode(get_user())


class TimezoneMiddleware(object):
    """Set active timezone to the customers timezone"""
    def process_request(self, request):
        customer = get_customer()
        if customer:
            timezone.activate(customer.timezone)
