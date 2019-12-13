"""
Common settings and globals.
"""

import json
import os
import os.path
import socket

from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from unipath import Path

import kombu


def get_secret_setting(setting):
    try:
        settings_module = os.environ['DJANGO_SETTINGS_MODULE']
    except KeyError:
        error_msg = "Set the DJANGO_SETTINGS_MODULE environment variable" % \
            setting
        raise ImproperlyConfigured(error_msg)
    secret_filename = '{}.json'.format(settings_module.split('.')[-1])
    user_dir = os.path.expanduser('~')
    secret_path = os.path.join(user_dir, secret_filename)
    try:
        with open(secret_path, 'r') as f:
            data = json.load(f)
    except IOError:
        error_msg = "Failed to read secrets file %s" % secret_path
        raise ImproperlyConfigured(error_msg)
    except ValueError:
        error_msg = "Failed to parse JSON from secrets file %s" % \
            secret_path
        raise ImproperlyConfigured(error_msg)
    try:
        return data[setting]
    except KeyError:
        error_msg = "Setting %s missing from secrets file %s" % \
            (setting, secret_path)
        raise ImproperlyConfigured(error_msg)


# ######### PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = Path(__file__).absolute().parent.parent

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = DJANGO_ROOT.parent

# Site name:
SITE_NAME = DJANGO_ROOT.name
# ######### END PATH CONFIGURATION

GRIDMANAGER_ADDRESS = "GridManager ApS\nNupark 51\n7500 Holstebro"

# ######### DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
# ######### END DEBUG CONFIGURATION


# ######### MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('Michael Nielsen', 'mcl@codewizards.dk'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
# ######### END MANAGER CONFIGURATION


# ######### DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {}
# ######### END DATABASE CONFIGURATION


