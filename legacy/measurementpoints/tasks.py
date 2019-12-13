# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from celery import shared_task

from gridplatform.trackuser.tasks import trackuser_task


@trackuser_task
@shared_task(
    name='legacy.measurementpoints.tasks.get_condensed_samples_task')
def get_condensed_samples_task(
        data_series_id, from_timestamp, to_timestamp, resolution):
    """
    Celery task that collect condensed samples for a DataSeries at within a
    given timespan at a given C{resolution}.

    @param data_series_id: The C{id} of the L{DataSeries} to collect condensed
    samples.

    @param from_timestamp: The start of the timespan.

    @param to_timestamp: The end of the timespan.
    """
    from .models import DataSeries
    data_series = DataSeries.objects.get(id=data_series_id).subclass_instance
    return list(
        data_series.get_condensed_samples(
            from_timestamp, resolution, to_timestamp))


@trackuser_task
@shared_task(name='legacy.measurementpoints.tasks.get_samples_task')
def get_samples_task(data_series_id, from_timestamp, to_timestamp):
    """
    Celery task that collect samples for a DataSeries at within a given
    timespan.

    @param data_series_id: The C{id} of the L{DataSeries} to collect condensed
    samples.

    @param from_timestamp: The start of the timespan.

    @param to_timestamp: The end of the timespan.
    """
    from .models import DataSeries
    data_series = DataSeries.objects.get(id=data_series_id).subclass_instance
    return list(data_series.get_samples(from_timestamp, to_timestamp))
