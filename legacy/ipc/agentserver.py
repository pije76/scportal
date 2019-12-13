# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import json

import pika
from django.conf import settings

logger = logging.getLogger(__name__)


# 1 for connection type ZigBee
def gridpoint_id(connection_type, nid):
    return {'connection_type': connection_type, 'id': nid}


def format_mac(mac):
    return '{:012x}'.format(int(mac))


def agent_routing_key(agent_mac):
    return 'agent.{:012x}'.format(int(agent_mac))


def send_message(routing_key, message):
    connection = pika.BlockingConnection(pika.URLParameters(
        str(settings.BROKER_URL)))
    channel = connection.channel()
    channel.exchange_declare(exchange='agentservers', exchange_type='topic')
    channel.basic_publish(
        exchange='agentservers',
        routing_key=routing_key,
        properties=pika.BasicProperties(
            content_type='application/json'),
        body=json.dumps(message))
    connection.close()
    logger.debug('sent; routing key: %s, message: %s', routing_key, message)


def control_mode(agent_mac, meters, control_manual):
    routing_key = agent_routing_key(agent_mac)
    message = {
        'command': 'control_mode',
        'agent': format_mac(agent_mac),
        'control_manual': bool(control_manual),
        'meters': [gridpoint_id(connection_type, nid)
                   for connection_type, nid in meters],
    }
    send_message(routing_key, message)


def relay_state(agent_mac, meters, relay_on):
    routing_key = agent_routing_key(agent_mac)
    message = {
        'command': 'relay_state',
        'agent': format_mac(agent_mac),
        'relay_on': bool(relay_on),
        'meters': [gridpoint_id(connection_type, nid)
                   for connection_type, nid in meters],
    }
    send_message(routing_key, message)


def agent_swupdate(agent_mac, software_image):
    sw_version = (software_image.sw_major, software_image.sw_minor,
                  software_image.sw_revision, software_image.sw_subrevision)
    hw_version = (software_image.hw_major, software_image.hw_minor,
                  software_image.hw_revision, software_image.hw_subrevision)
    routing_key = agent_routing_key(agent_mac)
    message = {
        'command': 'gridagent_software',
        'agent': format_mac(agent_mac),
        'sw_version': sw_version,
        'hw_model': software_image.device_type,
        'target_hw_version': hw_version,
    }
    send_message(routing_key, message)


def agent_rules(agent_mac, rulesets):
    rulesets = [{'meters': [gridpoint_id(connection_type, nid)
                            for connection_type, nid in meters],
                 'rules': [{'start_time': start_time,
                            'end_time': end_time,
                            'relay_on': relay_on}
                           for start_time, end_time, relay_on in rules]}
                for meters, rules in rulesets]
    routing_key = agent_routing_key(agent_mac)
    message = {
        'command': 'gridagent_rules',
        'agent': format_mac(agent_mac),
        'rulesets': rulesets,
    }
    send_message(routing_key, message)
