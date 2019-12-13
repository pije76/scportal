import json
import logging

from twisted.internet import protocol, reactor
from twisted.internet.defer import inlineCallbacks
from twisted.python import log
from txamqp.client import TwistedDelegate
from txamqp.content import Content
from txamqp.protocol import AMQClient
from txamqp.spec import load as load_spec

from gridagentserver_protocol.server_messages import (
    CommandGpSwitchRelay,
    CommandGpSwitchControl,
    ConfigGaSoftware,
    ConfigGpSoftware,
    ConfigGaRulesets,
)
from gridagentserver_protocol.datatypes import (
    Meter,
    RuleSet,
    Rule,
)

logger = logging.getLogger(__name__)


# factory has:
# * user
# * password
# * exchange
# * exchange_type
# * incoming (queue)
# * outgoing (queue)
# * routes

# connect -> authenticate -> open channel ->
# declare exchange -> declare "private" (exclusive=True) queue for input
class AmqpProtocol(AMQClient):
    def __init__(self, *args, **kwargs):
        AMQClient.__init__(self, *args, **kwargs)
        self._routes = set()
        self._adding_routes = set()
        self._removing_routes = set()

    @inlineCallbacks
    def connectionMade(self):
        # connected to server --- not ready to communicate...
        AMQClient.connectionMade(self)
        log.msg('connected to server')
        self.connected = False
        # authenticate
        yield self.authenticate(self.factory.user, self.factory.password)
        log.msg('authenticated as %s' % (self.factory.user,))
        # open channel
        self.chan = yield self.channel(1)
        log.msg('got channel')
        yield self.chan.channel_open()
        log.msg('channel opened')
        # declare exchange
        yield self.chan.exchange_declare(
            exchange=self.factory.exchange,
            type=self.factory.exchange_type)
        log.msg('exchange (%s, %s) declared' % (
            self.factory.exchange, self.factory.exchange_type))
        # declare queue
        result = yield self.chan.queue_declare(exclusive=True)
        self.queue_name = result.queue
        log.msg('queue (%s) declared' % (self.queue_name,))
        # consume
        result = yield self.chan.basic_consume(
            queue=self.queue_name, no_ack=True)
        self.consumer_tag = result.consumer_tag
        log.msg('started consuming (tag: %s)' % (self.consumer_tag,))
        queue = yield self.queue(self.consumer_tag)
        d = queue.get()
        d.addCallback(self._read_item, queue)

        self.connected = True

        self.routes_updated()
        # self.send()

    def routes_updated(self):
        """
        Tries to bring the current set of registered routes to the state
        specified on the factory.
        """
        # We have/use this rather than direct access to add and remove methods,
        # to handle the edge cases where a route is to be added/removed while
        # it is in the process of being removed/added.
        desired_routes = self.factory._routes
        to_add = desired_routes - self._routes
        to_remove = self._routes - desired_routes
        for route in to_add - self._adding_routes:
            self._add_route(route)
        for route in to_remove - self._removing_routes:
            self._remove_route(route)

    @inlineCallbacks
    def _add_route(self, routing_key):
        assert routing_key not in self._routes
        assert routing_key not in self._adding_routes
        self._adding_routes.add(routing_key)
        yield self.chan.queue_bind(queue=self.queue_name,
                                   exchange=self.factory.exchange,
                                   routing_key=routing_key)
        self._adding_routes.remove(routing_key)
        self._routes.add(routing_key)
        # Check the overall current state of routes --- we might need to remove
        # the route we just added again...
        log.msg('route (%s) added' % (routing_key,))
        self.routes_updated()

    @inlineCallbacks
    def _remove_route(self, routing_key):
        assert routing_key in self._routes
        assert routing_key not in self._removing_routes
        self._removing_routes.add(routing_key)
        yield self.chan.queue_unbind(queue=self.queue_name,
                                     exchange=self.factory.exchange,
                                     routing_key=routing_key)
        self._removing_routes.remove(routing_key)
        self._routes.remove(routing_key)
        # Check the overall current state of routes --- we might need to add
        # the route we just removed back in...
        log.msg('route (%s) removed' % (routing_key,))
        self.routes_updated()

    def _read_item(self, item, queue):
        self.factory.received(item)
        queue.get().addCallback(self._read_item, queue)

    def send(self, routing_key, msg):
        msg = Content(msg)
        self.chan.basic_publish(exchange=self.factory.exchange,
                                routing_key=routing_key,
                                content=msg)


def clean_version(major, minor, revision, extra):
    return (int(major), int(minor), int(revision), str(extra))


