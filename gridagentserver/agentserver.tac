# NOTE: this is not intended as a demonstration of correct use of Twisted
# conventions...

import logging.config
import os

from twisted.application import internet, service
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.python.log import ILogObserver, PythonLoggingObserver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agentserver.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Dev')

import configurations.importer
configurations.importer.install()
from agentserver import settings


logging.config.fileConfig('logging.ini')


from agentserver.amqp import AmqpFactory
from agentserver.twisted_server import AgentProtocolFactory


application = service.Application('gridagent')
# logging from Twisted to standard Python logging
application.setComponent(ILogObserver, PythonLoggingObserver().emit)

agentprotocol_factory = AgentProtocolFactory()

agentService = internet.TCPServer(settings.LISTEN_PORT, agentprotocol_factory)
agentService.setServiceParent(application)

amqp_factory = AmqpFactory(
    vhost=settings.AMQP_VHOST,
    user=settings.AMQP_USER,
    password=settings.AMQP_PASSWORD,
    spec_file=settings.AMQP_SPEC)

# set up circular references...
agentprotocol_factory.amqp = amqp_factory
amqp_factory.agentprotocol = agentprotocol_factory

amqp_endpint = TCP4ClientEndpoint(
    reactor, settings.AMQP_HOST, settings.AMQP_PORT)
amqp_connection = amqp_endpint.connect(amqp_factory)
# amqp_connection.addCallback(gotProtocol)
