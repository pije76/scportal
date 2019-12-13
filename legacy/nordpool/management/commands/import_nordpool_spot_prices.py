# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import ftplib

from isoweek import Week

from django.core.management.base import BaseCommand
from django.db.transaction import commit_on_success

from gridplatform.global_datasources.models import GlobalDataSource
from legacy.nordpool.importer import fetch_import_week
from legacy.nordpool.conf import settings


def create_nordpool_datasources(spotprices):
    """
    The list of spot prices in conf.py are the list of currently supported
    spot prices. If GlobalDataSources corresponding to them do not exist,
    create them by calling this funnction before import continues. If there are
    other nordpool GlobalDataSoures (app_label='nordpool') then that must mean
    that we previously supported a different set of spot prices. They are just
    left alone and should no longer get new data imported.
    """
    for spotprice in spotprices:
        if not GlobalDataSource.objects.filter(
                app_label='nordpool',
                codename=spotprice['CODENAME'],
                country=spotprice['COUNTRY']).exists():
            GlobalDataSource.objects.create(
                unit=spotprice['UNIT'],
                name=spotprice['NAME'],
                app_label='nordpool',
                codename=spotprice['CODENAME'],
                country=spotprice['COUNTRY'])


class Command(BaseCommand):
    args = '[week [year]]'
    help = 'Import data for all currently supported Nordpool spot prices ' \
        'for specific week plus one. Data is imported into global data sources, ' \
        'creating new ones if needed. Week/year defaults to current week/year.'

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

        spotprices = settings.NORDPOOL_SPOT_PRICES
        create_nordpool_datasources(spotprices)
        try:
            with commit_on_success():
                fetch_import_week(this_week.year, this_week.week, spotprices)
            with commit_on_success():
                fetch_import_week(next_week.year, next_week.week, spotprices)
        except ftplib.error_perm as e:
            if e.args[0].startswith('550'):
                # File not found error --- usually caused by file not yet
                # uploaded to Nordpool FTP server...
                pass
            else:
                raise
