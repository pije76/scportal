#!/bin/bash

url='http://127.0.0.1:8000'
if [ ! -z "$QUNIT_SERVER_URL" ]
then
	url=$QUNIT_SERVER_URL
fi

if ! curl --output /dev/null --silent --head --fail "$url"; then
    echo "No server running on ${url}"
    exit
fi


echo 'Running bootstrap tests'
phantomjs qunit/runner.js "${url}/qunit/bootstrap"
echo 'Running utils tests'
phantomjs qunit/runner.js "${url}/qunit/utils"
