# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

import pytz
from django.core.management.base import BaseCommand

from legacy.devices.models import AgentEvent

TIMESTAMP_FORMAT = '%Y-%m-%d-%H:%M:%S'


class Command(BaseCommand):
    args = '<mac> [from] [to]'
    help = 'Get event log for GridAgent with <mac>. ' + \
        'Timestamp format YYYY-MM-DD-hh:mm:ss.'

    def handle(self, *args, **options):
        timezone = pytz.utc
        mac = args[0]
        try:
            timestamp_from = datetime.datetime.strptime(
                args[1],
                TIMESTAMP_FORMAT).replace(tzinfo=timezone)
        except IndexError:
            timestamp_from = None
        try:
            timestamp_to = datetime.datetime.strptime(
                args[2],
                TIMESTAMP_FORMAT).replace(tzinfo=timezone)
        except IndexError:
            timestamp_to = None

        qs = AgentEvent.objects.filter(agent__mac=mac)
        if timestamp_from is not None:
            qs.filter(timestamp__gte=timestamp_from)
        if timestamp_to is not None:
            qs.filter(timestamp__lte=timestamp_to)
        for event in qs:
            print '%s %i %s' % (
                event.timestamp.strftime(TIMESTAMP_FORMAT),
                event.code,
                event.message,
            )