class AmqpFactory(protocol.ReconnectingClientFactory):
    protocol = AmqpProtocol

    def __init__(self, spec_file=None, vhost=None, user=None, password=None):
        spec_file = spec_file or 'amqp0-8.stripped.rabbitmq.xml'
        self.spec = load_spec(spec_file)
        self.user = user or 'guest'
        self.password = password or 'guest'
        self.vhost = vhost or '/'
        self.delegate = TwistedDelegate()
        self.exchange = 'agentservers'
        self.exchange_type = 'topic'
        self._routes = set(['agentserver'])
        self.p = None
        reactor.addSystemEventTrigger('before', 'shutdown', self.cleanup)

    def cleanup(self):
        logger.info('cleaning up twisted connection')
        return self.p.chan.channel_close()

    def buildProtocol(self, addr):
        self.p = self.protocol(self.delegate, self.vhost, self.spec)
        self.p.factory = self
        # Reset the reconnection delay since we're connected now.
        self.resetDelay()
        return self.p

    # ... WTF?
    def clientConnectionFailed(self, connector, reason):
        print "Connection failed."
        protocol.ReconnectingClientFactory.clientConnectionLost(
            self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        print "Client connection lost."
        self.p = None
        protocol.ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason)

    def add_route(self, routing_key):
        self._routes.add(routing_key)
        if self.p and self.p.connected:
            self.p.routes_updated()

    def remove_route(self, routing_key):
        self._routes.remove(routing_key)
        if self.p and self.p.connected:
            self.p.routes_updated()

    def send(self, routing_key, msg):
        if self.p is not None and self.p.connected:
            self.p.send(routing_key, msg)

    def received(self, msg):
        try:
            body = msg.content.body
            properties = msg.content.properties
            content_type = properties.get('content type', None)
            assert content_type == 'application/json'
            data = json.loads(body)
            command = data['command']
            logger.debug('handling command: %s', command)
            assert command in self.commands
            method = getattr(self, command)
            agent = data.get('agent', None)
            logger.debug('IPC message: %s', body)
            if agent is not None:
                agent_mac = int(data['agent'], base=16)
                handler = self.agentprotocol.handlers.get(agent_mac, None)
                if handler is not None:
                    method(agent_mac, handler, data)
            else:
                method(data)
        except Exception as e:
            logger.warning('Error handling IPC message: %s', e)
            logger.debug('Error handling IPC message: %s, message: %s', e, msg)

    commands = {
        'current_agents',
        'relay_state',
        'control_mode',
        'gridagent_rules',
        'gridagent_software',
        'gridpoint_software',
    }

    def current_agents(self, data):
        logger.info('Connected agents: %s', [
            'agent: %s, serial: %s, sw: %s, hw: %s' % (
                    h.agent_mac, h.serial, h.sw_version, h.hw_revision)
            for h in self.agentprotocol.handlers.values()])

    def relay_state(self, agent_mac, handler, data):
        relay_on = data['relay_on']
        meters = [Meter(m['connection_type'], m['id']) for m in data['meters']]
        for meter in meters:
            message = CommandGpSwitchRelay(meter, relay_on)
            handler.outgoing.put(message)

    def control_mode(self, agent_mac, handler, data):
        control_manual = data['control_manual']
        meters = [Meter(m['connection_type'], m['id']) for m in data['meters']]
        for meter in meters:
            message = CommandGpSwitchControl(meter, control_manual)
            handler.outgoing.put(message)

    def gridagent_software(self, agent_mac, handler, data):
        name_template = 'sw/{}-hw{:02d}_{:02d}_{:02d}{}-' \
            'sw{:02d}_{:02d}_{:02d}{}.hex'
        filename = name_template.format(
            data['hw_model'],
            *(data['target_hw_version'] + data['sw_version']))
        with open(filename) as f:
            image = f.read()
        message = ConfigGaSoftware(clean_version(*data['sw_version']),
                                   data['hw_model'],
                                   clean_version(*data['target_hw_version']),
                                   image)
        handler.outgoing.put(message)

    def gridpoint_software(self, agent_mac, handler, data):
        meters = [Meter(m['connection_type'], m['id']) for m in data['meters']]
        name_template = 'sw/{}-hw{:02d}_{:02d}_{:02d}{}-' \
            'sw{:02d}_{:02d}_{:02d}{}.hex'
        filename = name_template.format(
            data['hw_model'],
            *(data['target_hw_version'] + data['sw_version']))
        with open(filename) as f:
            image = f.read()
        message = ConfigGpSoftware(clean_version(*data['sw_version']),
                                   data['hw_model'],
                                   clean_version(*data['target_hw_version']),
                                   image,
                                   meters)
        handler.outgoing.put(message)

    def gridagent_rules(self, agent_mac, handler, data):
        rulesets = [
            RuleSet(0,
                    [Rule(**rule) for rule in ruleset['rules']],
                    [Meter(**meter) for meter in ruleset['meters']])
            for ruleset in data['rulesets']]

        message = ConfigGaRulesets(rulesets)
        handler.outgoing.put(message)
