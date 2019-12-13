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

echo 'Clearing memcached (old sessions...)'
echo 'flush_all' | telnet localhost 11211

set -e

echo 'Clearing pyc-files'
find . -name '*.pyc' -delete

echo 'Setting up tables'
gunzip -c initial.sql.gz | psql portal > /dev/null
./manage.py migrate --all --noinput --traceback
./manage.py fix_contenttypes_and_permissions

echo 'Adding "fixture" data'
python fixture_hack.py
#python measurement_fixture.hack.py
#./manage.py loaddata salestool_data
echo 'done'
