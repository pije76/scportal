# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings
from appconf import AppConf

__all__ = ['settings', 'EnerginetConf']


class EnerginetConf(AppConf):
    HOST = 'ftp.energinet.dk'

    # Whether to automatically create index instances on syncdb, if not already
    # created.
    AUTO_SETUP = True
    # Options used for creating index instances.
    UNIT = 'gram*kilowatt^-1*hour^-1'
    NAME = 'Energinet.dk CO₂'
    TIMEZONE = "Europe/Copenhagen"

    class Meta:
        required = ['USER', 'PASS']
