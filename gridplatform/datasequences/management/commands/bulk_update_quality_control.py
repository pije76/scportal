# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from optparse import make_option

from gridplatform.customers.models import Customer
from gridplatform.consumptions.models import Consumption
from gridplatform.datasequences.models.qualitycontrol import AccumulationOfflineTolerance  # noqa


class Command(BaseCommand):
    help = 'Can set offline tolerance for all data sequences on a customer'

    option_list = BaseCommand.option_list + (
        make_option(
            '-c',
            '--customer_id',
            dest='customer_id',
            help='Customer ID',
            type=int
        ),
        make_option(
            '-o',
            '--offlinetolerance',
            dest='offlinetolerance',
            help='Set the offline tolerance. '
            'Specified as number of clock hours',
            type=int
        ),
    )

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity'))
        customer_id = options['customer_id']
        offlinetolerance = options['offlinetolerance']

        if customer_id is None:
            raise CommandError('You must specify a customer ID')
        try:
            Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise CommandError(
                'Customer with ID %d does not exist' % (customer_id,))

        if offlinetolerance is None:
            raise CommandError('You have not told the script to anything! '
                               'Run with --help for a list of options')
        else:
            # Update existing offline tolerances
            exiting_count = AccumulationOfflineTolerance.objects.filter(
                datasequence__customer_id=customer_id).update(
                    hours=offlinetolerance)
            # Create all missing offline tolerances
            new_offlinetolerances = [
                AccumulationOfflineTolerance(datasequence=ds,
                                             hours=offlinetolerance)
                for ds in Consumption.objects.filter(
                    customer_id=customer_id,
                    accumulationofflinetolerance__isnull=True)
            ]
            AccumulationOfflineTolerance.objects.bulk_create(
                new_offlinetolerances)
            if verbosity >= 1:
                print 'Updated %d existing offline tolerances and created '
                '%d new.' % (exiting_count, len(new_offlinetolerances))
