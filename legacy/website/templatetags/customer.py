# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import template
from gridplatform.trackuser import get_user, get_customer

register = template.Library()


@register.simple_tag
def customer_name():
    if get_customer():
        return get_customer().name_plain
    else:
        return ""


@register.simple_tag
def username():
    return get_user().e_mail_plain
