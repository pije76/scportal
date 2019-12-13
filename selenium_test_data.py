from __future__ import absolute_import

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gridplatform.settings.local")

from legacy.website.tests import setup

print setup()
