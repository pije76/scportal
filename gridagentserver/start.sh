#!/bin/bash

cd `dirname $0`

twistd -y agentserver.tac
rm -f $HOME/gas-stopped-intentionally
