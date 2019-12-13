# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from collections import defaultdict

from gridplatform.trackuser.tasks import task
from gridplatform.utils import condense
from gridplatform.datasequences.utils import add_ranged_sample_sequences
from gridplatform.utils.unitconversion import PhysicalQuantity

from .models import ConsumptionGroup
from .models import MainConsumption
from .models import Consumption


@task(bind=True)
def net_cost_sum_and_costcompensation_amount_task(
        task, consumptiongroup_ids, from_timestamp, to_timestamp):
    consumptiongroups = ConsumptionGroup.objects.filter(
        id__in=consumptiongroup_ids)
    count = len(consumptiongroups)

    result = {}

    task.set_progress(0, count)
    for n, consumptiongroup in enumerate(consumptiongroups):
        result[consumptiongroup.id] = {
            'net_cost_sum': consumptiongroup.net_cost_sum(
                from_timestamp, to_timestamp),
            'costcompensation_amount_sum': (
                consumptiongroup.costcompensation_amount_sum(
                    from_timestamp, to_timestamp)),
        }

        task.set_progress(n + 1, count)

    return result


@task(bind=True)
def total_cost_sum_task(
        task, mainconsumption_ids, from_timestamp, to_timestamp):
    mainconsumptions = MainConsumption.objects.filter(
        id__in=mainconsumption_ids)
    count = len(mainconsumptions)

    result = {}

    task.set_progress(0, count)
    for n, mainconsumption in enumerate(mainconsumptions):
        result[mainconsumption.id] = mainconsumption.total_cost_sum(
            from_timestamp, to_timestamp)
        task.set_progress(n + 1, count)

    return result


@task(bind=True)
def mainconsumptions_weekly_utility_task(
        task, mainconsumption_ids, from_timestamp, to_timestamp, utility_type):
    mainconsumptions = MainConsumption.objects.filter(
        id__in=mainconsumption_ids)
    total_mainconsumptions = len(mainconsumptions)

    before_from_timestamp = from_timestamp - datetime.timedelta(days=7)
    before_to_timestamp = to_timestamp - datetime.timedelta(days=7)

    measured = {'week_selected': [], 'week_before': []}
    for n, mainconsumption in enumerate(mainconsumptions):
        task.set_progress(n, total_mainconsumptions)

        measured['week_selected'].append(
            list(mainconsumption.utility_sequence(
                from_timestamp, to_timestamp, condense.DAYS)))

        measured['week_before'].append(
            list(mainconsumption.utility_sequence(
                before_from_timestamp, before_to_timestamp, condense.DAYS)))

    result = {'utility_type': utility_type}
    result['week_selected'] = list(add_ranged_sample_sequences(
        measured['week_selected'], from_timestamp,
        to_timestamp, condense.DAYS))
    result['week_before'] = list(add_ranged_sample_sequences(
        measured['week_before'], before_from_timestamp,
        before_to_timestamp, condense.DAYS))

    return result


@task(bind=True)
def consumptions_weekly_utility_task(
        task, consumption_ids, from_timestamp, to_timestamp):
    consumptions = Consumption.objects.filter(
        id__in=consumption_ids)
    total_consumptions = len(consumptions)


    measured = {'week_selected': []}
    for n, consumption in enumerate(consumptions):
        task.set_progress(n, total_consumptions)

        measured['week_selected'].append(
            list(consumption.utility_sequence(
                from_timestamp, to_timestamp, condense.HOURS)))

    result = {}
    result['consumption_id'] = consumption_ids[0]
    result['week_selected'] = list(add_ranged_sample_sequences(
        measured['week_selected'], from_timestamp,
        to_timestamp, condense.HOURS))

    return result

@task(bind=True)
def consumptions_weekly_time_task(
        task, consumption_ids, from_timestamp, to_timestamp):
    consumptions = Consumption.objects.filter(
        id__in=consumption_ids)
    total_consumptions = len(consumptions)


    measured = {'week_selected': []}
    for n, consumption in enumerate(consumptions):
        task.set_progress(n, total_consumptions)

        measured['week_selected'].append(
            list(consumption.utility_sequence(
                from_timestamp, to_timestamp, condense.DAYS)))

    result = {}
    result['consumption_id'] = consumption_ids[0]
    result['week_selected'] = list(add_ranged_sample_sequences(
        measured['week_selected'], from_timestamp,
        to_timestamp, condense.HOURS))

    return result

@task(bind=True)
def mainconsumptions_weekly_co2_emissions_task(
        task, mainconsumption_ids, from_timestamp, to_timestamp):
    mainconsumptions = MainConsumption.objects.filter(
        id__in=mainconsumption_ids)
    total_mainconsumptions = len(mainconsumptions)

    before_from_timestamp = from_timestamp - datetime.timedelta(days=7)
    before_to_timestamp = to_timestamp - datetime.timedelta(days=7)

    measured = {'week_selected': [], 'week_before': []}
    for n, mainconsumption in enumerate(mainconsumptions):
        task.set_progress(n, total_mainconsumptions)

        measured['week_selected'].append(
            list(mainconsumption.co2_emissions_sequence(
                from_timestamp, to_timestamp, condense.DAYS)))

        measured['week_before'].append(
            list(mainconsumption.co2_emissions_sequence(
                before_from_timestamp, before_to_timestamp, condense.DAYS)))

    result = {}
    result['week_selected'] = list(add_ranged_sample_sequences(
        measured['week_selected'], from_timestamp,
        to_timestamp, condense.DAYS))
    result['week_before'] = list(add_ranged_sample_sequences(
        measured['week_before'], before_from_timestamp,
        before_to_timestamp, condense.DAYS))

    return result


@task(bind=True)
def mainconsumptions_weekly_cost_sequence(
        task, mainconsumption_ids, from_timestamp, to_timestamp):
    mainconsumption = MainConsumption.objects.get(
        id__in=mainconsumption_ids)

    result = {}

    before_from_timestamp = from_timestamp - datetime.timedelta(days=7)
    before_to_timestamp = to_timestamp - datetime.timedelta(days=7)

    task.set_progress(0, 2)
    result['week_selected'] = list(mainconsumption.variable_cost_sequence(
        from_timestamp, to_timestamp, condense.DAYS))

    task.set_progress(1, 2)

    result['week_before'] = list(mainconsumption.variable_cost_sequence(
        before_from_timestamp, before_to_timestamp, condense.DAYS))
    task.set_progress(2, 2)

    return result
