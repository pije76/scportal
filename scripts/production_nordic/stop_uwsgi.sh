#!/bin/bash

source $(dirname $0)/base.sh

PIDFILE=$PID_DIR/uwsgi.pid

# the default signal for kill is TERM, which causes uWSGI to "reload"
kill -INT $(cat $PIDFILE)
