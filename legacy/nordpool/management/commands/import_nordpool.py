# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import ftplib

from isoweek import Week

from django.core.management.base import BaseCommand
from django.db.transaction import commit_on_success

from legacy.nordpool.legacy import fetch_import_week
from legacy.nordpool.legacy import prices_today


class Command(BaseCommand):
    args = '[week [year]]'
    help = 'Import Nordpool spot prices for specific week plus one.  ' + \
        'Week/year defaults to current week/year.'

    def handle(self, *args, **options):
        week_number = None
        year = None

        try:
            week_number = int(args[0])
            year = int(args[1])
        except IndexError:
            pass

        today = datetime.datetime.now().date()
        if week_number is None:
            assert year is None
            this_week = Week.withdate(today)
        elif year is None:
            assert week_number is not None
            year = today.year
            this_week = Week(year, week_number)
        else:
            assert week_number is not None
            assert year is not None
            this_week = Week(year, week_number)
        next_week = this_week + 1

        try:
            with commit_on_success():
                fetch_import_week(this_week.year, this_week.week)
            with commit_on_success():
                fetch_import_week(next_week.year, next_week.week)
        except ftplib.error_perm as e:
            if e.args[0].startswith('550'):
                # File not found error --- usually caused by file not yet
                # uploaded to Nordpool FTP server...
                pass
            else:
                raise

        if not prices_today():
            print "Warning: Some spot prices does not have prices for today!"
