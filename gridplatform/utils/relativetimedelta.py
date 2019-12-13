# -*- coding: utf-8 -*-
"""
This module defines the :class:`.RelativeTimeDelta` class, which
deprecates :class:`dateutil.relativedelta` and does what we always
wished that :class:`datetime.timedelta` did.

.. data:: DATETIME_MIN

    A largest lower bound for timezone aware datetimes.

.. data:: DATETIME_MAX

    A least upper bound for timezone aware datetimes.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from dateutil.relativedelta import relativedelta
import pytz

from . import DATETIME_MIN, DATETIME_MAX

__all__ = ['RelativeTimeDelta', 'DATETIME_MIN', 'DATETIME_MAX']


def wrap(attr):
    """
    Wrap operator methods of
    :class:`dateutil.relativedelta.relativedelta` so that they return
    a :class:`.RelativeTimeDelta` instance where they would otherwise
    return a :class:`dateutil.relativedelta.relativedelta` instance.
    And otherwise ensure that daylight saving time is handled as one
    would expect.

    :see: :class:`.RelativeTimeDelta`
    """
    def wrapper(self, other):
        method = getattr(super(RelativeTimeDelta, self), attr)
        if isinstance(other, datetime.date) and \
                isinstance(other.tzinfo, pytz.tzinfo.BaseTzInfo):
            tzinfo = other.tzinfo
            if self.years != 0 or self.months != 0 or self.days != 0:
                # normalize + localize handles edge case wrt. the
                # timestamps with two different hour representations
                # on DST switch...
                return tzinfo.normalize(
                    tzinfo.localize(method(other.replace(tzinfo=None))))
            else:
                return tzinfo.normalize(method(other))

        res = method(other)
        if isinstance(res, relativedelta):
            res.__class__ = self.__class__
        return res
    return wrapper


class RelativeTimeDelta(relativedelta):
    """
    Timezone aware :class:`dateutil.relativedelta.relativedetla`
    specialization.

    :class:`datetime.timedelta` thinks that timespans are always a
    number of seconds.  This ofcourse does not hold for timespans such
    as days, months, and years.

    :class:`dateutil.relativedelta.relativedelta` almost got it right, although
    it thinks that timespans are not needed across daylight saving
    time transitions, i.e. a month after march 1st 00:00:00 is
    ofcourse april 1st 01:00:00.

    The :class:`.RelativeTimeDelta` class deprecates
    :class:`dateutil.relativedelta.relativedelta`.
    """

    __add__ = wrap("__add__")
    __radd__ = wrap("__radd__")
    __sub__ = wrap("__sub__")
    __rsub__ = wrap("__rsub__")
    __mul__ = wrap("__mul__")
    __rmul__ = wrap("__rmul__")
    __div__ = wrap("__div__")

    def __neg__(self):
        res = super(RelativeTimeDelta, self).__neg__()
        res.__class__ = self.__class__
        return res

    def __hash__(self):
        return hash((self.hours, self.days, self.months, self.year))
