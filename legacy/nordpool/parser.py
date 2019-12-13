# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Parsing of the weekly spot price format from NordPool.

The file format specification is available at:
ftp://ftp.nordpoolspot.com/Information/File_specifications/SPOT-eng.DOC
While not explicitly described, lines starting with # are comment lines.
Comment lines are still counted in the "total number of lines".

Prices may be "preliminary" or "official".  In both cases, final prices in EUR
are known --- prices in other currencies are "preliminary" until exact exchange
rates are known.  This is explained at:
ftp://ftp.nordpoolspot.com/Information/File_specifications/
Preliminary%20vs.%20official%20Elspot%20prices%20on%20NPS%20FTP-server.doc

Time is in local time, including DST.
On switch to DST: Entry for "missing" hour empty.
On switch from DST: Use same entry for both instances of "repeated" hour.

Prices are per MWh.
"""

import csv
import datetime
from decimal import Decimal
from collections import defaultdict


def parse_lines(lines):
    """
    Parse the semicolon-separated Nordpool file format and separate lines by
    their "data type" field.  Apart from all starting with a "data type" field,
    fields are specific to each data type; the specifics of those is not
    handled here.

    @type lines: string list
    @param lines: Lines from a spot price file.
    @rtype: dictionary from strings to lists of lists of strings
    @return: A dictionary from "data type" values to lists of per-line field
             lists, containing the fields apart from "data type".
    """
    linecount = len(lines)
    datalines = [l for l in lines if l[0] != b'#']
    reader = csv.reader(datalines, delimiter=b';', quoting=csv.QUOTE_NONE)
    data = defaultdict(list)
    for line in reader:
        datatype = line[0]
        content = line[1:]
        data[datatype].append(content)
    # simple consistency check; AL specifies total number of lines in file
    assert int(data['AL'][0][0]) == linecount
    return data


def extract_prices(data, area, currency):
    """
    Pulls prices for specified area and in specified currency out of a data
    dictionary as extracted from a Nordpool spot file.

    @type data: dictionary from strings to lists of lists of strings
    @param data: A data dictionary created from a Nordpool spot price file.
    @type area: string
    @param area: Nordpool pricing area to include.
    @type currency: string
    @param currency: Currency to include.
    @rtype: (datetime.date, decimal.Decimal list) list
    @return: A list of (date, hourly_price) tuples.
    """
    preliminary = []
    final = []

    def decimal_or_none(pricestr):
        if pricestr == '':
            return None
        else:
            return Decimal(pricestr.replace(',', '.'))
    for price in data['PR']:
        code, _year, _week, _weekday, date, alias, unit = price[:7]
        if alias != area or unit != currency:
            continue
        hourly = price[7:-1]
        hourly = map(decimal_or_none, hourly)
        # _average = price[-1]
        date = datetime.datetime.strptime(date, "%d.%m.%Y").date()
        if code == 'SF':
            preliminary.append((date, hourly))
        elif code == 'SO':
            final.append((date, hourly))
    return (preliminary, final)


def localized_hours(date, timezone):
    """
    Constructs localised C{datetime.datetime} objects for each hour in the
    given day; starting at midnight local time, ending at the hour before
    midnight on the next calendar day.  This takes DST into account, meaning
    that a "day" may consist of 23, 24 or 25 hours.

    @param date: Date to get hours for.
    @param timezone: A L{pytz.timezone} to compute hours in/for.
    @return: The list of C{datetime.datetime} objects.
    """
    start_hour = timezone.localize(
        datetime.datetime.combine(date, datetime.time()))
    # usually 24 hours, but 23 or 25 on DST-switch
    hours = [timezone.normalize(start_hour + datetime.timedelta(hours=n))
             for n in range(25)]
    return [hour for hour in hours if hour.date() == date]


def day_entries(date, hourly, timezone):
    """
    Combines date and hourly prices, nominally obtained by parsing a Nordpool
    spot price file, to get (from_timestamp, to_timestamp, value)-tuples that
    may be directly used in constructing L{legacy.indexes.models.Entry}
    objects.

    Takes DST and the data format wrt. those into account.

    @param date: Date to construct entries for.
    @param hourly: Hourly price entries.  Assumed to match the L{date}.
    @return: A list of (from_timestamp, to_timestamp, value)-tuples; with
             localised C{datetime.datetime} objects, sorted by time, each with
             a period of one hour and within the calendar day specified; in
             total covering the specified day.
    """
    hours = localized_hours(date, timezone)
    one_hour = datetime.timedelta(hours=1)
    # This implicitly handles DST-switch correctly wrt. the input data format:
    # Will not access the non-existent hour on switch to DST, will access the
    # repeating hour twice on switch to standard time.
    return [(hour, timezone.normalize(hour + one_hour), hourly[hour.hour])
            for hour in hours]
