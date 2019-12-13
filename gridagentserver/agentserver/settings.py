# Django/agent server configuration
import datetime

from configurations import Settings


class Base(Settings):
    TIME_ZONE = 'UTC'
    USE_TZ = True

    INSTALLED_APPS = (
        'gridplatform.encryption',
        'gridplatform.users',
        'gridplatform.customers',
        'legacy.devices',
        'legacy.measurementpoints',
        'gridplatform.datasequences',
    )

    SECRET_KEY = 'abc'

    # agent server config...
    POLL_INTERVAL = 60.0
    POLL_START_DELAY = 15.0

    TIME_SYNC_INTERVAL = datetime.timedelta(days=1)
    TIME_SYNC_TOLERANCE = 15.0

    LISTEN_PORT = 30001

    AMQP_PORT = 5672
    AMQP_VHOST = '/'
    AMQP_USER = "guest"
    AMQP_PASSWORD = "guest"
    AMQP_SPEC = 'amqp0-8.stripped.rabbitmq.xml'

    SITE_NAME = 'gridplatform'


class Prod(Base):
    SITE_MAIL_ADDRESS = "no-reply@grid-manager.com"
    AMQP_HOST = "engine.grid-manager.com"

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'gridportal',
            'USER': 'grid',
            'PASSWORD': 'ugOk9Blim',
            'HOST': '77.66.29.230',
            'PORT': '5432',
        }
    }


class Local(Base):
    AMQP_HOST = 'localhost'

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'portal',
            # Current *nix user have local sockec access...
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
        }
    }


# Configuration for the GreenTech Center server. The server is physically
# located at the GTC in Vejle, Denmark.
class GreenTech(Local):
    SITE_MAIL_ADDRESS = "no-reply@greentech.gridmanager.dk"


# Configuration for the server at Cheminova. Will be running for approximately
# 3 months.
class Cheminova(Local):
    SITE_MAIL_ADDRESS = "no-reply@cheminova.gridmanager.dk"


# For the GridManager Iberia server. Located in Spain, managed by Netgroup.
class Iberia(Local):
    SITE_MAIL_ADDRESS = "no-reply@iberia.grid-manager.com"


class Test(Local):
    SITE_MAIL_ADDRESS = "no-reply@test.grid-manager.com"


class Dev(Local):
    DEBUG = True
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
