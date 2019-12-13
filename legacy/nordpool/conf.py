# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings
from appconf import AppConf
from django.utils.translation import ugettext_noop

__all__ = ['settings', 'NordpoolConf']


class NordpoolConf(AppConf):
    HOST = 'ftp.nordpoolspot.com'

    SPOT_PRICES = (
        {
            'CODENAME': 'denmark_west',
            'NORDPOOL_UNIT': 'currency_dkk*megawatt^-1*hour^-1',
            'UNIT': 'currency_dkk*gigawatt^-1*hour^-1',
            'NAME': ugettext_noop('Nordpool Denmark West DKK'),
            'CURRENCY': 'DKK',
            'COUNTRY': 'DK',
            'TIMEZONE': 'Europe/Copenhagen',
            'AREA': 'DK1',
        },
        {
            'CODENAME': 'denmark_east',
            'NORDPOOL_UNIT': 'currency_dkk*megawatt^-1*hour^-1',
            'UNIT': 'currency_dkk*gigawatt^-1*hour^-1',
            'NAME': ugettext_noop('Nordpool Denmark East DKK'),
            'CURRENCY': 'DKK',
            'COUNTRY': 'DK',
            'TIMEZONE': 'Europe/Copenhagen',
            'AREA': 'DK2',
        },
    )

    # Legacy
    AUTO_INDEXES = [
        {
            # index
            'COUNTRY': 'denmark',
            'UNIT': 'currency_dkk*megawatt^-1*hour^-1',
            'NAME': ugettext_noop('Nordpool Denmark West DKK'),
            # nordpool
            'AREA': 'DK1',
            'TIMEZONE': 'Europe/Copenhagen',
        },
        {
            # index
            'COUNTRY': 'denmark',
            'UNIT': 'currency_dkk*megawatt^-1*hour^-1',
            'NAME': ugettext_noop('Nordpool Denmark East DKK'),
            # nordpool
            'AREA': 'DK2',
            'TIMEZONE': 'Europe/Copenhagen',
        }
    ]

    class Meta:
        required = ['USER', 'PASS']
