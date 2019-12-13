#!/bin/bash

source $(dirname $0)/base.sh

PIDFILE=$PID_DIR/%n.pid

celery multi stopwait celery_reports --pidfile=$PIDFILE
