# -*- coding: utf-8 -*-
"""
Run ``./manage.py help generate_cache`` for further details on invoking the
command for generating cache.
"""
from __future__ import absolute_import
from __future__ import unicode_literals


from optparse import make_option
import datetime

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

import pytz

from gridplatform.utils.relativetimedelta import RelativeTimeDelta

from ...models import generate_cache
from ...models import DataSource
from ...models import CACHABLE_UNITS


def _make_periods(from_timestamp, to_timestamp):
    assert from_timestamp <= to_timestamp
    period_to = to_timestamp
    while period_to > from_timestamp:
        period_from = max(
            from_timestamp, period_to - datetime.timedelta(days=7))
        yield period_from, period_to
        period_to = period_from


class Command(BaseCommand):
    help = "Generate condensed measurement cache data for accumulation " + \
        "data sources"

    option_list = BaseCommand.option_list + (
        make_option(
            '--years_back', '-Y',
            dest='years',
            type=int,
            default=0),
        make_option(
            '--months_back', '-m',
            dest='months',
            type=int,
            default=0),
        make_option(
            '--days_back', '-d',
            dest='days',
            type=int,
            default=0),
        make_option(
            '--hours_back', '-H',
            dest='hours',
            type=int,
            default=0),
    )

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity'))
        now = datetime.datetime.now(pytz.utc)
        to_timestamp = now.replace(minute=0, second=0, microsecond=0)
        delta = RelativeTimeDelta(
            years=options['years'],
            months=options['months'],
            days=options['days'],
            hours=options['hours'])
        from_timestamp = to_timestamp - delta
        if from_timestamp == to_timestamp:
            raise CommandError('Needs non-empty time range specified.')
        if verbosity >= 1:
            self.stdout.write('Generating cache for period:\n  %s -- %s' % (
                from_timestamp, to_timestamp))

        datasources = list(
            DataSource.objects.filter(unit__in=CACHABLE_UNITS))
        if verbosity >= 1:
            self.stdout.write('%s data sources' % (len(datasources),))

        for period_from, period_to in _make_periods(
                from_timestamp, to_timestamp):
            for datasource in datasources:
                with transaction.atomic():
                    generate_cache(datasource, period_from, period_to)
