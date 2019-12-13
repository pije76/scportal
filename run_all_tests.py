#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Run all our tests
"""

import os
import re
import coverage
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gridplatform.settings.local")

from django.conf import settings
from django.core.management import execute_from_command_line


def main():
    """
    Run all our tests
    """

    if len(sys.argv) > 1:
        apps = sys.argv[1:]
    else:
        apps = settings.PLATFORM_APPS + settings.LEGACY_APPS + \
               settings.ENERGYMANAGER_APPS

    omit = ['*/*/migrations/*']
    cov = coverage.coverage(source=apps, omit=omit, branch=True)
    cov.use_cache(0)
    cov.start()
    # NOTE: collectstatic is necessary for staticfiles {% static %} when
    # STATICFILES_STORAGE is CachedStaticFilesStorage; URLs will contain
    # MD5-sums of contents of files read from the CachedStaticFilesStorage,
    # i.e. from files under STATIC_ROOT, i.e. from the "output" directory of
    # collectstatic
    execute_from_command_line(["", "collectstatic",
                               "--noinput", "--traceback"])

    execute_from_command_line(["", "test", "--noinput",
                               "--traceback"] + list(apps))
    cov.stop()
    cov.report(show_missing=1)

if __name__ == '__main__':
    main()
