#!/bin/bash

max_messages_per_queue=100

sudo rabbitmqctl -q list_queues name messages | \
    awk "{ if (\$2 > $max_messages_per_queue) print \"RabbitMQ ERROR: To many messages (\"\$2\") in queue \"\$1}"
