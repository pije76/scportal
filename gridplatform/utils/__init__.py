# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import calendar
from fractions import Fraction
from decimal import Decimal

import pytz
from django.db.models.query import QuerySet

from .decorators import deprecated
from .unitconversion import PhysicalQuantity


__all__ = ['DATETIME_MIN', 'DATETIME_MAX', 'unix_timestamp', 'deprecated']


# Shift by 24 hours to leave room for converting to any local timezone.
#
# shift by additional one year, to allow for condense.floor
DATETIME_MIN = datetime.datetime.min.replace(tzinfo=pytz.utc) + \
    datetime.timedelta(days=366)
DATETIME_MAX = datetime.datetime.max.replace(tzinfo=pytz.utc) - \
    datetime.timedelta(days=366)


def unix_timestamp(timestamp):
    """
    Convert a :class:`datetime.datetime` to a POSIX timestamp.

    :param timestamp: The :class:`datetime.datetime` to convert.  If naive,
        assumed to already be in UTC.

    :return: 1970 epoch offset in seconds, i.e. a POSIX timestamp,
        representing the timestamp given.
    """
    assert isinstance(timestamp, datetime.datetime)
    return calendar.timegm(timestamp.utctimetuple())


def first_last(iterable):
    """
    Efficiently extract the first and last element of an iterable.

    :raise ValueError: If the iterable is empty.

    :return: ``(first, last)`` where ``first`` is the first element in
        ``iterable`` and ``last`` is the last element in ``iterable``.
    """
    try:
        if isinstance(iterable, QuerySet):
            raise TypeError('QuerySet does not support negative indexing')
        first = iterable[0]
        last = iterable[-1]
    except TypeError:
        iterator = iter(iterable)
        try:
            last = first = next(iterator)
        except StopIteration:
            raise ValueError('iterable is empty')

        for last in iterator:
            pass
    except IndexError:
        raise ValueError('iterable is empty')

    return (first, last)


def fraction_to_decimal(fraction):
    """
    :return: The given :class:`~fractions.Fraction` converted to a
        :class:`~decimal.Decimal`.
    :param fraction: The given :class:`~fractions.Fraction`
    """
    if isinstance(fraction, Fraction):
        return Decimal(fraction.numerator) / fraction.denominator
    else:
        return Decimal(fraction)


def choices_extract_python_identifier(choices, db_value):
    """
    Extract the name (python identifier) of the
    :class:`model_utils.Choices` attribute that correspond to a given
    db value.

    :param choices: A :class:`model_utils.Choices` instance.
    :param db_value:  The given db value.
    :return: A python identifier that corresponds to the given db value.
    """
    for key, value in choices._identifier_map.items():
        if value == db_value:
            return key
    raise ValueError('db value %r not found in %r' % (db_value, choices))


def development_sum(datasequences, unit, from_timestamp, to_timestamp):
    """
    Function for calculating the sum of developments given a datasequence
    iterable.
    """
    values = [
        datasequence.development_sum(from_timestamp, to_timestamp)
        for datasequence
        in datasequences
    ]
    return sum(values, PhysicalQuantity(0, unit))


def sum_or_none(iterable):
    """
    Sumarize elements of ``iterable``, but return ``None`` if
    ``iterable`` is empty.
    """
    iterable = iter(iterable)
    try:
        first = next(iterable)
        return sum(iterable, first)
    except StopIteration:
        return None
