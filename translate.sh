#!/bin/bash

if [ -z "$VIRTUAL_ENV" ]
then
    echo 'Missing (virtual) Python env'
    exit 1
fi

cd `dirname $0`

make makemessages -j6 LOCALES="da"

HAS_FUZZY=""
HAS_UNTRANSLATED=""
for FILE in $(find gridplatform energymanager legacy \( -name django.po -o -name djangojs.po \) | grep "locale/da")
do
    if [ -n "`msgattrib $FILE --only-fuzzy`" ]
    then
        HAS_FUZZY="$HAS_FUZZY $FILE"
    fi
    if [ -n "`msgattrib $FILE --untranslated`" ]
    then
        HAS_UNTRANSLATED="$HAS_UNTRANSLATED $FILE"
    fi
done

TO_EDIT=`(for NAME in $HAS_FUZZY $HAS_UNTRANSLATED; do echo $NAME; done) | sort | uniq`

if [ -n "$TO_EDIT" ]
then
    editor $TO_EDIT
fi

make compilemessages -j6 LOCALES="da"
