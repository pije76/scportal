"""
Unit test settings.
"""
from __future__ import absolute_import

import os

from .base import *  # noqa

# ######### DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-string-if-invalid  # noqa
TEMPLATE_STRING_IF_INVALID = '\XYZXYZXYZ'
# ######### END DEBUG CONFIGURATION


TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

# avoid poluting local system queue.
BROKER_BACKEND = 'memory'

# ######### TEST SETTINGS
TEST_RUNNER = 'junorunner.runner.JunoDiscoverRunner'
TEST_RUNNER_RERUN_LOG_FILE_NAME = os.environ.get(
    'TEST_RERUN_FILE', 'test_rerun.txt')
TEST_RUNNER_FAILURE_LIST_FILENAME = os.environ.get(
    'TEST_LOG_FILE', 'test_failures.txt')
# ######### END_TEST SETTINGS


# ######### STATIC FILE CONFIGURATION
# Don't use the "caching" variant; as it will try to read the file from where
# it *would* have been put by collectstatic to get the MD5 sum to append to the
# URL.
STATICFILES_STORAGE = \
    'django.contrib.staticfiles.storage.StaticFilesStorage'
# ######### END STATIC FILE CONFIGURATION


# ######### EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# ######### END EMAIL CONFIGURATION


# ######### DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'portal',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'TEST_NAME': os.environ.get('TEST_DATABASE_NAME', 'test_portal')
    },
}
# ######### END DATABASE CONFIGURATION


# ######### SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key should only be used for development and testing.
SECRET_KEY = r"{{ secret_key }}"
# ######### END SECRET CONFIGURATION

CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