# ######### GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'Europe/Copenhagen'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'da'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#languages
LANGUAGES = (
    ('en', _('English')),
    ('da', _('Danish')),
    ('es', _('Spanish')),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-thousand-separator  # noqa
USE_THOUSAND_SEPARATOR = True

AUTH_PROFILE_MODULE = 'customers.UserProfile'
AUTHENTICATION_BACKENDS = (
    'gridplatform.users.auth_backends.HashedUsernameBackend',
)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
# Encryption system keeps binary data in session; default/JSON serialisation
# would fail.
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

LOGIN_URL = reverse_lazy('start_site:login')
LOGOUT_URL = reverse_lazy('website-logout')
LOGIN_REDIRECT_URL = reverse_lazy('start_site:apps')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = 'no-reply@' + socket.gethostname()
# ######### END GENERAL CONFIGURATION


# ######### MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = os.path.normpath(os.path.join(SITE_ROOT, 'media/'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
# ######### END MEDIA CONFIGURATION


# ######### STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = os.path.normpath(os.path.join(SITE_ROOT, 'static/'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS  # noqa
STATICFILES_DIRS = ()

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders  # noqa
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

STATICFILES_STORAGE = \
    'django.contrib.staticfiles.storage.CachedStaticFilesStorage'
# ######### END STATIC FILE CONFIGURATION


# ######### SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = None
# ######### END SECRET CONFIGURATION


# ######### DATA IMPORT LOGIN CONFIGURATION
ENERGINET_CO2_USER = None
ENERGINET_CO2_PASS = None
NORDPOOL_USER = None
NORDPOOL_PASS = None
# ######### END DATA IMPORT LOGIN CONFIGURATION


# ######### SITE CONFIGURATION
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []
# ######### END SITE CONFIGURATION


# ######### FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS  # noqa
FIXTURE_DIRS = (
    os.path.normpath(os.path.join(SITE_ROOT, 'fixtures')),
)
# ######### END FIXTURE CONFIGURATION


# ######### TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors  # noqa
TEMPLATE_CONTEXT_PROCESSORS = (
    # Variables user, perms:
    'django.contrib.auth.context_processors.auth',
    # Variable boostrap_template
    'gridplatform.bootstrap.context_processors.bootstrap',
    # Variables current_user, current_customer:
    'gridplatform.trackuser.context_processors.trackuser',
    # If settings.DEBUG, variables debug=True, sql_queries:
    'django.core.context_processors.debug',
    # Variables LANGUAGES, LANGUAGE_CODE:
    'django.core.context_processors.i18n',
    # Variable MEDIA_URL:
    'django.core.context_processors.media',
    # Variable STATIC_URL:
    'django.core.context_processors.static',
    # Variable TIME_ZONE --- name af current "active" timezone:
    'django.core.context_processors.tz',
    # Variable request:
    'django.core.context_processors.request',
    # Variable messages (see documentation for Django messages framework):
    'django.contrib.messages.context_processors.messages',
    # Variable app_selection
    'energymanager.start_site.context_processors.app_selection',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
TEMPLATE_DIRS = (
    os.path.normpath(os.path.join(SITE_ROOT, 'templates')),
)
# ######### END TEMPLATE CONFIGURATION


# ######### MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    # Allow cross origin resource aquisition
    'corsheaders.middleware.CorsMiddleware',
    # Various convenience actions.  Only active/relevant is redirecting by
    # appending "/" to URL if requested URL does not exist but variant with
    # added "/" does.
    'django.middleware.common.CommonMiddleware',
    # Session support.
    'django.contrib.sessions.middleware.SessionMiddleware',
    # Locale support.
    'django.middleware.locale.LocaleMiddleware',
    # Cross site request forgery protection.
    'django.middleware.csrf.CsrfViewMiddleware',
    # Add "user" attribute, obtained from session, to request object.
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Load/decrypt encryption keys in session using key from cookie.
    'gridplatform.encryption.middleware.EncryptionMiddleware',
    'gridplatform.encryption.middleware.KeyLoaderMiddleware',
    # One database transaction per request; commit on success/response,
    # rollback on error.
    'django.middleware.transaction.TransactionMiddleware',
    # Message support (see documentation for Django messages framework).
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Keep current user/current customer in thread-locals...
    # (Against Django convention, but makes a lot of logic simpler/less
    # error-prone by allowing us to use "default=trackuser.get_user" and
    # "default=trackuser.get_customer" on model fields.)
    # Also adds "customer" variable to request from session/logged in user.
    'gridplatform.trackuser.middleware.TrackUserMiddleware',
    'gridplatform.utils.middleware.ExceptionRemoveInfoMiddleware',
    'gridplatform.utils.middleware.ExceptionAddInfoMiddleware',
    'gridplatform.utils.middleware.TimezoneMiddleware',
)
# ######### END MIDDLEWARE CONFIGURATION

# Allow javascript running on other sites to access the REST API.
CORS_ORIGIN_ALLOW_ALL = True
CORS_URLS_REGEX = '^/api/.*$'

# ######### URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
# ######### END URL CONFIGURATION


# ######### APP CONFIGURATION
DJANGO_APPS = (
    # Authentication/user login:
    'django.contrib.auth',
    # Generic relations:
    'django.contrib.contenttypes',
    # Sessions:
    'django.contrib.sessions',
    # Helpers for sharing backend/data between multiple websites:
    # 'django.contrib.sites',
    # Attach "messages" to session, to be displayed on next request:
    'django.contrib.messages',
    # Collect/manage per-app static files (collect for deployment, serve in
    # development, templatetag for URL):
    'django.contrib.staticfiles',
    # Numerous variants of "lorem ipsum" paragraphs:
    'django.contrib.webdesign',
    # Useful template tags:
    # 'django.contrib.humanize',
    # Admin panel and documentation:
    'django.contrib.admin',
    # 'django.contrib.admindocs',
)


# GridPortal 2.0 legacy or just dead apps that still have to linger in a zombie
# state due to their migrations.
LEGACY_APPS = (
    'legacy.legacy_utils',
    'legacy.devices',
    'legacy.display_indexes',
    'legacy.display_measurementpoints',
    'legacy.display_projects',
    'legacy.display_widgets',
    'legacy.edit_userprofile',
    'legacy.energinet_co2',
    'legacy.energy_use_reports',
    'legacy.enpi_reports',
    'legacy.indexes',
    'legacy.manage_collections',
    'legacy.manage_customers',
    'legacy.manage_devices',
    'legacy.manage_indexes',
    'legacy.manage_locations',
    'legacy.manage_measurementpoints',
    'legacy.manage_reports',
    'legacy.manage_rules',
    'legacy.manage_users',
    'legacy.measurementpoints',
    'legacy.datasequence_adapters',
    'legacy.projects',
    'legacy.rules',
    'legacy.setup_agents',
    'legacy.website',
    'legacy.efficiencymeasurementpoints',
    'legacy.nordpool',
)

# Apps specific for this project go here.
PLATFORM_APPS = (
    'gridplatform.encryption',
    'gridplatform.users',
    'gridplatform.customers',
    'gridplatform.providers',
    'gridplatform.rest',
    'gridplatform.condensing',
    'gridplatform.utils',
    'gridplatform.reports',
    'gridplatform.datasources',
    'gridplatform.global_datasources',
    'gridplatform.provider_datasources',
    'gridplatform.customer_datasources',
    'gridplatform.datasequences',
    'gridplatform.consumptions',
    'gridplatform.productions',
    'gridplatform.tariffs',
    'gridplatform.cost_compensations',
    'gridplatform.trackuser',
    'gridplatform.bootstrap',
    'gridplatform.token_auth',
    'gridplatform.jserror',
    'gridplatform.energyperformances',
    'gridplatform.co2conversions',
    'gridplatform.smilics',
    'gridplatform.datahub',
)

ENERGYMANAGER_APPS = (
    'energymanager.start_site',
    'energymanager.provider_site',
    'energymanager.energy_projects',
    'energymanager.led_light_site',
    'energymanager.price_relay_site',
    'energymanager.configuration_site',
    'energymanager.project_site',
    'energymanager.datahub_site',
)

THIRD_PARTY_APPS = (
    # Tree structured model relations.
    'mptt',
    # Template filters for HTML/CSS attributes on form fields
    'widget_tweaks',
    # asset packing
    'compressor',
    # Pytz integration/timezone helpers (model fields, middleware)
    # NOTE: We will *only* use the timezone model fields --- for the rest,
    # we use the built-in features from Django 1.4.
    'timezones2',
    # Django REST framework
    'rest_framework',
    'django_filters',
    'djangorestframework_camel_case',
    'corsheaders',
    # Images
    'imagekit',
    'model_utils',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = PLATFORM_APPS + LEGACY_APPS + ENERGYMANAGER_APPS + \
    DJANGO_APPS + THIRD_PARTY_APPS
# ######### END APP CONFIGURATION


# ######### LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'stderr': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'pika': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
        },
    },
    'root': {
        'handlers': ['stderr'],
        'level': 'INFO',
    },
}
# ######### END LOGGING CONFIGURATION


