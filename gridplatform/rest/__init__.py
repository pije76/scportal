# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db.models.deletion import ProtectedError
from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.response import Response

def gridplatform_rest_api_exception_handler(exception):
    response = exception_handler(exception)

    if response is None:
        if isinstance(exception, ProtectedError):
            return Response(
                {'detail': unicode(exception)},
                status=status.HTTP_409_CONFLICT)

    return response
