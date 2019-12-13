from string import hexdigits
from struct import Struct
import json
import re

import pika


mqhost = 'engine.grid-manager.com'
#mqhost = 'localhost'


def send_message(routing_key, message, verbose=False, dry_run=False):
    if not dry_run:
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=mqhost))
        channel = connection.channel()
        channel.exchange_declare(exchange='agentservers',
                                 exchange_type='topic')
        channel.basic_publish(exchange='agentservers',
                              routing_key=routing_key,
                              properties=pika.BasicProperties(
                                  content_type='application/json'),
                              body=json.dumps(message))
        connection.close()
    if verbose:
        print 'message:\n%s\n(routing key %s)' % (
            json.dumps(message, indent=2), routing_key)
        if dry_run:
            print '(not sent)'
        else:
            print '(sent)'


def normalise_mac(mac, bytes=6):
    norm = filter(lambda c: c in hexdigits, mac.lower())
    if len(norm) != bytes * 2:
        raise Exception('invalid mac address %s (%s)' % (mac, norm))
    return norm


number_splitter = re.compile(r'^(\d+)(.*)$')


def normalise_version(version):
    major, minor, revision = version.split('.')
    revision, extra = number_splitter.match(revision).groups()
    return (int(major), int(minor), int(revision), extra)


uint64 = Struct('!Q')
int64 = Struct('!q')


def gridpoint_id(mac):
    n = int(mac, base=16)
    m, = int64.unpack(uint64.pack(n))
    # 1 for connection type ZigBee
    return {'connection_type': 1, 'id': m}
