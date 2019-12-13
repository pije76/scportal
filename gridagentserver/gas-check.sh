#!/bin/bash

cd $(dirname $0)

maxmemusage=$((300*1024))
pidfile='twistd.pid'
if [ -a $pidfile ]; then
    pid=`cat $pidfile`
    mem=`ps --pid $pid -o rss --no-headers`

    if [ -z $mem ]; then
        echo 'GridAgent ERROR: GAS was dead. Reviving it now!'
        source $HOME/ve/bin/activate
        ./start.sh
    else
        if [ $pid -gt $maxmemusage ]; then
            echo 'GridAgent ERROR: GAS used too much memory! Restarting it!'
            source $HOME/ve/bin/activate
            ./stop.sh
            ./start.sh
        fi
    fi
elif [ ! -e $HOME/gas-stopped-intentionally ]; then
    echo 'GridAgent ERROR: GAS was not started. Starting it now!'
    source $HOME/ve/bin/activate
    ./start.sh
fi
