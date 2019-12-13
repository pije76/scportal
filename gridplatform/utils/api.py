# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals


def next_valid_date_for_datasequence(datasequences, date, timezone):
        """
        :return: The next date with data among given data sequences. If no
            such date exist, ``None`` is returned.

        :param datasequences: The given data sequences.
        :param date: The date to find a date after.
        :param tzinfo timezone: The timezone used to translate dates into
            timestamp ranges.
        """
        dates = [
            c.next_valid_date(date, timezone)
            for c in datasequences
            if c.next_valid_date(date, timezone)]
        if not dates:
            return None
        return min(dates)


def previous_valid_date_for_datasequence(datasequences, date, timezone):
    """
    :return: The previous date with data among given data sequences.
        If no such date exist, ``None`` is returned.

    :param datasequences: The given data sequences.
    :param date: The date to find a date before.
    :param tzinfo timezone: The timezone used to translate dates into
        timestamp ranges.
    """
    dates = [
        c.previous_valid_date(date, timezone)
        for c in datasequences
        if c.previous_valid_date(date, timezone)]
    if not dates:
        return None
    return max(dates)
