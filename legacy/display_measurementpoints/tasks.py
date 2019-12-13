# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import math

from django.shortcuts import get_object_or_404
from django.utils import translation

from celery import shared_task

from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from legacy.measurementpoints.models import Graph
from legacy.measurementpoints.proxies import ConsumptionMeasurementPointSummation  # noqa
from legacy.measurementpoints.proxies import ConsumptionMultiplicationPoint
from legacy.measurementpoints.models import DataSeries
from gridplatform.trackuser.tasks import trackuser_task
from gridplatform.trackuser import get_customer


def get_ticks(count, maximum):
    return int(math.floor(count / math.ceil(float(count) / float(maximum))))


def is_clock_hour(timestamp):
    return timestamp.minute == timestamp.second == timestamp.microsecond == 0


@trackuser_task
@shared_task(name='legacy.display_measurementpoints.tasks.graph_task')
def graph_task(pk, from_timestamp, to_timestamp, language, num_tics=None):
    assert is_clock_hour(from_timestamp)
    assert is_clock_hour(to_timestamp)

    graph = get_object_or_404(
        Graph, collection__customer__id=get_customer().id, pk=pk)

    translation.activate(language)

    delta = RelativeTimeDelta(to_timestamp, from_timestamp)
    months = delta.years * 12 + delta.months

    days = int(round((to_timestamp - from_timestamp).total_seconds() /
               datetime.timedelta(days=1).total_seconds()))

    is_multiplication_or_summation = isinstance(
        graph.collection.subclass_instance,
        (
            ConsumptionMeasurementPointSummation,
            ConsumptionMultiplicationPoint))
    if days <= 7:
        # display hours
        hours = int((to_timestamp - from_timestamp).total_seconds() /
                    datetime.timedelta(hours=1).total_seconds())

        if graph.role in DataSeries.CONTINUOUS_RATE_ROLES:
            if hours == 0:
                minutes = int(
                    (to_timestamp - from_timestamp).total_seconds() / 60)
                result = graph.get_graph_data(
                    get_ticks(minutes, num_tics or 30),
                    from_timestamp, to_timestamp=to_timestamp)
            elif hours > 24:
                if is_multiplication_or_summation:
                    result = graph.get_graph_data(
                        get_ticks(hours, num_tics or 10),
                        from_timestamp, hours * 60 / 5,
                        RelativeTimeDelta(minutes=5))
                else:
                    # up to 10080 samples across 1000 pixels. VERRY
                    # BAD
                    result = graph.get_graph_data(
                        get_ticks(hours, num_tics or 10),
                        from_timestamp, to_timestamp=to_timestamp)
            else:
                if is_multiplication_or_summation:
                    result = graph.get_graph_data(
                        get_ticks(hours, num_tics or 12),
                        from_timestamp, hours * 60 / 5,
                        RelativeTimeDelta(minutes=5))
                else:
                    # up to 1440 samples across 1000 pixels. BAD
                    result = graph.get_graph_data(
                        get_ticks(hours, num_tics or 12),
                        from_timestamp,
                        to_timestamp=to_timestamp)
        else:
            if hours == 0:
                minutes = int(
                    (to_timestamp - from_timestamp).total_seconds() / 60)
                result = graph.get_graph_data(
                    get_ticks(minutes, num_tics or 30),
                    from_timestamp, minutes,
                    RelativeTimeDelta(minutes=1))
            elif hours > 24:
                result = graph.get_graph_data(
                    get_ticks(hours, num_tics or 10),
                    from_timestamp, hours,
                    RelativeTimeDelta(hours=1))
            else:
                result = graph.get_graph_data(
                    get_ticks(hours, num_tics or 10), from_timestamp,
                    hours,
                    RelativeTimeDelta(hours=1))

    elif days < 32:
        # display days
        hours = int((to_timestamp - from_timestamp).total_seconds() /
                    datetime.timedelta(hours=1).total_seconds())
        if graph.role in DataSeries.CONTINUOUS_RATE_ROLES:
            # up to 768 samples across 1000 pixels. OK
            result = graph.get_graph_data(
                get_ticks(days, num_tics or 15),
                from_timestamp, hours,
                RelativeTimeDelta(hours=1))
        else:
            result = graph.get_graph_data(
                get_ticks(days, num_tics or 15),
                from_timestamp,
                days, RelativeTimeDelta(days=1))

    elif days < 180:
        # display days
        hours = int((to_timestamp - from_timestamp).total_seconds() /
                    datetime.timedelta(hours=1).total_seconds())
        if graph.role in DataSeries.CONTINUOUS_RATE_ROLES:
            # up to 4320 samples across 1000 pixels. VERRY BAD
            result = graph.get_graph_data(
                get_ticks(days, num_tics or 10),
                from_timestamp,
                hours, RelativeTimeDelta(hours=1))
        else:
            result = graph.get_graph_data(
                get_ticks(days, num_tics or 12),
                from_timestamp, days,
                RelativeTimeDelta(days=1))
    else:
        # display months
        if graph.role in DataSeries.CONTINUOUS_RATE_ROLES:
            # up to 1825 samples across 1000 pixels (assuming
            # expected maximum is 5 years). For 2 years, this
            # sample accumulation rate seem quite adequate. OK.
            result = graph.get_graph_data(
                get_ticks(months, num_tics or 11),
                from_timestamp, days,
                RelativeTimeDelta(days=1))
        else:
            result = graph.get_graph_data(
                get_ticks(months, num_tics or 11),
                from_timestamp,
                months, RelativeTimeDelta(months=1))

    result["options"].update({"grid": {"outlineWidth": 0,
                              "verticalLines": True}})
    result["options"]["yaxis"].update({"titleAngle": 90})
    result["options"].update({"HtmlText": False})
    return result
