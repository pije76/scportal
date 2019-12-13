# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from cStringIO import StringIO
import contextlib
import datetime
import fractions
import gzip

from django.template.defaultfilters import floatformat
from django.utils.translation import ugettext as _

from celery import current_task
from celery import shared_task

from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from gridplatform.reports.csv import generate_csv
from gridplatform.trackuser import get_customer
from gridplatform.trackuser.tasks import trackuser_task
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.unitconversion import PhysicalQuantity
from legacy.energy_use_reports.tasks import DataCollectionError
from legacy.measurementpoints.models import DataSeries
from legacy.measurementpoints.models import Graph


@trackuser_task
@shared_task(
    time_limit=1860, soft_time_limit=1800,
    name='gridplatform.reports.tasks.graphdata_download_task')
def graphdata_download_task(data):
    from_timestamp = data['from_timestamp']
    to_timestamp = data['to_timestamp']
    graph_id = data['graph']
    graph = Graph.objects.get(
        collection__customer_id=get_customer().id, pk=graph_id)
    data = []
    for data_series in graph.dataseries_set.all():
        if PhysicalQuantity.compatible_units(data_series.unit, 'watt'):
            samples = data_series.subclass_instance.get_samples(
                from_timestamp, to_timestamp=to_timestamp)
        else:
            samples = data_series.get_condensed_samples(
                from_timestamp, RelativeTimeDelta(hours=1),
                to_timestamp=to_timestamp)
        data.append({
            'dataseries_id': data_series.id,
            'samples': list(samples),
        })

    tz = from_timestamp.tzinfo

    def format_time(val):
        normalized = tz.normalize(val.astimezone(tz))
        # Using danish date format to satisfy import requirements
        return normalized.strftime("%d-%m-%Y %H:%M")

    def format(val):
        if isinstance(val, datetime.datetime):
            normalized = tz.normalize(val.astimezone(tz))
            return normalized.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(val, fractions.Fraction):
            return float(val)
        else:
            return val

    lines = []
    for entry in data:
        dataseries_id = entry['dataseries_id']
        dataseries = DataSeries.objects.get(pk=dataseries_id)
        converter = dataseries.get_preferred_unit_converter()
        lines.append([_(u"Data series for {data_series_name}").format(
            data_series_name=dataseries.get_role_display())])
        lines.append(["---"])
        samples = entry['samples']
        for sample in samples:
            line = [
                format_time(sample.from_timestamp) + ' - ' +
                format_time(sample.to_timestamp),
                floatformat(
                    float(
                        converter.extract_value(
                            sample.physical_quantity)), 6),
                unicode(
                    dataseries.get_preferred_unit_converter().
                    get_display_unit()),
            ]
            lines.append(line)
    csvfilename = '{}.csv'.format(graph)
    with contextlib.closing(StringIO()) as f:
        gz = gzip.GzipFile(mode='wb', fileobj=f)
        gz.write(generate_csv(lines))
        gz.close()

        return {
            'csvfilename': csvfilename,
            'gzippedfile': f.getvalue(),
        }


# Softly kill using exception after 30 minutes. Kill for real after 31 minutes.
@trackuser_task
@shared_task(
    time_limit=1860, soft_time_limit=1800,
    name='gridplatform.reports.tasks.collect_consumption_data')
def collect_consumption_data(mp_ids, from_timestamp, to_timestamp, from_date,
                             to_date, include_cost):
    measurementpoints = \
        ConsumptionMeasurementPoint.objects.subclass_only().filter(
            id__in=mp_ids).select_related('customer')
    mp_data = {}
    errors = []
    include_degree_days_corrected = False

    for i, mp in enumerate(measurementpoints):
        current_task.update_state(state='PROGRESS',
                                  meta={'current': i,
                                        'total': len(measurementpoints)})
        if mp.consumption:
            ds = mp.consumption
            preferred_unit_converter = ds.get_preferred_unit_converter()
            assert ds.is_accumulation()

            development = ds.calculate_development(
                from_timestamp, to_timestamp)
            if development is not None:
                consumption = preferred_unit_converter.extract_value(
                    development.physical_quantity)
                if development.extrapolated:
                    errors.append(
                        DataCollectionError(
                            _('Consumption for {measurement_point} is '
                              'calculated from incomplete data.'),
                            measurement_point=mp))
            else:
                consumption = 0
                assert development is None
                errors.append(
                    DataCollectionError(
                        _('Consumption and therefore also cost is undefined '
                          'for {measurement_point}'),
                        measurement_point=mp))

            if mp.heating_degree_days_corrected_consumption is not None:
                include_degree_days_corrected = True
                cds = mp.heating_degree_days_corrected_consumption
                corrected_development = cds.calculate_development(
                    from_timestamp, to_timestamp)
                if corrected_development is not None:
                    if corrected_development.extrapolated:
                        errors.append(
                            DataCollectionError(
                                _('Heating degree days corrected consumption '
                                  'for {measurement_point} is calculated '
                                  'from incomplete data'),
                                measurement_point=mp))
                    corrected_consumption = \
                        preferred_unit_converter.extract_value(
                            corrected_development.physical_quantity)
                else:
                    corrected_consumption = None
                    errors.append(
                        DataCollectionError(
                            _('Heating degree days corrected consumption '
                              'undefined for '
                              '{measurement_point}'),
                            mp))
            else:
                corrected_consumption = None

            cost = None
            currency_unit = None
            if include_cost:
                if mp.cost is not None:
                    costds = mp.cost
                    currency_unit = costds.unit
                    cost_development = costds.calculate_development(
                        from_timestamp, to_timestamp)
                    if cost_development is not None:
                        cost_preferred_unit_converter = \
                            costds.get_preferred_unit_converter()
                        cost = cost_preferred_unit_converter.extract_value(
                            cost_development.physical_quantity)
                        if cost_development.extrapolated:
                            errors.append(
                                DataCollectionError(
                                    _('Cost for {measurement_point} is '
                                      'calculated from incomplete data'),
                                    measurement_point=mp))
                    else:
                        cost = 0
                        errors.append(
                            DataCollectionError(
                                _('Cost undefined for '
                                  '{measurement_point}'),
                                mp))
                else:
                    assert mp.cost is None
                    errors.append(
                        DataCollectionError(
                            _('Unable to calculate cost for '
                              '{measurement_point} '
                              'because it has no tariff attached.'),
                            measurement_point=mp))
            else:
                cost = None
                currency_unit = None
            mp_data[mp.id] = {
                'unit': preferred_unit_converter.physical_unit,
                'consumption': consumption,
                'degreedays_corrected_consumption': corrected_consumption,
                'cost': cost,
                'currency_unit': currency_unit,
                'billing_meter_number': mp.billing_meter_number,
                'billing_installation_number': mp.billing_installation_number,
            }
    return {
        'mp_ids': mp_ids,
        'mp_data': mp_data,
        'from_timestamp': from_timestamp,
        'to_timestamp': to_timestamp,
        'from_date': from_date,
        'to_date': to_date,
        'include_degree_days_corrected': include_degree_days_corrected,
        'include_cost': include_cost,
        'errors': errors,
    }
