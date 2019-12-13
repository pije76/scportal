#!/bin/bash

cd `dirname $0`

if [ -e twistd.pid ]
then
    kill `cat twistd.pid`
fi
touch $HOME/gas-stopped-intentionally
