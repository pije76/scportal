# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from cStringIO import StringIO

from pytz import utc
from django.core.management.base import BaseCommand

from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.export import consumption_report


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        to_timestamp = datetime.datetime.now(utc) - RelativeTimeDelta(hours=1)
        from_timestamp = to_timestamp - RelativeTimeDelta(days=1)
        mp_ids = map(int, args)
        mp_map = {mp.id: mp for mp in Collection.objects.filter(id__in=mp_ids)}
        # get them in the input/specified order...
        mps = [mp_map[mp_id] for mp_id in mp_ids]

        f = StringIO()
        consumption_report(mps, from_timestamp, to_timestamp, f)

        # print(f.getvalue(), end='')
