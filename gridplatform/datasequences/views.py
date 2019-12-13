# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from rest_framework.response import Response
from rest_framework.templatetags.rest_framework import replace_query_param
from rest_framework.views import APIView

from gridplatform.utils.paginator import parse_date_or_404
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.serializers import RangedSampleSerializer


class HourlyDataView(APIView):
    permission_classes = ()
    method_name = None
    unit_field = 'unit'

    def _get(self, request, datasequence, timezone):
        unit = getattr(datasequence, self.unit_field)
        date_query_param = request.QUERY_PARAMS.get('date')
        date = date_query_param or timezone.normalize(
            datetime.datetime.now(timezone)).date()
        date = parse_date_or_404(date)
        from_timestamp = timezone.localize(
            datetime.datetime.combine(date, datetime.time()))
        to_timestamp = timezone.localize(
            datetime.datetime.combine(
                date + datetime.timedelta(days=1), datetime.time()))
        method = getattr(datasequence, self.method_name)
        data = method(from_timestamp, to_timestamp, RelativeTimeDelta(hours=1))
        serializer = RangedSampleSerializer(
            data, many=True, context={'unit': unit})

        base_url = request and request.build_absolute_uri() or ''
        next_date = datasequence.next_valid_date(date, timezone)
        if next_date:
            next_url = replace_query_param(base_url, 'date', next_date)
        else:
            next_url = None
        previous_date = datasequence.previous_valid_date(date, timezone)
        if previous_date:
            previous_url = replace_query_param(base_url, 'date', previous_date)
        else:
            previous_url = None
        return Response({
            'next': next_url,
            'previous': previous_url,
            'results': serializer.data,
        })
