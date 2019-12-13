# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django import forms
from django.http import HttpResponseNotFound
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import floatformat
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST

from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.models import DataSeries
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_user
from gridplatform.users.decorators import auth_or_error, auth_or_redirect
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.views import render_to, json_response
from gridplatform.utils import condense
from legacy.display_widgets.models import DashboardWidget
from legacy.manage_collections.models import CollectionItem
from gridplatform.reports.consumption import consumption_csv


from .tasks import graph_task


accumulation_types = {
    DataSeries.PIECEWISE_CONSTANT_ACCUMULATION,
    DataSeries.CONTINUOUS_ACCUMULATION
}

rate_types = {
    DataSeries.PIECEWISE_CONSTANT_RATE,
    DataSeries.CONTINUOUS_RATE
}


class PeriodForm(forms.Form):
    from_date = forms.DateTimeField()
    to_date = forms.DateTimeField()
    months_limit = None

    BAR_MINUTE_CURVE_RAW = datetime.timedelta(hours=1)
    BAR_HOURS_CURVE_RAW = datetime.timedelta(days=7)
    BAR_DAYS_CURVE_HOURS = datetime.timedelta(days=180)

    def __init__(self, *args, **kwargs):
        self.months_limit = kwargs.pop('months_limit', self.months_limit)
        super(PeriodForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(PeriodForm, self).clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')

        if from_date and to_date:
            if from_date >= to_date:
                raise forms.ValidationError(
                    _('From date must be before to date'))

            if self.months_limit:
                date_span = RelativeTimeDelta(to_date, from_date)
                if date_span.months >= self.months_limit:
                    raise forms.ValidationError(
                        _('The selection has exceeded the limit '
                          'of {limit} months').format(limit=self.months_limit))
            if to_date - from_date < datetime.timedelta(minutes=59):
                raise forms.ValidationError(
                    _('Selection is too small. It must be at least one hour.'))
        return cleaned_data

    def get_period(self):
        assert self.is_valid()
        from_timestamp = self.cleaned_data['from_date']
        to_timestamp = self.cleaned_data['to_date'] + \
            datetime.timedelta(minutes=1)

        duration = to_timestamp - from_timestamp
        if duration <= self.BAR_MINUTE_CURVE_RAW:
            from_timestamp, to_timestamp = self.normalize_range(
                from_timestamp, to_timestamp, RelativeTimeDelta(minutes=1))
        elif duration < self.BAR_HOURS_CURVE_RAW:
            from_timestamp, to_timestamp = self.normalize_range(
                from_timestamp, to_timestamp, RelativeTimeDelta(hours=1))
        elif duration < self.BAR_DAYS_CURVE_HOURS:
            from_timestamp, to_timestamp = self.normalize_range(
                from_timestamp, to_timestamp, RelativeTimeDelta(days=1))
        else:
            from_timestamp, to_timestamp = self.normalize_range(
                from_timestamp, to_timestamp, RelativeTimeDelta(months=1))

        return from_timestamp, to_timestamp

    def normalize_range(self, from_timestamp, to_timestamp, resolution):
        """
        Normalize a datetime range against a relative time delta.
        """
        timezone = get_customer().timezone
        rounded_from_time = condense.floor(
            from_timestamp, resolution, timezone)
        rounded_to_time = condense.floor(to_timestamp, resolution, timezone)
        if rounded_to_time < to_timestamp:
            rounded_to_time = rounded_to_time + resolution
        return (rounded_from_time, rounded_to_time)


@auth_or_redirect
@render_to('display_measurementpoints/index.html')
def index(request):
    customer = request.customer

    root_groups = get_user().userprofile.collections.all()
    if not root_groups:
        root_groups = Collection.objects.root_nodes().filter(customer=customer)

    groups = [group.get_descendants(include_self=True)
              .exclude(hidden_on_details_page=True)
              for group in root_groups]
    return {
        'groups': groups,
    }


@auth_or_redirect
@render_to('display_measurementpoints/group_detail.html')
def group(request, pk):
    period_form = PeriodForm(request.GET)
    customer = get_customer()
    if not period_form.is_valid():
        from_timestamp = condense.floor(
            customer.now(), RelativeTimeDelta(days=1),
            customer.timezone)
        to_timestamp = from_timestamp + RelativeTimeDelta(days=1)
    else:
        from_timestamp, to_timestamp = period_form.get_period()

    if 'from_date' in request.GET:
        from_datetime = request.GET['from_date']
        to_datetime = request.GET['to_date']
    else:
        from_datetime = None
        to_datetime = None

    customer = request.customer

    root_groups = get_user().userprofile.collections.all()
    if root_groups:
        # if user is bound to groups, use those
        groups = [group.get_descendants(include_self=True)
                  .exclude(hidden_on_details_page=True)
                  for group in root_groups]
    else:
        # otherwise, show all groups for customer
        groups = [Collection.objects.filter(customer=customer)
                  .exclude(hidden_on_details_page=True)]

    group_list = [c for grouptree in groups
                  for c in grouptree if c.id == int(pk)]
    if group_list != []:
        group = group_list[0]
    else:
        return HttpResponseNotFound()

    if group.role in Collection.MEASUREMENT_POINTS:
        group = group.subclass_instance

    graphs = list(group.graph_set.filter(hidden=False))
    if to_timestamp - from_timestamp > datetime.timedelta(days=31, hours=1):
        for graph in graphs:
            if graph.role in DataSeries.CONTINUOUS_RATE_ROLES:
                graph.HIDE_HACK = True

    floorplan_items = []

    # You can only have one floorplan per collection
    floorplan = group.get_floorplan()
    if floorplan:
        floorplan_items = [
            item.subclass_instance for item in floorplan.item_set.all()]

    main_graph = None
    if len(graphs) > 0:
        main_graph = graphs.pop(0)

    widgets = DashboardWidget.objects.filter(
        collection=group, user=get_user())

    is_group = False
    if group.role == group.GROUP:
        is_group = True

    return {
        'from_timestamp': from_timestamp,
        'to_timestamp': to_timestamp,
        'group': group,
        'widgets': widgets,
        'relay': group.relay,
        'groups': groups,
        'graphs': graphs,
        'main_graph': main_graph,
        'period_form': period_form,
        'floorplan': floorplan,
        'placed_items': floorplan_items,
        'is_group': is_group,
        'from_date': from_timestamp.strftime('%Y-%m-%d'),
        'to_date': to_timestamp.strftime('%Y-%m-%d'),
        'from_datetime': from_datetime,
        'to_datetime': to_datetime,
    }


@auth_or_redirect
@render_to('display_measurementpoints/fullscreen_floorplan.html')
def fullscreen_floorplan(request, pk):
    customer = request.customer

    root_groups = get_user().userprofile.collections.all()
    if root_groups:
        # if user is bound to groups, use those
        groups = [group.get_descendants(include_self=True)
                  .exclude(hidden_on_details_page=True)
                  for group in root_groups]
    else:
        # otherwise, show all groups for customer
        groups = [Collection.objects.filter(customer=customer)
                  .exclude(hidden_on_details_page=True)]

    group_list = [c for grouptree in groups
                  for c in grouptree if c.id == int(pk)]
    if group_list != []:
        group = group_list[0]
    else:
        return HttpResponseNotFound()

    if group.role in Collection.MEASUREMENT_POINTS:
        group = group.subclass_instance

    floorplan_items = []

    # You can only have one floorplan per collection
    floorplan = group.get_floorplan()
    if floorplan:
        floorplan_items = [
            item.subclass_instance for item in floorplan.item_set.all()]

    return {
        'group': group,
        'floorplan': floorplan,
        'placed_collections': floorplan_items,
    }


@auth_or_error
@json_response
@require_POST
def async_graph(request, pk):
    period_form = PeriodForm(request.POST)
    customer = get_customer()
    if not period_form.is_valid():
        from_timestamp = condense.floor(
            customer.now().replace(minute=0, second=0, microsecond=0),
            RelativeTimeDelta(days=1),
            customer.timezone)
        to_timestamp = from_timestamp + RelativeTimeDelta(days=1)
    else:
        from_timestamp, to_timestamp = period_form.get_period()
        from_timestamp = condense.floor(
            from_timestamp, RelativeTimeDelta(hours=1), customer.timezone)
        to_timestamp = condense.ceil(
            to_timestamp, RelativeTimeDelta(hours=1), customer.timezone)
    customer = request.customer

    current_language = translation.get_language()
    async = graph_task.delay(
        pk, from_timestamp, to_timestamp, current_language)
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

    current_language = translation.get_language()
    async = graph_task.delay(
        pk, from_timestamp, to_timestamp, current_language, 5)
    return {
        'task_id': async.id,
        'status': async.status,
    }


@auth_or_error
@json_response
def floorplan_values(request, pk):
    customer = request.customer
    items = CollectionItem.objects.filter(
        floorplan__collection_id=pk,
        floorplan__collection__customer=customer)
    values = {}
    for item in items:
        last_rate = item.collection.subclass_instance.get_last_rate()
        if last_rate:
            values.update({item.id: [floatformat(float(last_rate[0]), 1),
                                     unicode(last_rate[1])]})
        else:
            values.update({item.id: None})

    return values


def _parse_date(datestring, tzinfo):
    return tzinfo.normalize(datetime.datetime.strptime(
        datestring, '%Y-%m-%d').replace(tzinfo=tzinfo))


@auth_or_error
def export_csv(request, from_date, to_date, name, pk=None):
    customer = get_customer()
    tz = customer.timezone

    from_date = _parse_date(from_date, tz)
    to_date = _parse_date(to_date, tz)

    if pk is not None:
        collection = get_object_or_404(Collection, customer=customer, pk=pk)
        collections = collection.get_descendants(include_self=True)
    else:
        collections = Collection.objects.filter(customer=customer)

    return consumption_csv(collections, from_date, to_date)
