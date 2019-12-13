# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import csv
import datetime
import itertools
import string
import pytz


def parse_forecast(lines):
    """
    Parse a CO2 forecast file in the format implied by
    "20130529_CO2prognose.txt".

    @return: A dictionary with entries "date" a datetime.date, "header" the CSV
    header elements and "data" a list of (from_hour, to_hour, value) entries.

    @note: The numeric value is apparently grams of CO2 per kWh.
    """
    it = iter(lines)
    dateline = next(it).strip()
    date = datetime.datetime.strptime(dateline, '%Y%m%d').date()
    reader = csv.reader(it, delimiter=b';')
    header = tuple(next(reader))

    def parse_hour(hour_str):
        return datetime.datetime.strptime(
            hour_str.replace('24:', '00:'),
            '%H:%M').time()

    def parse_interval(interval_str):
        from_hour, to_hour = interval_str.split('-')
        return (parse_hour(from_hour), parse_hour(to_hour))

    result = [parse_interval(interval) + (int(amount),)
              for interval, amount in reader]
    return {
        'date': date,
        'header': header,
        'data': result,
    }


def parse_online(lines):
    """
    Parse an "online data" file in the format implied by
    "20130529_onlinedata.txt".

    @return: A dictionary with "header" the CSV header elements and "data" a
    list of (timestamp, value, ...) entries.

    @note: CO2 is apparently the last column/column 16, with a value in grams
    of CO2 per kWh.  (... and header "CO2 udledning".)
    """
    it = iter(lines)

    def line_not_empty(line):
        return line.strip() != b''

    # eats up to and including the blank line from iterator
    header_lines = itertools.takewhile(line_not_empty, it)
    # [' 1 Centrale kraftværker DK1', ...] ->
    # {'1': 1 Centrale kraftværker DK1'' ...}
    header_strings = dict([line.strip().split(b' ', 1)
                           for line in header_lines])

    def strip_elems(elems):
        return map(string.strip, elems)

    def drop_empty_last(elems):
        if elems[-1] == b'':
            return elems[:-1]
        else:
            return elems

    # non-CSV header lines and blank line already skipped in iterator
    reader = csv.reader(it, delimiter=b';')
    # get rid of extra whitespace inside elements
    reader = itertools.imap(strip_elems, reader)
    # get rid of whitespace after last/handle use of ; as terminator rather
    # than separator
    reader = itertools.imap(drop_empty_last, reader)

    header = next(reader)

    # Dato og tid      ;      1 ; ... ->
    # ['Dato og tid', 'Centrale kraftværker DK1', ...]
    header = (header[0],) + tuple([header_strings[nr] for nr in header[1:]])

    timezone = pytz.timezone('Europe/Copenhagen')

    def parse_line(line_items):
        try:
            timestamp = timezone.localize(
                datetime.datetime.strptime(line_items[0], '%Y-%m-%d %H:%M'),
                is_dst=True)
        except ValueError:
            # Apparently the non DST timestamps are encoded using N between the
            # hour and minutes instead of : for the single hour that is
            # ambiguous.
            timestamp = timezone.localize(
                datetime.datetime.strptime(
                    line_items[0], '%Y-%m-%d %HN%M'),
                is_dst=False)
        data = map(int, line_items[1:])
        return (timestamp,) + tuple(data)

    result = [parse_line(line_items) for line_items in reader]

    return {
        'header': header,
        'data': result,
    }
