#!/bin/bash

cd `dirname $0`

python -m unittest discover -p '**_test.py'

# unit test library from twisted...
trial gridagentserver_protocol.twisted_protocol_test
