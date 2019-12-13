# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase

from . import models


class GlobalDataSourceTest(TestCase):
    def test_tariff_creation(self):
        models.GlobalDataSource.objects.create(
            name='global data source',
            unit='currency_dkk*kilowatt^-1*hour^-1')
