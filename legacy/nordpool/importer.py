# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import itertools

from isoweek import Week
import pytz

from gridplatform.global_datasources.models import GlobalDataSource
from gridplatform.utils.unitconversion import PhysicalQuantity

from . import ftpclient
from . import parser


def update_rawdata(
        from_timestamp, to_timestamp, datasource, preliminary, final,
        timezone, nordpool_unit, unit):
    rawdata_qs = datasource.rawdata_set.filter(
        timestamp__gte=from_timestamp,
        timestamp__lt=to_timestamp)
    existing_rawdata = {rawdata.timestamp: rawdata for rawdata in rawdata_qs}
    final_dates = set([date for date, hourly in final])
    preliminary_rawdata = []
    for date, hourly in preliminary:
        if date not in final_dates:
            preliminary_rawdata.extend(
                parser.day_entries(date, hourly, timezone))
    final_rawdata = []
    for date, hourly in final:
        final_rawdata.extend(parser.day_entries(date, hourly, timezone))
    for from_ts, to_ts, value in itertools.chain(preliminary_rawdata,
                                                 final_rawdata):
        if value is None:
            # As of October 19th 2014 Nordpool started to document the prices
            # using 25 hours for each day, to (in their opinion) better support
            # the one day every year where 03:00 is two hours long. They could
            # of course just have documented hourly prices with UTC timestamps
            # and thus have completely avoided the daylight savings issues!
            # Nordpool news about the format change:
            # http://www.nordpoolspot.com/TAS/Power-Data-Services/PDS-news/
            continue
        if from_ts in existing_rawdata:
            rawdata = existing_rawdata[from_ts]
            assert rawdata.timestamp == from_ts
            rawdata.value = \
                int(PhysicalQuantity(value, nordpool_unit).convert(unit))
            rawdata.save()
        else:
            datasource.rawdata_set.create(
                timestamp=from_ts,
                value=int(
                    PhysicalQuantity(value, nordpool_unit).convert(unit)))


def import_week(data, spotprices):
    year, week, _day, _hour, _total_hours, _clock, _date = data['ST'][0]
    year = int(year)
    week = int(week)
    naive_week_start = datetime.datetime.combine(
        Week(year, week).monday(), datetime.time())
    naive_week_end = datetime.datetime.combine(
        naive_week_start + datetime.timedelta(days=7), datetime.time())
    for spotprice in spotprices:
        datasource = GlobalDataSource.objects.get(
            app_label='nordpool', codename=spotprice['CODENAME'])
        tz = pytz.timezone(spotprice['TIMEZONE'])
        area = spotprice['AREA']
        currency = spotprice['CURRENCY']
        week_start = tz.localize(naive_week_start)
        week_end = tz.localize(naive_week_end)
        preliminary, final = parser.extract_prices(data, area, currency)
        update_rawdata(
            week_start, week_end, datasource, preliminary, final, tz,
            spotprice['NORDPOOL_UNIT'], spotprice['UNIT'])


def fetch_import_week(year, week, spotprices):
    lines = ftpclient.fetch_spot(year, week)
    data = parser.parse_lines(lines)
    import_week(data, spotprices)
