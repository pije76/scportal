# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.db import transaction

from gridplatform.utils import utilitytypes
from legacy.indexes.models import SpotMapping
from legacy.indexes.models import Index
from legacy.measurementpoints.fields import DataRoleField
from legacy.nordpool.conf import settings


class Command(BaseCommand):
    args = ''
    help = 'Setup Nordpool spot tariffs for later import by '\
        '`import_nordpool` command'

    def handle(self, *args, **options):
        if SpotMapping.objects.exists():
            print 'Nothing to do. Nordpool spot tariffs already setup.'
            return

        with transaction.atomic():
            for opts in settings.NORDPOOL_AUTO_INDEXES:
                print 'setting up %s' % opts
                index = Index.objects.create(
                    unit=opts['UNIT'],
                    name_plain=opts['NAME'],
                    timezone=opts['TIMEZONE'],
                    role=DataRoleField.ELECTRICITY_TARIFF,
                    utility_type=utilitytypes.METER_CHOICES.electricity,
                    data_format=Index.SPOT,
                    customer=None)
                SpotMapping.objects.create(
                    index=index,
                    area=opts['AREA'],
                    timezone=opts['TIMEZONE'],
                    unit=opts['UNIT'])
