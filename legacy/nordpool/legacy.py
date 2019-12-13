# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import itertools

from isoweek import Week

from legacy.indexes.models import SpotMapping
from gridplatform.utils import condense
from gridplatform.utils.relativetimedelta import RelativeTimeDelta

from . import ftpclient
from . import parser


def update_entries(from_date, to_date, index, preliminary, final, timezone):
    entry_qs = index.entry_set.filter(
        from_timestamp__gte=from_date,
        from_timestamp__lt=to_date)
    existing_entries = {entry.from_timestamp: entry for entry in entry_qs}
    final_dates = set([date for date, hourly in final])
    preliminary_entries = []
    for date, hourly in preliminary:
        if date not in final_dates:
            preliminary_entries.extend(
                parser.day_entries(date, hourly, timezone))
    final_entries = []
    for date, hourly in final:
        final_entries.extend(parser.day_entries(date, hourly, timezone))
    for from_timestamp, to_timestamp, value in itertools.chain(
            preliminary_entries, final_entries):
        if value is None:
            # As of October 19th 2014 Nordpool started to document the prices
            # using 25 hours for each day, to (in their opinion) better support
            # the one day every year where 03:00 is two hours long. They could
            # of course just have documented hourly prices with UTC timestamps
            # and thus have completely avoided the daylight savings issues!
            # Nordpool news about the format change:
            # http://www.nordpoolspot.com/TAS/Power-Data-Services/PDS-news/
            continue
        if from_timestamp in existing_entries:
            entry = existing_entries[from_timestamp]
            assert entry.from_timestamp == from_timestamp
            assert entry.to_timestamp == to_timestamp
            if entry.value != value:
                entry.value = value
                entry.save()
        else:
            index.entry_set.create(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                value=value)


def import_week(data):
    year, week, _day, _hour, _total_hours, _clock, _date = data['ST'][0]
    year = int(year)
    week = int(week)
    naive_week_start = datetime.datetime.combine(
        Week(year, week).monday(), datetime.time())
    naive_week_end = datetime.datetime.combine(
        naive_week_start + datetime.timedelta(days=7), datetime.time())
    for mapping in SpotMapping.objects.all().select_related('index'):
        tz = mapping.timezone
        week_start = tz.localize(naive_week_start)
        week_end = tz.localize(naive_week_end)
        preliminary, final = parser.extract_prices(
            data, mapping.area, mapping.currency)
        update_entries(week_start, week_end, mapping.index,
                       preliminary, final, mapping.timezone)


def fetch_import_week(year, week):
    lines = ftpclient.fetch_spot(year, week)
    data = parser.parse_lines(lines)
    import_week(data)


def prices_today():
    prices_exists = []
    for mapping in SpotMapping.objects.all().select_related('index'):
        today = condense.floor(
            datetime.datetime.now(mapping.timezone),
            condense.DAYS,
            mapping.timezone)
        tomorrow = today + RelativeTimeDelta(days=1)
        prices_exists.append(mapping.index.entry_set.filter(
            from_timestamp__gt=today, to_timestamp__lt=tomorrow).exists())
    return all(prices_exists)
