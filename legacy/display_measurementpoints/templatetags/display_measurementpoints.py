# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import template
from django.template.defaultfilters import floatformat
from django.utils.translation import ugettext as _


register = template.Library()


@register.filter(is_safe=True)
def physicalquantity(physical_quantity, decimals):
    """
    Formats a physical quantity nicely.

    @param physical_quantity: A two-tuple C{(n, u)} where C{n} is number to be
    displayed.  and C{u} is a localized unit name.

    @param decimals: The number of decimals that should be displayed.  Use
    negative values to indicate that right-most zeroes must be
    discarded. (similar to floatformat filter)

    @precondition: decimals <= 12, because the underlying library will truncate
    and replace additional decimals with 0.

    @note: This method is not intended to format a PhysicalQuantity instance
    directly.  The application is responsible for converting the
    PhysicalQuantity to the right unit, decide how many decimals are needed,
    and provide a localized unit.

    @note: The name of this method follows a convention of Emacs Django
    template mode, where filters may not contain underscore.
    """
    assert int(decimals) <= 12, \
        'successive decimals will be 0, regardless of their value'
    return _(u'{numeric_quantity} {unit_name}').format(
        numeric_quantity=floatformat(physical_quantity[0], decimals),
        unit_name=physical_quantity[1])
