#!/bin/bash

cd $(dirname $0)
cd ../../

source ../ve/bin/activate

export DJANGO_SETTINGS_MODULE="gridplatform.settings.production"

export PID_DIR=$(readlink --canonicalize ..)
