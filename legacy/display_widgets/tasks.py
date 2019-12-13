# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404

from celery import shared_task

from legacy.measurementpoints.proxies import MeasurementPoint
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.trackuser.tasks import trackuser_task


@trackuser_task
@shared_task(name='legacy.display_widgets.tasks.gauge_task')
def gauge_task(widget, from_timestamp, to_timestamp):
    """
    @bug: What is the desired return values when no data is available.  A
    today_min of 0 might be violating gauge_min, so it is in no way neutral to
    replace missing values with 0.  On the other hand, if the interpolation
    later shows that the gauge thresholds were violated at a certain time, it
    would be eroneuous to have the gauge indicate anything different.
    """
    measurement_point = get_object_or_404(
        MeasurementPoint.objects.subclass_only(),
        id=widget.collection_id).subclass_instance

    gauge_lower_threshold = measurement_point.gauge_lower_threshold
    gauge_upper_threshold = measurement_point.gauge_upper_threshold
    gauge_min = measurement_point.gauge_min
    gauge_max = measurement_point.gauge_max
    today_avg, today_min, today_max = \
        measurement_point.get_gauge_data_series().aggregated_samples(
            from_timestamp, to_timestamp)
    last_rate = measurement_point.get_gauge_data_series().latest_sample(
        from_timestamp, to_timestamp)
    gauge_unit = widget.collection.gauge_preferred_unit

    preferred_unit_converter = measurement_point.rate.\
        get_preferred_unit_converter()

    if last_rate is None:
        return {
            'last_rate': None,
            'minimum': float(
                preferred_unit_converter.extract_value(
                    PhysicalQuantity(gauge_min, gauge_unit))),
            'low': float(
                preferred_unit_converter.extract_value(
                    PhysicalQuantity(gauge_lower_threshold, gauge_unit))),
            'high': float(
                preferred_unit_converter.extract_value(
                    PhysicalQuantity(
                        gauge_upper_threshold, gauge_unit))),
            'maximum': float(
                preferred_unit_converter.extract_value(
                    PhysicalQuantity(gauge_max, gauge_unit))),
            'color': widget.collection.gauge_colours,
            'unit': unicode(preferred_unit_converter.get_display_unit()),
            'today_min': None,
            'today_max': None,
            'today_avg': None}
    else:
        return {
            'last_rate': float(
                preferred_unit_converter.extract_value(
                    last_rate.physical_quantity)),
            'minimum': float(
                preferred_unit_converter.extract_value(
                    PhysicalQuantity(gauge_min, gauge_unit))),
            'low': float(
                preferred_unit_converter.extract_value(
                    PhysicalQuantity(gauge_lower_threshold, gauge_unit))),
            'high': float(
                preferred_unit_converter.extract_value(
                    PhysicalQuantity(gauge_upper_threshold, gauge_unit))),
            'maximum': float(
                preferred_unit_converter.extract_value(
                    PhysicalQuantity(gauge_max, gauge_unit))),
            'color': widget.collection.gauge_colours,
            'unit': unicode(preferred_unit_converter.get_display_unit()),
            'today_min': round(
                float(
                    preferred_unit_converter.extract_value(
                        today_min.physical_quantity)),
                3),
            'today_max': round(
                float(
                    preferred_unit_converter.extract_value(
                        today_max.physical_quantity)),
                3),
            'today_avg': round(
                float(
                    preferred_unit_converter.extract_value(
                        today_avg.physical_quantity)),
                3),
        }