# ######### WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME
# ######### END WSGI CONFIGURATION


# ######### SOUTH CONFIGURATION
# See: http://south.readthedocs.org/en/latest/installation.html#configuring-your-django-installation  # noqa
INSTALLED_APPS += (
    # Database migration helpers:
    'south',
)
# Don't need to use South when setting up a test database.
SOUTH_TESTS_MIGRATE = False
# ######### END SOUTH CONFIGURATION


# ######### CELERY CONFIGURATION
INSTALLED_APPS += (
    # Celery/Django integration; used for cache result backend
    'djcelery',
)
# Only assign one task to each celery worker thread at the time:
# http://docs.celeryproject.org/en/latest/userguide/optimizing.html#reserve-one-task-at-a-time  # noqa
# http://docs.celeryproject.org/en/latest/faq.html#should-i-use-retry-or-acks-late  # noqa
CELERY_ACKS_LATE = True
CELERYD_PREFETCH_MULTIPLIER = 1

# Don't persist Celery queues to disk...
# http://docs.celeryproject.org/en/latest/userguide/optimizing.html#using-transient-queues  # noqa
# http://kombu.readthedocs.org/en/latest/reference/kombu.html?highlight=queue#kombu.Queue  # noqa
CELERY_QUEUES = (
    kombu.Queue('celery', routing_key='celery', durable=False),
    kombu.Queue('reports', routing_key='reports', durable=False),
    kombu.Queue('sanitize', routing_key='sanitize', durable=True),
)
CELERY_DEFAULT_QUEUE = 'celery'
CELERY_CREATE_MISSING_QUEUES = False

# We don't currently use rate limiting for any tasks...
# http://docs.celeryproject.org/en/latest/userguide/tasks.html#disable-rate-limits-if-they-re-not-used  # noqa
CELERY_DISABLE_RATE_LIMITS = True

# Store Celery results in Django cache
CELERY_RESULT_BACKEND = 'djcelery.backends.cache:CacheBackend'

CELERY_TRACK_STARTED = True

# Send error mail to ADMINS if errors occur during task execution.
CELERY_SEND_TASK_ERROR_EMAILS = True
# ######### END CELERY CONFIGURATION


# ######### DJANGO REST FRAMEWORK CONFIGURATION
REST_FRAMEWORK = {
    'FILTER_BACKEND': 'rest_framework.filters.DjangoFilterBackend',
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'gridplatform.rest.serializers.DefaultSerializer',
    'DEFAULT_PAGINATION_SERIALIZER_CLASS':
        'gridplatform.rest.serializers.DefaultPaginationSerializer',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'gridplatform.token_auth.authentication.EncryptionTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissions',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
    ),
    'PAGINATE_BY': 10000,
    'EXCEPTION_HANDLER': (
        'gridplatform.rest.gridplatform_rest_api_exception_handler'),
}
# ######### END DJANGO REST FRAMEWORK CONFIGURATION


BOOTSTRAP_THEME = 'genius'

SESSION_SAVE_EVERY_REQUEST = True


QUARTER_FORMAT = 'Q Y'
YEAR_FORMAT = 'Y'

SITE_MAIL_ADDRESS = "no-reply@gridportal.dk"
