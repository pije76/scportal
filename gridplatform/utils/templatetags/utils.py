# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import json

from django import template
from django.utils.safestring import mark_safe

from gridplatform.utils import units
from gridplatform.trackuser import get_customer
from gridplatform.utils.decorators import deprecated

register = template.Library()


@register.filter
def insertnbsp(value):
    """
    Inserts four times the given value of non-breakable space and mark
    it safe.  Useful for indentation.

    :param value:  The given value.
    """
    try:
        return mark_safe('&nbsp;' * int(value) * 4)
    except TypeError:
        return ''


@register.filter
def jsonify(object):
    """
    Dump the given object as JSON and mark it safe.

    :param object:  The given object.
    """
    return mark_safe(json.dumps(object))


@register.filter
def buckingham_display(buckingham_str):
    """
    Convert a Buckingham unit to its predefiend human readable
    counterpart.

    :warning: Not all valid Buckingham units have a predefined human
        readable counterpart.
    :warning: Some Buckingham units correspond to multiple predefined
        human readable counterpart, some of which may be wrong in the
        given application.

    :deprecated: Use specializations of
        :class:`gridplatform.utils.preferredunits.UnitConverter`
        instead.  Some units need to be displayed differently
        depending on their application.
    """
    try:
        return units.UNIT_DISPLAY_NAMES[buckingham_str]
    except KeyError:
        pass
    try:
        return get_customer().get_production_unit_choices()[buckingham_str]
    except KeyError:
        pass
    return buckingham_str
