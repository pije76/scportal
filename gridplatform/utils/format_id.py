# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _


def format_mac(val, bytes=6):
    """
    Formats a given integer value as a MAC address.

    :param val: The integer value to be formatted.
    :keyword bytes: The number of bytes significant in the given
        integer value.
    """
    bytelist = []
    for _ignore in range(bytes):
        bytelist.append(val & 0xff)
        val >>= 8
    return (':'.join(['{:02x}'] * bytes)).format(*reversed(bytelist))


def format_mbus_manufacturer(val):
    """
    From section 6.3.1 in http://www.m-bus.com/mbusdoc/md6.php

    The association of three-letter-codes to manufactorers is
    available on http://dlms.com/organization/flagmanufacturesids/
    """
    charlist = []
    for _ignore in range(3):
        charlist.append(chr((val & 0x1f) + 64))
        val >>= 5
    return ''.join(reversed(charlist))


# From section 8.4.1 in
# http://www.m-bus.com/mbusdoc/md8.php
mbus_medium = {
    0x00: _(u'Other'),
    0x01: _(u'Oil'),
    0x02: _(u'Electricity'),
    0x03: _(u'Gas'),
    0x04: _(u'Heat outlet'),
    0x05: _(u'Steam'),
    0x06: _(u'Hot water'),
    0x07: _(u'Water'),
    0x08: _(u'Heat cost allocator'),
    0x09: _(u'Compressed air'),
    0x0A: _(u'Cooling load meter outlet'),
    0x0B: _(u'Cooling load meter inlet'),
    0x0C: _(u'Heat inlet'),
    0x0D: _(u'Heat/cooling load meter'),
    0x0E: _(u'Bus/system'),
    0x0F: _(u'Unknown medium'),
    # 0x10--0x15 reserved
    0x16: _(u'Cold water'),
    0x17: _(u'Dual water'),
    0x18: _(u'Pressure'),
    0x19: _(u'A/D converter'),
    # 0x20--0xff reserved
}

# 0x10--0x15 reserved
for n in range(0x10, 0x15 + 1):
    mbus_medium[n] = _('Reserved')
# 0x20--0xff reserved
for n in range(0x20, 0xff + 1):
    mbus_medium[n] = _('Reserved')


def format_mbus_enhanced(val):
    """
    Formats the information contained in a integer mbus ID in a human
    readable fashion.
    """
    return _(
        u'{id}, manufacturer: {manufacturer}, '
        'generation: {generation}, medium: {medium}').format(
            id=val >> 32,
            manufacturer=format_mbus_manufacturer((val >> 16) & 0xffff),
            generation=(val >> 8) & 0xff,
            medium=mbus_medium[val & 0xff])
