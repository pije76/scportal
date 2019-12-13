# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import template
from django.utils.encoding import iri_to_uri


register = template.Library()

MAX_PAGE_CHOICES = 9


@register.simple_tag
def pagination_max_page_choices():
    return MAX_PAGE_CHOICES


@register.filter
def pagination_page_choices(paginator, page_obj):
    if paginator.num_pages < MAX_PAGE_CHOICES:
        return paginator.page_range

    first = page_obj.number - MAX_PAGE_CHOICES / 2
    last = page_obj.number + MAX_PAGE_CHOICES / 2
    if first < 1:
        first = 1
        last = MAX_PAGE_CHOICES + 1
    elif last > paginator.num_pages:
        first = paginator.num_pages - MAX_PAGE_CHOICES
        last = paginator.num_pages
    else:
        first -= 1
    return paginator.page_range[first:last]


@register.simple_tag(takes_context=True)
def page_url(context, n):
    request = context['request']
    query = [(k, v) for k, v in request.GET.iteritems() if k != 'page'] + \
        [('page', n)]
    querystring = '&'.join(['%s=%s' % (k, v) for k, v in query])
    return '%s?%s' % (request.path, iri_to_uri(querystring))
