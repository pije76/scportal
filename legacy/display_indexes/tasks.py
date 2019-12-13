# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import math

from django import template
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import floatformat
from django.utils.translation import ugettext as _

from celery import shared_task

from legacy.measurementpoints.models import Graph
from legacy.indexes.models import Index
from gridplatform.trackuser.tasks import trackuser_task


def get_ticks(count, maximum):
    return int(math.floor(count / math.ceil(float(count) / float(maximum))))


@trackuser_task
@shared_task(name='legacy.display_indexes.tasks.graph_task')
def graph_task(pk, from_timestamp, to_timestamp):
    index = get_object_or_404(Index, pk=pk).subclass_instance

    class RuntimeGraph(Graph):
        class Meta:
            proxy = True

        def __init__(self, index, *args, **kwargs):
            super(RuntimeGraph, self).__init__(*args, **kwargs)
            self.index = index

        def _get_caption_text(self, data_samples, converter, is_rate,
                              is_condensed):
            """
            Override of L{AbstractGraph._condense_caption_text}.

            @note: The is_condensed paramter is ignored for index so far.

            """
            floatformat_decimals = '-3'
            if is_rate:
                if data_samples:
                    min_value = min(
                        sample.physical_quantity for sample in data_samples)

                    max_value = max(
                        sample.physical_quantity for sample in data_samples)

                    caption = _('Min: {{ min_value }} {{ unit }} | '
                                'Max: {{ max_value }} {{ unit }}')
                    subcontext = template.Context({
                        'min_value': converter.extract_value(min_value),
                        'max_value': converter.extract_value(max_value),
                        'unit': converter.get_display_unit()})
                else:
                    subcontext = template.Context({})
                    caption = _('No values in this range.')

            for elem in ['min_value', 'max_value']:
                if elem in subcontext:
                    subcontext[elem] = floatformat(
                        subcontext[elem], floatformat_decimals)
            return template.Template(unicode(caption)).render(subcontext)

    graph = RuntimeGraph(index)

    days = int((to_timestamp - from_timestamp).total_seconds() /
               datetime.timedelta(days=1).total_seconds())

    if days <= 1:
        hours = int((to_timestamp - from_timestamp).total_seconds() / 3600)
        result = graph.get_graph_data(
            get_ticks(hours, 5), from_timestamp,
            to_timestamp=to_timestamp, data_series_set=[index])

    elif days < 31:
        # display hours
        result = graph.get_graph_data(
            get_ticks(days, 12),
            from_timestamp, to_timestamp=to_timestamp,
            data_series_set=[index])
    else:
        result = graph.get_graph_data(
            get_ticks(days, 12), from_timestamp,
            to_timestamp=to_timestamp, data_series_set=[index])

    result["options"].update({"grid": {"outlineWidth": 0,
                                       "verticalLines": True}})
    result["options"]["yaxis"].update({"titleAngle": 90})
    result["options"].update({"HtmlText": False})
    return result
