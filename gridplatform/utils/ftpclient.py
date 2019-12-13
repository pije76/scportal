# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib
import ftplib


@contextlib.contextmanager
def ftpconnection(host='', user='', passwd=''):
    """
    Context manager wrapper for connecting to an FTP server, closing the
    connection with the QUIT command.

    :type host: string
    :param host: Hostname to connect to.  Will not connect if left empty.
    :type user: string
    :param user: User to log in as.  Will not log in if left empty.
    :type passwd: string
    :param passwd: Password password for login.
    """
    ftp = ftplib.FTP(host, user, passwd)
    try:
        yield ftp
    finally:
        ftp.quit()
