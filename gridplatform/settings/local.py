"""
Development settings and globals.
"""

from __future__ import absolute_import

import dj_database_url

from .base import *  # noqa


def local_secret_setting(setting, default):
    # If you need secret settings then create a file 'local.json' in your home
    # dir containing the needed settings.
    try:
        return get_secret_setting(setting)
    except ImproperlyConfigured:
        return default


# ######### DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-string-if-invalid  # noqa
TEMPLATE_STRING_IF_INVALID = '\XYZXYZXYZ'
# ######### END DEBUG CONFIGURATION


# ######### EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# ######### END EMAIL CONFIGURATION


# ######### DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': dj_database_url.parse('postgres:///portal'),
}
# ######### END DATABASE CONFIGURATION


# ######### CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
'''CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': [
            'localhost:11211',
        ]
    }
}'''
# ######### END CACHE CONFIGURATION


# ######### SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key should only be used for development and testing.
SECRET_KEY = r"SECRET SECRET SECRET"
# ######### END SECRET CONFIGURATION


# ######### DATA IMPORT LOGIN CONFIGURATION
ENERGINET_CO2_USER = local_secret_setting('ENERGINET_CO2_USER', None)
ENERGINET_CO2_PASS = local_secret_setting('ENERGINET_CO2_PASS', None)
NORDPOOL_USER = local_secret_setting('NORDPOOL_USER', None)
NORDPOOL_PASS = local_secret_setting('NORDPOOL_PASS', None)
# ######### END DATA IMPORT LOGIN CONFIGURATION


# ######### QUNIT CONFIGURATION
INSTALLED_APPS += (
    'django_qunit',
)
QUNIT_TEST_PATH = 'qunit/'

TEMPLATE_LOADERS += (
    'django_qunit.snippet_loader.Loader',
)

# ######### END QUNIT CONFIGURATION

# ######### TOOLBAR CONFIGURATION
# See: http://django-debug-toolbar.readthedocs.org/en/latest/installation.html#explicit-setup  # noqa
# INSTALLED_APPS += (
#'debug_toolbar',
#'debug_panel',
# )
# MIDDLEWARE_CLASSES += (
# 'debug_toolbar.middleware.DebugToolbarMiddleware',
#    'debug_panel.middleware.DebugPanelMiddleware',
#)
#DEBUG_TOOLBAR_PATCH_SETTINGS = False
# http://django-debug-toolbar.readthedocs.org/en/latest/installation.html
#INTERNAL_IPS = ('127.0.0.1', '10.0.2.2', )
# DEBUG_TOOLBAR_CONFIG = {
# 'HIDE_IN_STACKTRACES': (
#     'SocketServer', 'threading', 'wsgiref', 'debug_toolbar'),
#}
# ######### END TOOLBAR CONFIGURATION


# ######### CELERY CONFIGURATION
BROKER_URL = "amqp://guest:guest@localhost:5672//"
# ######### END CELERY CONFIGURATION


NETS_KEY_DIR = "/home/code/keys"
