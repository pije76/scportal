# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import requests
import re

from django.core.management.base import BaseCommand
from django.db import transaction

import pytz

from gridplatform.global_datasources.models import GlobalDataSource
from gridplatform.datasources.models import RawData


class Command(BaseCommand):
    help = "Import data from nordpool api"

    def handle(self, *args, **options):
        dk1, created = GlobalDataSource.objects.get_or_create(
            name="dk1", app_label="nordpool", codename="nordpool_dk1",
            country="DK", unit="currency_dkk*gigawatt^-1*hour^-1")
        dk2, created = GlobalDataSource.objects.get_or_create(
            name="dk2", app_label="nordpool", codename="nordpool_dk2",
            country="DK", unit="currency_dkk*gigawatt^-1*hour^-1")

        url = 'http://www.nordpoolspot.com/api/marketdata/page/41?currency=,DKK,,EUR'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML,'
                          ' like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10136',
            'Referer': 'http://www.nordpoolspot.com/Market-data1/'
                       'Elspot/Area-Prices/ALL1/Hourly/?view=table',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'da-DK,da;q=0.8,en-US;q=0.6,en;q=0.4,nb;q=0.2',
        }

        response = requests.get(url, headers=headers)
        data = {}

        if response.ok:
            data = response.json()['data']['Rows']

        prog = re.compile(r"\d\d&nbsp;-&nbsp;\d\d")

        with transaction.atomic():
            for row in data:
                if prog.match(row["Name"]):
                    timestamp = datetime.datetime.strptime(
                        row["StartTime"], "%Y-%m-%dT%H:%M:%S")
                    timestamp = pytz.timezone('Europe/Copenhagen').localize(timestamp)
                    print timestamp
                    for column in row["Columns"]:
                        if column["Name"] == "DK1":
                            self._update_or_create(
                                timestamp,
                                dk1.id,
                                {
                                    'value': int(float(column["Value"].replace(',', '.').replace(' ', '')) * 1000),
                                }
                            )
                        elif column["Name"] == "DK2":
                            self._update_or_create(
                                timestamp,
                                dk2.id,
                                {
                                    'value': int(float(column["Value"].replace(',', '.').replace(' ', '')) * 1000),
                                }
                            )

    def _update_or_create(self, timestamp, datasource_id, updated_values):
        try:
            obj = RawData.objects.get(timestamp=timestamp, datasource_id=datasource_id)
            for key, value in updated_values.iteritems():
                setattr(obj, key, value)
            obj.save()
        except RawData.DoesNotExist:
            updated_values.update({'timestamp': timestamp, 'datasource_id': datasource_id, 'unit': "currency_dkk*gigawatt^-1*hour^-1"})
            obj = RawData(**updated_values)
            obj.save()
