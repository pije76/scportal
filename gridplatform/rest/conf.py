# -*- coding: utf-8 -*-
"""
These settings control the view names and namespaces used for the REST API.

.. data:: settings.REST_API_NAMESPACE = 'api'

    URL namespace used to generically define view names when combined with
    :data:`settings.REST_SERIALIZER_VIEW_NAME_BASE` and generic postfixes such
    as ``'-list'`` or ``'-detail'``.

.. data:: settings.REST_SERIALIZER_VIEW_NAME_BASE = '%(app_label)s:%(model_name)s'

    Format string used to generically define base of view names of REST views.  Will be
    formatted with the arguments ``app_label`` and ``model_name``.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

from appconf import AppConf
from django.conf import settings


__all__ = ['settings', 'RestConf']


class RestConf(AppConf):

    class Meta:
        prefix = 'rest'

    API_NAMESPACE = 'api'
    SERIALIZER_VIEW_NAME_BASE = '%(app_label)s:%(model_name)s'
