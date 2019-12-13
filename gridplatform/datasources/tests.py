# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.test import TestCase
from django.core.exceptions import ValidationError
import pytz

from .models import RawData
from .models import DataSource


class TariffRawDataTest(TestCase):
    def setUp(self):
        self.datasource = DataSource(
            unit='currency_dkk*kilowatt^-1*hour^-1')

    def test_tariff_clean_accepts_valid_timestamp(self):
        rawdata = RawData(
            datasource=self.datasource,
            value=1,
            timestamp=datetime.datetime(2014, 1, 1, 1, tzinfo=pytz.utc))

        rawdata.clean()

    def test_tariff_clean_detects_invalid_timestamp(self):
        rawdata = RawData(
            datasource=self.datasource,
            value=1,
            timestamp=datetime.datetime(2014, 1, 1, 0, 5, tzinfo=pytz.utc))

        with self.assertRaises(ValidationError) as e:
            rawdata.clean()

        self.assertIn('timestamp', e.exception.message_dict)


class Co2ConversionRawDataTest(TestCase):
    def setUp(self):
        self.datasource = DataSource(
            unit='gram*kilowatt^-1*hour^-1')

    def test_tariff_clean_accepts_valid_timestamp(self):
        rawdata = RawData(
            datasource=self.datasource,
            value=1,
            timestamp=datetime.datetime(2014, 1, 1, 1, 25, tzinfo=pytz.utc))

        rawdata.clean()

    def test_tariff_clean_detects_invalid_timestamp(self):
        rawdata = RawData(
            datasource=self.datasource,
            value=1,
            timestamp=datetime.datetime(2014, 1, 1, 0, 3, tzinfo=pytz.utc))

        with self.assertRaises(ValidationError):
            rawdata.clean()
