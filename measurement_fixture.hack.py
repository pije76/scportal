#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import datetime
import random
import pytz

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gridplatform.settings.local")

from django.db import transaction

from legacy.devices.models import PhysicalInput
from legacy.devices.models import RawData

days = 14
start = datetime.datetime.now(pytz.utc).replace(microsecond=0) - \
    datetime.timedelta(days=days)

dst_start = datetime.datetime(2013, 3, 31, tzinfo=pytz.utc)
dst_end = datetime.datetime(2012, 10, 28, tzinfo=pytz.utc)


val = 0

for physicalinput in PhysicalInput.objects.filter(
        unit='milliwatt*hour'):
    measurements = []
    if physicalinput.rawdata_set.exists():
        continue
    val = 0

    for time in [dst_end, dst_start]:
        for i in range(60 * 24 * 2):
            current = time + datetime.timedelta(minutes=i)
            if datetime.time(hour=6) < current.time() < datetime.time(hour=16):
                incr = random.randint(10000000, 11500000)
            else:
                incr = random.randint(100000, 300000)
            measurements.append(RawData(
                datasource_id=physicalinput.id,
                timestamp=current,
                value=val))
            val += incr / 60

    for i in range(60 * 24 * days):
        current = start + datetime.timedelta(minutes=i)
        if datetime.time(hour=6) < current.time() < datetime.time(hour=16):
            incr = random.randint(10000000, 11500000)
        else:
            incr = random.randint(100000, 300000)
        measurements.append(RawData(
            datasource_id=physicalinput.id,
            timestamp=current,
            value=val))
        val += incr / 60

    with transaction.commit_on_success():
        RawData.objects.bulk_create(measurements)

for physicalinput in PhysicalInput.objects.filter(
        unit='millikelvin') | PhysicalInput.objects.filter(
            unit='milliwatt') | PhysicalInput.objects.filter(
            unit='millinone'):
    measurements = []
    if physicalinput.rawdata_set.exists():
        continue
    for i in range(3 * 24 * days):
        current = start + datetime.timedelta(minutes=20 * i)
        val = random.randint(260000, 290000)
        measurements.append(RawData(
            datasource_id=physicalinput.id,
            timestamp=current,
            value=val))

    with transaction.commit_on_success():
        RawData.objects.bulk_create(measurements)

for pulse in PhysicalInput.objects.filter(
        unit='impulse'):
    measurements = []
    for i in range(3 * 24 * days):
        current = start + datetime.timedelta(minutes=20 * i)
        measurements.append(RawData(
            datasource_id=pulse.id,
            timestamp=current,
            value=i))
    RawData.objects.bulk_create(measurements)
