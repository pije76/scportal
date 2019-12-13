# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

# from django import template
# from django.utils import simplejson
# from django.utils.safestring import mark_safe

# from ..models import Dashboard
# from ..views import dashboard_data

# register = template.Library()


# @register.simple_tag(takes_context=True)
# def user_dashboard(context):
#     request = context['request']
#     user = context['user']
#     try:
#         dashboard = Dashboard.objects.prefetch_related(
#             'container_set',
#             'container_set__element_set',
#             'container_set__element_set__content_object'
#         ).get(user=user, type=Dashboard.DASHBOARD)
#     except Dashboard.DoesNotExist:
#         dashboard = Dashboard.objects.create(
#             user=user, type=Dashboard.DASHBOARD)
#     return mark_safe(simplejson.dumps(dashboard_data(request, dashboard)))


# @register.simple_tag(takes_context=True)
# def user_sidepane(context):
#     request = context['request']
#     user = context['user']
#     try:
#         dashboard = Dashboard.objects.prefetch_related(
#             'container_set',
#             'container_set__element_set',
#             'container_set__element_set__content_object'
#         ).get(user=user, type=Dashboard.SIDEPANE)
#     except Dashboard.DoesNotExist:
#         dashboard = Dashboard.objects.create(
#             user=user, type=Dashboard.SIDEPANE)
#     return mark_safe(simplejson.dumps(dashboard_data(request, dashboard)))
