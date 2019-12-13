# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import math

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext
from django.http import Http404

from legacy.measurementpoints.models import Collection
from legacy.indexes.models import Index
from legacy.indexes.models import StandardMonthIndex
from legacy.measurementpoints.models import Graph
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_user
from gridplatform.users.decorators import auth_or_error, auth_or_redirect
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.views import render_to, json_response
from legacy.display_measurementpoints.views import PeriodForm
from legacy.display_widgets.models import DashboardWidget
from gridplatform.utils import condense

from .tasks import graph_task


@auth_or_redirect
@render_to('display_indexes/index.html')
def index(request):
    customer = request.customer
    root_groups = get_user().userprofile.collections.filter(
        role=Collection.GROUP)

    if root_groups:
        # if user is bound to groups, use those
        groups = [g
                  for r in root_groups
                  for g in r.get_descendants(include_self=True)]
    else:
        # otherwise, show all groups for customer
        groups = list(Collection.objects.filter(
            customer=customer, role=Collection.GROUP))

    group_ids = [g.id for g in groups]
    global_indexes = list(Index.objects.filter(
        Q(customer=customer) | Q(customer=None)).filter(
        Q(collection__isnull=True) | Q(collection_id__in=group_ids)))
    global_indexes.sort(key=lambda index: unicode(index).lower())

    return {
        'indexes': global_indexes,
    }


@auth_or_redirect
@render_to('display_indexes/index_detail.html')
def detail(request, pk):
    period_form = PeriodForm(request.GET, months_limit=2)
    if not period_form.is_valid():
        from_timestamp = condense.floor(
            get_customer().now(),
            RelativeTimeDelta(days=1),
            get_customer().timezone)
        to_timestamp = from_timestamp + RelativeTimeDelta(days=1)
    else:
        from_timestamp, to_timestamp = period_form.get_period()

    customer = get_customer()
    root_groups = get_user().userprofile.collections.exclude(
        graph__isnull=False).all()
    if root_groups:
        # if user is bound to groups, use those
        groups = [g
                  for r in root_groups
                  for g in r.get_descendants(include_self=True)]
    else:
        # otherwise, show all groups for user
        groups = list(Collection.objects.exclude(graph__isnull=False).filter(
            customer=customer))
    group_ids = [g.id for g in groups]
    global_indexes = Index.objects.filter(
        Q(customer=customer) | Q(customer=None)).filter(
        Q(collection__isnull=True) | Q(collection_id__in=group_ids))

    index = get_object_or_404(global_indexes, pk=pk).subclass_instance
    global_indexes = list(global_indexes)
    global_indexes.sort(key=lambda index: ugettext(index.name_plain).lower())

    is_standard_month = False
    if isinstance(index, StandardMonthIndex):
        is_standard_month = True

    widgets = DashboardWidget.objects.filter(
        index=index, user=get_user())

    return {
        'indexes': global_indexes,
        'id': pk,
        'period_form': period_form,
        'name': index.name_plain,
        'standart_month': is_standard_month,
        'widgets': widgets
    }


def get_ticks(count, maximum):
    return int(math.floor(count / math.ceil(float(count) / float(maximum))))


@auth_or_error
@json_response
@require_POST
def async_graph(request, pk):
    period_form = PeriodForm(request.POST)
    if not period_form.is_valid():
        from_timestamp = condense.floor(
            get_customer().now(),
            RelativeTimeDelta(days=1),
            request.customer.timezone)
        to_timestamp = from_timestamp + RelativeTimeDelta(days=1)
    else:
        from_timestamp, to_timestamp = period_form.get_period()

    async = graph_task.delay(pk, from_timestamp, to_timestamp)
    return {
        'task_id': async.id,
        'status': async.status,
    }


@auth_or_error
@json_response
@require_POST
def async_graph_last_24h(request, pk):
    if not get_customer():
        raise Http404
    to_timestamp = condense.floor(
        request.customer.now() + RelativeTimeDelta(hours=1),
        RelativeTimeDelta(hours=1),
        request.customer.timezone)
    from_timestamp = to_timestamp - RelativeTimeDelta(hours=24)

    async = graph_task.delay(pk, from_timestamp, to_timestamp)
    return {
        'task_id': async.id,
        'status': async.status,
    }


@auth_or_error
@json_response
def graph(request, pk):
    """
    @deprecated: Use the L{async_graph} instead.
    """
    period_form = PeriodForm(request.GET)
    if not period_form.is_valid():
        from_timestamp = condense.floor(
            get_customer().now(), RelativeTimeDelta(days=1),
            get_customer().timezone)
        to_timestamp = from_timestamp + RelativeTimeDelta(days=1)
    else:
        from_timestamp, to_timestamp = period_form.get_period()
    customer = request.customer

    qs = Index.objects.filter(Q(customer=customer) | Q(customer=None))
    root_groups = get_user().userprofile.collections.all()
    if root_groups:
        # if user is restricted to groups, filter...
        groups = [group.get_descendants(include_self=True)
                  for group in root_groups]
        group_ids = [c.id for grouptree in groups
                     for c in grouptree]
        qs = qs.filter(Q(collection_id__isnull=True) |
                       Q(collection_id__in=group_ids))
    index = get_object_or_404(qs, pk=pk).subclass_instance

    class RuntimeGraph(Graph):
        class Meta:
            proxy = True

        def __init__(self, index, *args, **kwargs):
            super(RuntimeGraph, self).__init__(*args, **kwargs)
            self.index = index

    graph = RuntimeGraph(index)

    days = int((to_timestamp - from_timestamp).total_seconds() /
               datetime.timedelta(days=1).total_seconds())

    if isinstance(index, StandardMonthIndex):
        result = graph.get_graph_data(
            12, from_timestamp, num_samples=12,
            sample_resolution=RelativeTimeDelta(months=1),
            data_series_set=[index])
    else:
        if days <= 1:
            # display hours
            hours = int((to_timestamp - from_timestamp).total_seconds() / 3600)
            result = graph.get_graph_data(
                get_ticks(hours, 12), from_timestamp,
                to_timestamp=to_timestamp,
                data_series_set=[index])

        elif days < 31:
            # display hours
            result = graph.get_graph_data(
                get_ticks(days, 12), from_timestamp,
                to_timestamp=to_timestamp,
                data_series_set=[index])
        else:
            result = graph.get_graph_data(
                get_ticks(days, 12), from_timestamp,
                to_timestamp=to_timestamp,
                data_series_set=[index])

    result["options"].update({"grid": {"outlineWidth": 0,
                                       "verticalLines": True}})
    result["options"]["yaxis"].update({"titleAngle": 90})
    result["options"].update({"HtmlText": False})

    return result
