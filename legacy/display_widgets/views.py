# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import json

from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.db.models import Max
from django.db.models import F
from django.utils.translation import ugettext as _
from django.http import HttpResponseForbidden

from gridplatform.utils.views import render_to
from gridplatform.utils.views import json_response
from gridplatform.trackuser import get_customer
from legacy.measurementpoints.models import Collection
from legacy.indexes.models import Index
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import Graph
from gridplatform.users.decorators import auth_or_error, auth_or_redirect
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils import condense
from legacy.display_widgets.models import DashboardWidget
from gridplatform.trackuser import get_user

from .tasks import gauge_task


@auth_or_error
@json_response
@require_POST
def async_gauge(request, pk):
    widget = get_object_or_404(
        DashboardWidget,
        id=pk)

    customer = get_customer()
    today = customer.now()
    day = RelativeTimeDelta(days=1)
    from_timestamp = condense.floor(today, day, customer.timezone)
    to_timestamp = from_timestamp + day

    async = gauge_task.delay(widget, from_timestamp, to_timestamp)
    return {
        'task_id': async.id,
        'status': async.status,
    }


def generate_widget(request, widget):
    graph = None
    if widget.widget_type == DashboardWidget.CONSUMPTION_GRAPH:
        graph = Graph.objects.get(
            role__in=[
                DataRoleField.CONSUMPTION,
                DataRoleField.REACTIVE_ENERGY,
            ],
            collection__dashboardwidget__id=widget.id)
        template_file = 'display_widgets/consumption_widget.html'
    elif widget.widget_type == DashboardWidget.COOLDOWN_GRAPH:
        graph = Graph.objects.get(role=DataRoleField.MEAN_COOLDOWN_TEMPERATURE,
                                  collection__dashboardwidget__id=widget.id)
        template_file = 'display_widgets/consumption_widget.html'
    elif widget.widget_type == DashboardWidget.PRODUCTION_GRAPH:
        graph = Graph.objects.get(role=DataRoleField.PRODUCTION,
                                  collection__dashboardwidget__id=widget.id)
        template_file = 'display_widgets/consumption_widget.html'
    elif widget.widget_type == DashboardWidget.GAUGE:
        template_file = 'display_widgets/gauge_widget.html'
    elif widget.widget_type == DashboardWidget.INDEX_GRAPH:
        template_file = 'display_widgets/index_widget.html'
    elif widget.widget_type == DashboardWidget.RATE_GRAPH:
        graph = Graph.objects.get(
            role__in=[
                DataRoleField.POWER,
                DataRoleField.VOLUME_FLOW,
                DataRoleField.RELATIVE_TEMPERATURE,
                DataRoleField.ABSOLUTE_TEMPERATURE,
                DataRoleField.CURRENT,
                DataRoleField.VOLTAGE,
                DataRoleField.REACTIVE_POWER,
                DataRoleField.POWER_FACTOR,
            ],
            collection__dashboardwidget__id=widget.id)
        template_file = 'display_widgets/consumption_widget.html'

    return {
        'widget': render_to_string(
            template_file,
            {
                'widget': widget,
                'graph': graph,
            },
            RequestContext(request)),
    }


@auth_or_redirect
@render_to('display_widgets/dashboard.html')
def dashboard(request):
    widgets = DashboardWidget.objects.filter(
        user=get_user()).order_by('row')
    left_widgets = []
    right_widgets = []

    for w in widgets:
        widget_options = generate_widget(request, w)
        if w.column == DashboardWidget.LEFT_COLUMN:
            left_widgets += [widget_options]
        else:
            right_widgets += [widget_options]
    return {
        'left_widgets': left_widgets,
        'right_widgets': right_widgets,
    }


@auth_or_redirect
@render_to('display_widgets/dashboard_fullscreen.html')
def dashboard_fullscreen(request):
    widgets = DashboardWidget.objects.filter(
        user=get_user()).order_by('row')
    left_widgets = []
    right_widgets = []

    for w in widgets:
        widget_options = generate_widget(request, w)
        if w.column == DashboardWidget.LEFT_COLUMN:
            left_widgets += [widget_options]
        else:
            right_widgets += [widget_options]
    return {
        'left_widgets': left_widgets,
        'right_widgets': right_widgets,
    }


@auth_or_error
@json_response
def remove_from_dashboard(request):
    pk = request.GET['id']
    widget = get_object_or_404(DashboardWidget, pk=pk)
    if widget.user != get_user():
        return HttpResponseForbidden()

    widget.delete()

    DashboardWidget.objects.filter(
        column=widget.column, row__gt=widget.row).update(row=F('row') - 1)

    return {
        'statustext': _('The widget has been removed from the dashboard'),
    }


@auth_or_error
@json_response
def remove_specific_widget(request, pk, widget_type):
    widget_type = int(widget_type)
    if widget_type == DashboardWidget.INDEX_GRAPH:
        widget = get_object_or_404(
            DashboardWidget,
            user=get_user(),
            index_id=pk,
            widget_type=widget_type)
    else:
        widget = get_object_or_404(
            DashboardWidget,
            user=get_user(),
            collection_id=pk,
            widget_type=widget_type)

    if widget.user != get_user():
        return HttpResponseForbidden()

    widget.delete()

    DashboardWidget.objects.filter(
        column=widget.column, row__gt=widget.row).update(row=F('row') - 1)

    return {
        'statustext': _('The widget has been removed from the dashboard'),
    }


@auth_or_error
@json_response
def add_to_dashboard(request, pk, widget_type):
    widget_type = int(widget_type)
    if widget_type == DashboardWidget.INDEX_GRAPH:
        widget_object = Index.objects.get(pk=pk)
    else:
        widget_object = Collection.objects.get(pk=pk)
    if widget_object.dashboardwidget_set.filter(
            widget_type=widget_type,
            user=get_user()).exists():
        return {
            'statustext': _('The widget is already on the dashboard'),
        }

    widget = DashboardWidget()
    if widget_type == DashboardWidget.INDEX_GRAPH:
        widget.index = widget_object
    else:
        widget.collection = widget_object

    widget.user = get_user()
    widget.column = DashboardWidget.LEFT_COLUMN
    widget.widget_type = widget_type
    row_max = DashboardWidget.objects.filter(
        user=get_user(),
        column=DashboardWidget.LEFT_COLUMN).aggregate(Max('row'))['row__max']
    if row_max:
        widget.row = row_max + 1
    else:
        widget.row = 1

    widget.save()
    return {
        'statustext': _('The widget has been added to the dashboard'),
    }


@json_response
def update_order(request):
    order = json.loads(request.POST['order'])
    left_column = order[DashboardWidget.LEFT_COLUMN]['widgets']
    right_column = order[DashboardWidget.RIGHT_COLUMN]['widgets']

    def update_widget(id, column, row):
        try:
            widget = DashboardWidget.objects.get(pk=id)
            widget.row = row
            widget.column = column
            widget.save()
            return True
        except DashboardWidget.DoesNotExist:
            return False

    row = 1
    for id in left_column:
        success = update_widget(id, DashboardWidget.LEFT_COLUMN, row)
        row += 1
        if not success:
            return {
                'success': False,
                'statusText':
                _('You need to reload the dashboard before rearanging '
                  'the widgets'),
            }

    row = 1
    for id in right_column:
        success = update_widget(id, DashboardWidget.RIGHT_COLUMN, row)
        row += 1
        if not success:
            return {
                'success': False,
                'statusText':
                _('You need to reload the dashboard before rearanging '
                  'the widgets'),
            }

    return {
        'success': True,
    }
