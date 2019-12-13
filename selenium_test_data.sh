#!/bin/bash

if [ -z "$VIRTUAL_ENV" ]
then
    echo "ERROR: virtualenv not active"
    exit -1
fi

# sudo -u postgres dropdb portal
if [ "$(uname)" == "Darwin" ]
then
    dropdb -h localhost portal
else
    dropdb portal
fi

if [ $? -ne 0 ]
then
    echo "ERROR: failed to drop database"
    exit -1
fi

# sudo -u postgres createdb -O $USER portal
if [ "$(uname)" == "Darwin" ]
then
    createdb -h localhost -E utf8 portal
else
    createdb -E utf8 portal
fi
if [ $? -ne 0 ]
then
    echo "ERROR: failed to recreate database"
    exit -1
fi

echo 'Setting up tables'
./manage.py syncdb --noinput --traceback
./manage.py migrate --all --traceback

echo 'Setting up test data'
python selenium_test_data.py
