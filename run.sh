#!/bin/bash

if [ -z "$VIRTUAL_ENV" ]
then
    . ../ve/bin/activate
fi

cd ~/gridplatform
./manage.py runserver 0.0.0.0:8000