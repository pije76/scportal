# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import ftplib

from gridplatform.utils.ftpclient import ftpconnection

from .conf import settings


def _fetch_energinet(base_dir, filename):
    assert settings.ENERGINET_CO2_HOST
    assert settings.ENERGINET_CO2_USER
    assert settings.ENERGINET_CO2_PASS
    with ftpconnection(settings.ENERGINET_CO2_HOST,
                       settings.ENERGINET_CO2_USER,
                       settings.ENERGINET_CO2_PASS) as ftp:
        ftp.cwd(base_dir)
        try:
            lines = []
            ftp.retrlines('RETR %s' % (filename,), lines.append)
            return lines
        except ftplib.error_perm as e:
            if e.args[0].startswith('550'):
                # "file unavailable" (FTP error code 550)
                return None
            else:
                raise


def fetch_forecast(date):
    return _fetch_energinet(
        'CO2Prognoser',
        '{}_CO2prognose.txt'.format(date.strftime('%Y%m%d')))


def fetch_online(date):
    return _fetch_energinet(
        'Onlinedata',
        '{}_onlinedata.txt'.format(date.strftime('%Y%m%d')))
