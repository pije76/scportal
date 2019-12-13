# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Client towards the Nordpool FTP server.

@attention: Not included in unit tests --- we don't want to hit the Nordpool
FTP server on normal test runs...  (And we haven't added infrastructure for
writing tests that shouldn't run...)
"""

import ftplib

from gridplatform.utils.ftpclient import ftpconnection

from .conf import settings


class NotFoundError(IOError):
    pass


def fetch_spot(year, week):
    """
    Fetch the spot price file for a specified week from the Nordpool FTP
    server.

    @type year: integer
    @param year: The year to fetch data for.
    @type week: integer
    @param week: The week number to fetch data for.  Use ISO weeks.
    @rtype: string list
    @return: A list of lines from the week data file.
    @raise NotFoundError: If the expected data file was not found on the
                          server.
    """
    base_dir = 'Elspot/Elspot_file'
    filename = 'spot%02d%02d.sdv' % (year % 100, week)
    yeardir = '%04d' % (year,)
    with ftpconnection(
            settings.NORDPOOL_HOST, settings.NORDPOOL_USER,
            settings.NORDPOOL_PASS) as ftp:
        ftp.cwd(base_dir)
        try:
            # base directory contains three years of data; for last year and
            # earlier, data is (also) present in subdirectories per year
            lines = []
            ftp.retrlines('RETR %s' % (filename,), lines.append)
        except ftplib.error_perm as e:
            if e.args[0].startswith('550'):
                # "file unavailable" (FTP error code 550)
                # try subdirectory for year if file not present in base
                # directory
                ftp.cwd(yeardir)
                lines = []
                ftp.retrlines('RETR %s' % (filename,), lines.append)
            else:
                raise
        return lines
