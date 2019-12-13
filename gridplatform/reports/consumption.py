# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from collections import namedtuple
import itertools
import re

from django.utils.translation import ugettext as _
from django.template.defaultfilters import floatformat

from legacy.measurementpoints.models import Collection
from gridplatform.utils.units import UNIT_CHOICES
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.preferredunits import PhysicalUnitConverter

from .csv import generate_csv
from .pdf import generate_pdf


_ConsumptionData = namedtuple('_ConsumptionData', [
    'from_timestamp', 'to_timestamp', 'group', 'portal_name',
    'measurement_type',
    'consumption', 'degreedays_corrected_consumption', 'unit',
    'cost', 'cost_unit',
    'meter_number', 'installation_number', 'mp_id',
])


def currency_display(currency_unit):
    if currency_unit is None:
        return ''
    else:
        normalized_unit = PhysicalQuantity(1, currency_unit).units
        assert re.match('currency_[a-z]{3}', normalized_unit)
        return PhysicalUnitConverter(normalized_unit)


def extend_consumption_data(collected):
    mp_ids = collected['mp_ids']
    mp_data = collected['mp_data']
    from_timestamp = collected['from_timestamp']
    to_timestamp = collected['to_timestamp']
    measurementpoints = Collection.objects.filter(
        id__in=mp_ids)
    result = {}
    for mp in measurementpoints:
        try:
            data = mp_data[mp.id]
        except KeyError:
            continue
        if mp.utility_type not in result:
            result[mp.utility_type] = {
                'data': [],
                'utility_name': mp.get_utility_type_display().capitalize(),
                'unit': unicode(dict(UNIT_CHOICES)[data['unit']]),
            }

        result[mp.utility_type]['data'].append(_ConsumptionData(
            from_timestamp,
            to_timestamp,
            mp.get_ancestors(),
            unicode(mp),
            unicode(mp.get_utility_type_display()),
            data['consumption'],
            data['degreedays_corrected_consumption'],
            unicode(dict(UNIT_CHOICES)[data['unit']]),
            data['cost'],
            currency_display(data['currency_unit']),
            data['billing_meter_number'],
            data['billing_installation_number'],
            mp.id))

    return result


def consumption_csv(from_date, to_date, collected_data,
                    include_degree_days_corrected, include_cost):
    """
    Generate CSV consumption report for a given period.

    @param measurementpoints: Measurementpoints/collections to include in
    report.

    @param from_date: Start of period to include in report.

    @param to_date: End of period to include in report.


    @return: C{HttpResponse} containing CSV data.
    """
    header = _ConsumptionData(
        _('from'), _('to'), _('group'), _('portal name'),
        _('resource type'), _('consumption'),
        _('degreedays-corrected consumption'),
        _('unit'), _('cost'),
        _('currency'), _('meter number'), _('installation number'),
        _('id'))

    def degree_days_filter(line):
        before_degree_days = [
            line.from_timestamp, line.to_timestamp, line.group,
            line.portal_name,
            line.measurement_type, line.consumption,
        ]
        if include_degree_days_corrected:
            degree_days = [line.degreedays_corrected_consumption]
        else:
            degree_days = []
        before_cost = [line.unit]
        if include_cost:
            cost = [line.cost, line.cost_unit]
        else:
            cost = []
        last = [line.meter_number, line.installation_number, line.mp_id]
        return before_degree_days + degree_days + before_cost + cost + last

    from_formatted = from_date.strftime('%Y-%m-%d')
    to_formatted = to_date.strftime('%Y-%m-%d')

    def csv_format(data):
        return data._replace(
            from_timestamp=from_formatted,
            to_timestamp=to_formatted,
            group=':'.join([unicode(g) for g in data.group]),
            consumption=floatformat(data.consumption, 2),
            degreedays_corrected_consumption=floatformat(
                data.degreedays_corrected_consumption, 2),
            cost=floatformat(data.cost, 2))
    data = collected_data
    for utility_type, values in collected_data.iteritems():
        data[utility_type]['data'] = itertools.imap(csv_format, values['data'])
        data[utility_type]['data'] = itertools.imap(degree_days_filter,
                                                    data[utility_type]['data'])
    return generate_csv(data, header=degree_days_filter(header))


def consumption_pdf(from_date, to_date, collected_data,
                    include_degree_days_corrected, include_cost, customer,
                    errors=None):
    """
    Generate PDF consumption report for a given period.

    @param measurementpoints: Measurementpoints/collections to include in
    report.

    @param from_date: Start of period to include in report.

    @param to_date: End of period to include in report.

    @return: C{HttpResponse} containing PDF data.
    """

    data = {
        'data': collected_data,
        'from_date': from_date,
        'to_date': to_date,
        'include_degree_days_corrected': include_degree_days_corrected,
        'include_cost': include_cost,
        'errors': errors,
    }

    return generate_pdf(
        'reports/consumption.tex',
        data,
        title=_('Consumption'),
        report_type='consumption',
        customer=customer)
