#!/bin/bash

# on deploy, put script in crontab as user, e.g.
# @reboot $HOME/gridplatform/scripts/production_nordic/start_uwsgi.sh

source $(dirname $0)/base.sh

PIDFILE=$PID_DIR/uwsgi.pid

ADDRESS=127.0.0.1:8000
STATS_ADDRESS=127.0.0.1:9000

LOGSIZE=$((8*1024*1024))
LOGFILE=uwsgi.log
BACKUP_LOGFILE=uwsgi.log.bak

PROCESSES=4
THREADS=2

# As an optimisation, --http can be replaced with --socket; if we update nginx
# settings to use uwsgi_pass instead of proxy_pass.

# --log-maxsize enables log rotation --- unless specified otherwise, current
# --log file is moved to file with Unix timestamp as suffix.  To limit the
# --number of files/the disk space utilisation, we specify --log-backupname,
# --with the single file name to be overwritten on rotation.

# --log-x-forwarded-for logs X-Forwarded-For rather than REMOTE_ADDR --- so the
# --address of the client, as specified by nginx, rather than the address of
# --the local nginx.

# --stats lets us fetch server status/stats at the specified address --- which
# --might e.g. be monitored with uwsgitop.  (JSON status dump on TCP
# --connection.)


uwsgi \
  --http=$ADDRESS \
  --wsgi=gridplatform.wsgi:application --need-app \
  --master --processes=$PROCESSES --threads=$THREADS \
  --stats=$STATS_ADDRESS \
  --log-x-forwarded-for \
  --log-master \
  --pidfile=$PIDFILE \
  --env LC_ALL='en_US.UTF-8' \
  --daemonize=$LOGFILE --log-maxsize=$LOGSIZE --log-backupname=$BACKUP_LOGFILE
