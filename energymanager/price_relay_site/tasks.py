# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.tariffs.models import EnergyTariff
from gridplatform.trackuser.tasks import task


@task(bind=True)
def price_relay_tariff_hourly_task(
        task, tariff_id, project_id, from_timestamp, to_timestamp):
    tariff = EnergyTariff.objects.get(pk=tariff_id)

    task.set_progress(0, 1)

    data = list(tariff.period_set.value_sequence(from_timestamp, to_timestamp))

    result = {}
    result['tariff_id'] = tariff_id
    result['project_id'] = project_id
    result['data'] = list(tariff.period_set.value_sequence(from_timestamp, to_timestamp))
    task.set_progress(1, 1)

    return result
