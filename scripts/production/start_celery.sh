#!/bin/bash

source $(dirname $0)/base.sh

PIDFILE=$PID_DIR/%n.pid
LOGFILE=%n.log

celery multi start celery --app=gridplatform -Q celery \
    --time-limit=3600 --concurrency=4 \
    --pidfile=$PIDFILE --logfile=$LOGFILE --loglevel=INFO
