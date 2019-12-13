# -*- coding: utf-8 -*-
"""
Defines a ``fix_contenttypes_and_permissions`` command, which runs
:func:`django.contrib.contenttypes.management.update_all_contenttypes`
and then runs
:func:`django.contrib.auth.management.create_permissions` for each
app.  This ensures that there are no missing content types and no
missing permissions.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions
from django.contrib.contenttypes.management import update_all_contenttypes
from django.core.management.base import BaseCommand
from django.db.models import get_apps


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        # Add any missing content types
        update_all_contenttypes()

        # Add any missing permissions
        for app in get_apps():
            create_permissions(app, None, 2)
