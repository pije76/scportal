"""
Production settings and globals.
"""
from __future__ import absolute_import

import os
import os.path

import dj_database_url

from .base import *  # noqa


# ######### HOST CONFIGURATION
# See: https://docs.djangoproject.com/en/1.5/releases/1.5/#allowed-hosts-required-in-production   # noqa
ALLOWED_HOSTS = get_secret_setting('ALLOWED_HOSTS')
# ######### END HOST CONFIGURATION


# ######### DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
# See: https://github.com/kennethreitz/dj-database-url
DATABASES = {
    'default': dj_database_url.parse(get_secret_setting('DATABASE_URL')),
}
# ######### END DATABASE CONFIGURATION


# ######### CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': get_secret_setting('CACHE_LOCATION'),
    }
}
# ######### END CACHE CONFIGURATION


# ######### SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = get_secret_setting('SECRET_KEY')
# ######### END SECRET CONFIGURATION


# ######### MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(SITE_ROOT), 'media/'))
# ######### END MEDIA CONFIGURATION


# ######### DJANGO COMPRESSOR CONFIGURATION
# Use pre-compression.  The "compress" management command must be run as part
# of deployment.
# See: http://django-compressor.readthedocs.org/en/latest/usage/#pre-compression  # noqa
COMPRESS_OFFLINE = True
# See: http://django-compressor.readthedocs.org/en/latest/settings/#django.conf.settings.COMPRESS_CSS_HASHING_METHOD  # noqa
COMPRESS_CSS_HASHING_METHOD = 'content'
# ######### END DJANGO COMPRESSOR CONFIGURATION


# ######### DATA IMPORT LOGIN CONFIGURATION
ENERGINET_CO2_USER = get_secret_setting('ENERGINET_CO2_USER')
ENERGINET_CO2_PASS = get_secret_setting('ENERGINET_CO2_PASS')
NORDPOOL_USER = get_secret_setting('NORDPOOL_USER')
NORDPOOL_PASS = get_secret_setting('NORDPOOL_PASS')
# ######### END DATA IMPORT LOGIN CONFIGURATION


# ######### CELERY CONFIGURATION
BROKER_URL = get_secret_setting("BROKER_URL")
CELERY_ROUTES = {
    'legacy.energy_use_reports.tasks.EnergyUseReportTask': {
        'queue': 'reports',
    },
    'legacy.manage_reports.tasks.collect_consumption_data': {
        'queue': 'reports',
    },
    'legacy.display_projects.tasks.ProjectReportTask': {
        'queue': 'reports',
    },
    'legacy.enpi_reports.tasks.ENPIReportTask': {
        'queue': 'reports',
    },
}
# ######### END CELERY CONFIGURATION


SITE_MAIL_ADDRESS = get_secret_setting('SITE_MAIL_ADDRESS')

INSTALLED_APPS = INSTALLED_APPS + (
    # Integration with the WSGI server used for deployment.
    # 'gunicorn',
)

NETS_KEY_DIR = "/home/portal/keys"
