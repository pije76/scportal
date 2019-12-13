# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import pytz
import json

from decimal import Decimal
from django.http import HttpResponse

from legacy.devices.models import PhysicalInput, Meter
from gridplatform.datasources.models import RawData
from django.views.decorators.csrf import csrf_exempt

DOUBLE_INPUTS = [
    "e1", "e2", "e3", "et",
]


def convert_to_base(input, value):
    if input in DOUBLE_INPUTS:
        return Decimal(value) * 1000

def save_to_db(hardware_id, value_dict, timestamp):
    meter = Meter.objects_encrypted.get(hardware_id=hardware_id)
    inputs = PhysicalInput.objects_encrypted.filter(meter_id=meter.id)
    dt = datetime.datetime.utcfromtimestamp(float(timestamp)).replace(
        tzinfo=pytz.utc)
    for physical_input in inputs:
        value = value_dict.get(physical_input.hardware_id, None)
        if value:
            RawData.objects.create(
                datasource_id=physical_input.id,
                timestamp=dt,
                value=convert_to_base(physical_input.hardware_id, value)
            )


def wibeee_receiver(request):
    hardware_id = request.GET.get("mac", None)
    timestamp = request.GET.get("time", None)
    if hardware_id and timestamp:
        save_to_db(hardware_id, request.GET, timestamp)
        return HttpResponse("OK")
    else:
        return HttpResponse("fail")


@csrf_exempt
def wibeee_receiver_json(request):
    # {"time":"1495802646","v1":"227.164","v2":"227.164","v3":"227.164","i1":"0.160","i2":"0.000","i3":"0.000","p1":"36.263","p2":"0.000","p3":"0.000","pt":"36.263","a1":"6.062","a2":"0.000","a3":"0.000","at":"6.062","r1":"0.000","r2":"0.000","r3":"0.000","rt":"0.000","f1":"-0.167","f2":"1.000","f3":"1.000","ft":"-0.167"}
    data = json.loads(request.body)
    hardware_id = data['mac']
    for measurement in data['measures']:
        save_to_db(hardware_id, measurement, measurement['time'])
    return HttpResponse("OK")
