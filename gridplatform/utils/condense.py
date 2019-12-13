# -*- coding: utf-8 -*-
"""
Historically we have called time period's aggregating of samples
for condensing, and the generic description of the time periods in the
forms of :class:`.RelativeTimeDelta` for condense resolutions.  The
code and the documentation has not been cleaned up with respect to
this terminology confusion.

This module is made to be used as a namespace.  In particular most
names held within this module seem overly generic if not used with the
namespace.  For instance ``condense.ceil`` will be less confusing than
just ``ceil`` in application code.

.. data:: YEARS

    A condense resolution of one year.

.. data:: QUARTERS

    A condense resolution of a quarter year.

.. data:: MONTHS

    A condense resolution of one month.

.. data:: DAYS

    A condense resolution of one day.

.. data:: HOURS

    A condense resolution of one hour.

.. data:: FIVE_MINUTES

    A condense resolution of five minutes.

.. data:: MINUTES

    A condense resolution of one minute.

.. data:: RESOLUTIONS

    A tuple of ordered condense resolutions ``(YEARS,... , MINUTES)``.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import pytz
from django.utils.formats import date_format
from django.utils.dateformat import format
from django.utils.translation import ugettext_lazy as _

from .relativetimedelta import RelativeTimeDelta

YEARS = RelativeTimeDelta(years=1)
QUARTERS = RelativeTimeDelta(months=3)
MONTHS = RelativeTimeDelta(months=1)
DAYS = RelativeTimeDelta(days=1)
HOURS = RelativeTimeDelta(hours=1)
FIVE_MINUTES = RelativeTimeDelta(minutes=5)
MINUTES = RelativeTimeDelta(minutes=1)

RESOLUTIONS = (
    YEARS,
    QUARTERS,
    MONTHS,
    DAYS,
    HOURS,
    FIVE_MINUTES,
    MINUTES,
)


def next_resolution(resolution):
    """
    Helper method for implementing
    :meth:`legacy.measurementpoints.models.DataSeries.get_recursive_condense_resolution`.

    :param resolution: A condense resolution.

    :return: Returns a slightly more fine grained
        :class:`.RelativeTimeDelta` than ``resolution`` or ``None``.

    :raise ValueError: If ``resolution`` is not a valid condense resolution.
    """
    if resolution not in RESOLUTIONS:
        raise ValueError('%r is not a valid condense resolution' % resolution)
    if resolution == RESOLUTIONS[-1]:
        return None
    return RESOLUTIONS[
        RESOLUTIONS.index(resolution) + 1]


def is_finer_resolution(r1, r2):
    """
    :return: Returns true if ``r1`` is finer than ``r2``.
    """
    return RESOLUTIONS.index(r1) > RESOLUTIONS.index(r2)


def is_coarser_resolution(r1, r2):
    """
    :return: Returns true if ``r1`` is coarser than ``r2``.
    """
    return is_finer_resolution(r2, r1)


def floor(time_object, resolution, timezone):
    """
    Round ``time_object`` down to nearest multiple of ``resolution``
    in the given ``timezone``.

    :return: Returns a datetime object in ``timezone`` which is a multiple of
        ``resolution``.
    """
    assert resolution in RESOLUTIONS, \
        '%r is an invalid resolution' % resolution

    time_object = timezone.normalize(time_object.astimezone(timezone))

    if resolution == YEARS:
        time_object = time_object.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        adjust_timezone = True
    elif resolution == QUARTERS:
        time_object = time_object.replace(
            month=time_object.month - ((time_object.month - 1) % 3),
            day=1, hour=0, minute=0, second=0, microsecond=0)
        adjust_timezone = True
    elif resolution == MONTHS:
        time_object = time_object.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
        adjust_timezone = True
    elif resolution == DAYS:
        time_object = time_object.replace(
            hour=0, minute=0, second=0, microsecond=0)
        adjust_timezone = True
    elif resolution == HOURS:
        time_object = time_object.replace(
            minute=0, second=0, microsecond=0)
        adjust_timezone = False
    elif resolution == MINUTES:
        time_object = time_object.replace(
            second=0, microsecond=0)
        adjust_timezone = False
    elif resolution == FIVE_MINUTES:
        time_object = time_object.replace(
            minute=time_object.minute - (time_object.minute % 5),
            second=0, microsecond=0)
        adjust_timezone = False
    else:
        assert False

    if adjust_timezone and isinstance(timezone, pytz.tzinfo.BaseTzInfo):
        # normalize + localize handles edge case wrt. the timestamps with
        # two different hour # representations on DST switch...
        #
        # see test_floor_exiting_dst and test_floor_entering_dst
        time_object = timezone.localize(
            time_object.replace(tzinfo=None))

    time_object = timezone.normalize(time_object)

    return time_object


def ceil(time_object, resolution, timezone):
    """
    Round ``time_object`` up to nearest multiple of ``resolution`` in the given
    ``timezone``.

    :return: Returns a datetime object in ``timezone`` which is a multiple of
        ``resolution``.
    """
    floored = floor(time_object, resolution, timezone)
    if time_object == floored:
        return time_object
    else:
        return floored + resolution


def get_date_formatter(from_timestamp, to_timestamp, resolution=None):
    """
    Get a date formatter which given a datetime will output a string with
    sufficient information for making each tick on graphs across timespan given
    by ``from_timestamp`` and ``to_timestamp``, optionally condensed to
    ``resolution`` identifiable.

    E.g. if all samples would be on the same date, only the clock time needs to
    be displayed.  Or if all samples each represent a month, only month and
    year needs to be displayed.

    Returns a function that takes a datetime object and returns a formatted
    date/time string
    """
    if floor(from_timestamp, DAYS, from_timestamp.tzinfo) + DAYS >= \
            to_timestamp:
        # all times in the open interval between from_timestamp and
        # to_timestamp have the same date.
        return lambda timestamp: date_format(timestamp, 'TIME_FORMAT')
    elif resolution is None or resolution in (MINUTES, FIVE_MINUTES, HOURS):
        # both date and clock time is required.
        return lambda timestamp: date_format(
            timestamp, 'SHORT_DATETIME_FORMAT')
    elif resolution == DAYS:
        return lambda timestamp: date_format(timestamp, 'SHORT_DATE_FORMAT')
    elif resolution == MONTHS:
        return lambda timestamp: format(timestamp, _('M. Y'))
    elif resolution == QUARTERS:
        return lambda timestamp: format(timestamp, _('Q{quarter} Y').format(
            quarter=(timestamp.month - 1) / 3 + 1))
    elif resolution == YEARS:
        return lambda timestamp: date_format(timestamp, 'YEAR_FORMAT')

    raise ValueError(
        'no preferred date format for from_timestamp=%r, to_timestamp=%r and '
        'resolution=%r' % (from_timestamp, to_timestamp, resolution))
