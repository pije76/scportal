# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import codecs
import datetime
import operator
import os.path
import pytz

from django.test import TestCase

from .parser import parse_forecast, parse_online


file_base = os.path.abspath(os.path.dirname(__file__))

forecast_file = os.path.join(file_base, '20130529_CO2prognose.txt')
online_file = os.path.join(file_base, '20130529_onlinedata.txt')


class ParserTest(TestCase):
    def test_parse_forecast(self):
        with open(forecast_file, 'r') as f:
            forecast = parse_forecast(f)
        # date for the example file
        self.assertEqual(forecast['date'], datetime.date(2013, 5, 29))
        self.assertEqual(forecast['header'], ('Timeinterval', 'CO2'))
        # should have 24 hours
        self.assertEqual(len(forecast['data']), 24)
        # should be sorted by "from" timestamp
        self.assertListEqual(
            forecast['data'],
            sorted(forecast['data'], key=operator.itemgetter(0)))
        # entries should be (datetime.time, datetime.time, int); check an
        # instance from the example file
        self.assertEqual(forecast['data'][1],
                         (datetime.time(1, 0), datetime.time(2, 0), 389))

    def test_parse_online(self):
        with codecs.open(online_file, 'r', 'iso8859-1') as f:
            online = parse_online(f)
        # date/time entry in header is handled separately...
        self.assertEqual(online['header'][0], 'Dato og tid')
        # normal header entry --- including a non-ASCII character
        self.assertEqual(online['header'][2], u'Centrale kraftværker DK2')
        # each entry is timestamp and 16 data values
        self.assertEqual(len(online['header']), 17)

        self.assertTupleEqual(
            online['data'][2],
            (
                pytz.timezone('Europe/Copenhagen').localize(
                    datetime.datetime(2013, 5, 29, 0, 10)),
                1094, 536, 197, 90, 593, 332, 291, 607,
                -897, 174, 98, -4, 0, 12, 6, 380))
