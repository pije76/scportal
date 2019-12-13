# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from operator import attrgetter

import datetime
from optparse import make_option

from django.core.management.base import BaseCommand
from gridplatform.trackuser import replace_customer
from gridplatform.trackuser import replace_user
from gridplatform.utils import condense
from gridplatform.utils.iter_ext import nwise
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from legacy.devices.models import PhysicalInput
from legacy.devices.models import RawData
import pytz


def is_monotonic(data):
    return all(a.value <= b.value for a, b in zip(data, data[1:])) or \
        all(a.value >= b.value for a, b in zip(data, data[1:]))


def find_hickups(data):
    hickups = []
    for raw_data in nwise(data, 15):
        # Strategy: The data is split into two control periods and
        # on period which is analysed for hickups given that both
        # control periods are monotonic.
        # All values in the hickup candidates period are checked if
        # the break the monotonisicity, and if so, if they are
        # diverging more than a certain decided tolerance.
        control_period_before = raw_data[:5]
        hickup_candidates = raw_data[5:10]
        control_period_after = raw_data[10:15]
        control_sequence = control_period_before + \
            control_period_after
        if not is_monotonic(raw_data) and \
                is_monotonic(control_sequence):
            value_getter = attrgetter('value')
            control_max = max(control_sequence, key=value_getter)
            control_min = min(control_sequence, key=value_getter)
            control_diff = control_max.value - control_min.value
            tolerance = max(control_diff * 2, 100000)
            hickups.extend([
                candidate for candidate in hickup_candidates
                if not (
                    (control_min.value - tolerance) <
                    candidate.value <
                    (control_max.value + tolerance)
                )
            ])
    return sorted(set(hickups))


class Command(BaseCommand):
    help = 'Detect hickups by scanning through raw measurement data'

    option_list = BaseCommand.option_list + (
        make_option(
            '-d',
            '--delete',
            action='store_true',
            dest='delete',
            default=False,
            help='Delete hickups when detected'),
        make_option(
            '-f',
            '--from',
            action='store',
            dest='from_datetime',
            default="2000-01-01T00:00",
            help='From timestamp in yyyy-mm-ddThh:mm notation'),
        make_option(
            '-c',
            '--customer',
            action='append',
            dest='customer',
            help='Only detect hickups for a certain customer id',
            type=int),
        make_option(
            '-m',
            '--meter',
            action='append',
            dest='meter',
            help='Only detect hickups for a specific meter id',
            type=int),
        make_option(
            '-p',
            '--previous-hour',
            action='store_true',
            dest='use_previous_hour',
            default=False),
        make_option(
            '-q',
            '--quiet',
            action='store_true',
            dest='be_quiet',
            default=False))

    def handle(self, *args, **options):
        with replace_customer(None), replace_user(None):
            be_quiet = options['be_quiet']
            delete_hickups = options['delete']

            hour = RelativeTimeDelta(hours=1)
            if options['use_previous_hour']:
                from_datetime = condense.floor(
                    datetime.datetime.now(pytz.utc), hour, pytz.utc) - hour
            else:
                from_datetime = pytz.utc.localize(
                    datetime.datetime.strptime(
                        options['from_datetime'], '%Y-%m-%dT%H:%M'))
            # Now go back one extra hour to make sure we catch possible hickups
            # in the beginning of the period.
            from_datetime = from_datetime - hour

            if not be_quiet:
                self.stdout.write("Finding peaks from %s" % (from_datetime,))

            customer = options['customer']
            meter = options['meter']

            # Note that we only check GM devices (the only devices for which
            # physical inputs exist) and we only check energy inputs.
            physical_input_qs = PhysicalInput.objects.filter(
                unit='milliwatt*hour')

            if meter:
                physical_input_qs = physical_input_qs.filter(
                    meter_id__in=meter)

            if customer:
                physical_input_qs = physical_input_qs.filter(
                    meter__customer_id__in=customer)

            hickup_ids = []
            for physical_input in physical_input_qs:
                raw_data = list(RawData.objects.filter(
                    datasource=physical_input,
                    timestamp__gt=from_datetime).order_by('timestamp'))
                while True:
                    hickups = find_hickups(raw_data)
                    if not hickups:
                        break
                    for hickup in hickups:
                        raw_data.remove(hickup)
                        hickup_ids.append(hickup.id)
                        if not be_quiet:
                            self.stdout.write(
                                ('hickup: meter_id: %s, '
                                 'physicalinput_id: %s, '
                                 'agent_mac: %s, value=%s, timestamp=%s')
                                % (
                                    physical_input.meter.id,
                                    physical_input.id,
                                    physical_input.meter.agent.mac,
                                    hickup.value,
                                    hickup.timestamp
                                )
                            )
            if delete_hickups and hickup_ids:
                RawData.objects.filter(id__in=hickup_ids).delete()
