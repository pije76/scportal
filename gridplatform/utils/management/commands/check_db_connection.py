# -*- coding: utf-8 -*-
"""
Defines a ``check_db_connection`` command that checks if it is
possible to execute a noop command via the current database
connection.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import sys

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        try:
            cursor = connection.cursor()
            cursor.execute("select 1")
            success = 0
            print 'connected'
        except:
            success = 1
            print 'Not connected'

        sys.exit(success)
