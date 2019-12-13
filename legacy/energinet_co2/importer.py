# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from legacy.indexes.models import Entry

from .ftpclient import fetch_online
from .models import ModelBinding
from .parser import parse_online


def fetch_import_day(date):
    bindings = ModelBinding.objects.all()
    if not len(bindings):
        # not set up
        return

    # forecast = fetch_forecast(date)
    # if forecast is not None:
    #     forecast = parse_forecast(forecast)
    #     assert forecast['date'] == date
    online = fetch_online(date)
    if online is not None:
        online = parse_online(online)
    for binding in bindings:
        # normally just one, but might as well handle several...
        # if forecast:
        #     for from_hour, to_hour, value in forecast['data']:
        #         from_timestamp = datetime.datetime.combine(date, from_hour)
        #         to_timestamp = datetime.datetime.combine(date, to_hour)
        #         if to_timestamp < from_timestamp:
        #             to_timestamp = to_timestamp + datetime.timedelta(days=1)
        #         aware_from_timestamp = tz.localize(from_timestamp)
        #         aware_to_timestamp = tz.localize(to_timestamp)
        #         binding.forecast_index.entry_set.get_or_create(
        #             from_timestamp=aware_from_timestamp,
        #             to_timestamp=aware_to_timestamp,
        #             value=value)
        if online:
            for line in online['data']:
                from_timestamp = line[0]
                to_timestamp = from_timestamp + datetime.timedelta(minutes=5)
                value = line[16]
                try:
                    entry = binding.index.entry_set.get(
                        from_timestamp=from_timestamp,
                        to_timestamp=to_timestamp)
                    if entry.value != value:
                        entry.value = value
                        entry.save()
                except Entry.DoesNotExist:
                    binding.index.entry_set.create(
                        from_timestamp=from_timestamp,
                        to_timestamp=to_timestamp,
                        value=value)
