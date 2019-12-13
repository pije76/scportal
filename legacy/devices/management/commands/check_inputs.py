# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib
import datetime
import cStringIO

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.db import connection
import pytz
import unicodecsv


from gridplatform.datasequences.models import NonpulseAccumulationPeriod
from gridplatform.datasequences.models import PulseAccumulationPeriod
from gridplatform.consumptions.models import Consumption


class _excel_semicolon(unicodecsv.excel):
    delimiter = b';'


def _format_csv(data, header=None):
    with contextlib.closing(cStringIO.StringIO()) as outfile:
        # BOM included for Excel-compatibility --- assuming that this is the
        # "start of the file"
        bom = b'\xef\xbb\xbf'
        outfile.write(bom)
        writer = unicodecsv.writer(outfile, dialect=_excel_semicolon)
        if header is not None:
            writer.writerow(header)
        for mp in sorted(data, key=lambda x: (getattr(x, 'customer_id'),
                                              getattr(x, 'id'))):
            writer.writerow((mp.id, mp.customer.id))
        return outfile.getvalue()


_csv_header = ('measurementpoint id', 'customer id')


def _physicalinput_data(pi):
    return (
        pi.meter.agent.mac,
        pi.meter.get_manufactoring_id_display(),
        pi.get_type_display(),
        pi.order,
        pi.meter.customer_id)


class Command(BaseCommand):
    args = '[email_recipient]'
    help = 'Get lists of inputs with no measurements or no change in '
    ' measurements for the last 24 hours.'

    def handle(self, *args, **options):
        try:
            email = args[0]
        except IndexError:
            email = None
        now = datetime.datetime.now(pytz.utc).replace(microsecond=0)
        day_ago = now - datetime.timedelta(days=1)

        cursor = connection.cursor()
        cursor.execute(
            'SELECT datasource_id '
            'FROM datasources_rawdata WHERE timestamp > %s '
            'GROUP BY datasource_id '
            'HAVING MIN(value) = MAX(value)', [day_ago])
        ids = [n for (n,) in cursor.fetchall()]

        nonpulseaccum_inputperiods = \
            NonpulseAccumulationPeriod.objects.filter(
                data_source_id__in=ids)
        pulseaccum_inputperiods = \
            PulseAccumulationPeriod.objects.filter(
                data_source_id__in=ids)
        inputconfiguration_ids = set(
            list(nonpulseaccum_inputperiods.values_list(
                'input_configuration_id', flat=True)) +
            list(pulseaccum_inputperiods.values_list(
                'input_configuration_id', flat=True)))

        mps = []
        for inputconfiguration_id in inputconfiguration_ids:
            inputconfiguration = Consumption.objects.get(
                id=inputconfiguration_id)
            if inputconfiguration.link_derivative_set.exists():
                mps.append(inputconfiguration.
                           link_derivative_set.all()[0].graph.
                           collection.subclass_instance)

        no_change = _format_csv(
            mps,
            _csv_header)
        if email:
            message = EmailMessage(
                'Input check report',
                'Period: {} -- {}'.format(day_ago, now),
                settings.SITE_MAIL_ADDRESS,
                [email])
            message.attach(
                'no_change.csv', no_change, 'text/csv')
            message.send(fail_silently=False)
        else:
            print 'Period: {} -- {}'.format(day_ago, now)
            print
            print 'No change in measurements:'
            print no_change
