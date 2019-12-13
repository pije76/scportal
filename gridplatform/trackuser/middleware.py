# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils import timezone

from gridplatform.customers.models import Customer

from . import _store
from . import get_customer
from . import get_timezone


class TrackUserMiddleware(object):
    """
    Middleware to keep track of the current user during processing of a
    request.  Useful for making it available to model member methods; e.g::

        customer = models.ForeignKey(
            Customer, editable=False, default=trackuser.get_customer)

    However, for such uses see also :class:`EncryptionCustomerFieldMixin`.

    Also makes "current customer" available as property on request/session, and
    sets "current timezone" to the customer timezone.
    """
    def process_request(self, request):
        user = request.user
        _store.user = user
        # NOTE: "Log in as customer" fearture; to be removed.
        override_customer_id = request.session.get('customer_id', None)
        if override_customer_id is not None:
            try:
                override_customer = Customer.objects.get(
                    id=override_customer_id)
            except Customer.DoesNotExist:
                override_customer = None
        else:
            override_customer = None
        _store.override_customer = override_customer
        # NOTE: customer on request --- used in Portal 2 code; to be removed
        request.customer = get_customer()
        customer_timezone = get_timezone()
        if customer_timezone is not None:
            timezone.activate(customer_timezone)
        else:
            timezone.deactivate()
        return None

    def process_response(self, request, response):
        _store.user = None
        _store.override_customer = None
        _store.selected_customer = None
        timezone.deactivate()
        return response
