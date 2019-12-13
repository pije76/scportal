#!/bin/bash

for d in `find gridplatform -maxdepth 1 -type d`
do
    if [ $d = 'gridplatform' ]
    then
        continue
    fi
    cd $d
    django-admin.py compilemessages
    cd -
done
