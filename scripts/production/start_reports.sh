#!/bin/bash

source $(dirname $0)/base.sh

PIDFILE=$PID_DIR/%n.pid
LOGFILE=%n.log

celery multi start celery_reports --app=gridplatform -Q reports \
    --time-limit=3600 --concurrency=2 \
    --pidfile=$PIDFILE --logfile=$LOGFILE --loglevel=INFO
