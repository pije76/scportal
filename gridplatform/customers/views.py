# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.functional import cached_property


class GetObjectCustomerMixin(object):
    @cached_property
    def _customer(self):
        return self.get_object().customer
