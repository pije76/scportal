#!/usr/bin/env python

import pika


mqhost = 'localhost'


def callback(ch, method, properties, body):
    print '%s: %s' % (method.routing_key, body)


def all_agent_messages():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=mqhost))
    channel = connection.channel()
    channel.exchange_declare(exchange='agentservers', exchange_type='topic')
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='agentservers',
                       queue=queue_name,
                       routing_key='agentserver')
    channel.queue_bind(exchange='agentservers',
                       queue=queue_name,
                       routing_key='agent.*')
    channel.basic_consume(callback, queue=queue_name, no_ack=True)
    channel.start_consuming()


if __name__ == '__main__':
    all_agent_messages()
