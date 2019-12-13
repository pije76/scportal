# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.core.management.base import BaseCommand
from django.db.transaction import commit_on_success

from legacy.energinet_co2.importer import fetch_import_day

DATE_FORMAT = '%Y-%m-%d'


class Command(BaseCommand):
    args = '[date]'
    help = 'Import Energinet.dk CO2 data. ' + \
        'Date format YYYY-MM-DD; defaults to yesterday.'

    def handle(self, *args, **options):
        try:
            date = datetime.datetime.strptime(args[0], DATE_FORMAT).date()
        except IndexError:
            date = (datetime.datetime.now() -
                    datetime.timedelta(days=1)).date()
        with commit_on_success():
            fetch_import_day(date)
