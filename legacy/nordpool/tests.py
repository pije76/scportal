# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import os.path

import pytz
from django.test import TestCase

from gridplatform.global_datasources.models import GlobalDataSource
from legacy.indexes.models import Index, SpotMapping
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes

from . import parser
from . import importer
from . import legacy


def week_filename(date):
    base = os.path.abspath(os.path.dirname(__file__))
    year, week, _weekday = date.isocalendar()
    return os.path.join(base, 'spot%02d%02d.sdv' % (year % 100, week))


def parse_file(filename):
    with open(filename, 'rb') as f:
        lines = f.readlines()
    return parser.parse_lines(lines)


class TestParsing(TestCase):
    def setUp(self):
        self.days = {
            'normal': datetime.date(2012, 1, 3),
            'switch_to_dst': datetime.date(2012, 3, 25),
            'switch_from_dst': datetime.date(2012, 10, 28),
            'week_partial': datetime.date(2012, 11, 12),
        }

    def test_parse_csv(self):
        for day in self.days.values():
            parse_file(week_filename(day))

    def test_extract_prices(self):
        area = 'DK1'
        currency = 'DKK'
        for day in (self.days['normal'],
                    self.days['switch_to_dst'],
                    self.days['switch_from_dst']):
            data = parse_file(week_filename(day))
            preliminary, final = parser.extract_prices(data, area, currency)
            self.assertEqual(len(final), 7)

    def test_day_entries(self):
        area = 'DK1'
        currency = 'DKK'
        tz = pytz.timezone('Europe/Copenhagen')

        def day_final_entries(day):
            data = parse_file(week_filename(day))
            preliminary, final = parser.extract_prices(data, area, currency)
            day_data, = filter(lambda entry: entry[0] == day, final)
            date, hourly = day_data
            return parser.day_entries(date, hourly, tz)

        self.assertEqual(
            len(day_final_entries(self.days['normal'])), 24)
        self.assertEqual(
            len(day_final_entries(self.days['switch_to_dst'])), 23)
        entries = day_final_entries(self.days['switch_from_dst'])
        self.assertEqual(len(entries), 25)
        # hour from 2--3 repeated with/without DST; price repeated
        self.assertEqual(entries[2][2], entries[3][2])
        self.assertEqual(entries[2][0].hour, entries[3][0].hour)
        day = self.days['week_partial']
        data = parse_file(week_filename(day))
        preliminary, final = parser.extract_prices(data, area, currency)
        day_data, = filter(lambda entry: entry[0] == day, preliminary)
        date, hourly = day_data
        self.assertEqual(len(parser.day_entries(date, hourly, tz)), 24)

    def test_import(self):
        spotprices = (
            {
                'CODENAME': 'denmark_west',
                'NORDPOOL_UNIT': 'currency_dkk*gigawatt^-1*hour^-1',
                'UNIT': 'currency_dkk*megawatt^-1*hour^-1',
                'NAME': 'Nordpool Denmark West DKK',
                'CURRENCY': 'DKK',
                'COUNTRY': 'DK',
                'TIMEZONE': 'Europe/Copenhagen',
                'AREA': 'DK1',
            },
        )
        ds = GlobalDataSource.objects.create(
            name='test',
            app_label='nordpool',
            codename='denmark_west',
            country='DK')
        data = parse_file(week_filename(self.days['normal']))
        importer.import_week(data, spotprices)
        self.assertEqual(ds.rawdata_set.count(), 7 * 24)

        data = parse_file(week_filename(self.days['week_partial']))
        importer.import_week(data, spotprices)
        self.assertEqual(ds.rawdata_set.count(), 7 * 24 + 3 * 24)
        # importing again for same week should have no effect
        importer.import_week(data, spotprices)
        self.assertEqual(ds.rawdata_set.count(), 7 * 24 + 3 * 24)

    def test_legacy_import(self):
        tz = pytz.timezone('Europe/Copenhagen')
        index = Index(
            unit="currency_dkk*megawatt^-1*hour^-1",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SPOT, name='Denmark West DKK',
            timezone=tz,
            customer=None,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        index.save()
        mapping = SpotMapping(index=index, area='DK1', currency='DKK',
                              unit='currency_dkk', timezone=tz)
        mapping.save()

        data = parse_file(week_filename(self.days['normal']))
        legacy.import_week(data)
        self.assertEqual(index.entry_set.count(), 7 * 24)

        data = parse_file(week_filename(self.days['week_partial']))
        legacy.import_week(data)
        self.assertEqual(index.entry_set.count(), 7 * 24 + 3 * 24)
        # importing again for same week should have no effect
        legacy.import_week(data)
        self.assertEqual(index.entry_set.count(), 7 * 24 + 3 * 24)
