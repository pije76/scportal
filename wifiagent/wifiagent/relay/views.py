import datetime

from django.shortcuts import render
from django.http import HttpResponse

from .request_handler import RequestHandler
from .models import Measurement

# Create your views here.

def receiver(request):
    mac = request.GET.get('mac', None)  #device mac
    ip = request.GET.get('ip', None)  #device local ip
    vrms1 = request.GET.get('v1', None)  #VRMS Phase 1
    vrms2 = request.GET.get('v2', None)  #VRMS Phase 2
    vrms3 = request.GET.get('v3', None)  #VRMS Phase 3
    vrms_total = request.GET.get('vT', None)  #VRMS Total
    irms1 = request.GET.get('i1', None)  #IRMS Phase 1
    irms2 = request.GET.get('i2', None)  #IRMS Phase 2
    irms3 = request.GET.get('i3', None)  #IRMS Phase 3
    irms_total = request.GET.get('iT', None)  #IRMS Total
    apparent_power1 = request.GET.get('p1', None)  #Apparent power Phase 1
    apparent_power2 = request.GET.get('p2', None) #Apparent power Phase 2
    apparent_power3 = request.GET.get('p3', None) #Apparent power Phase 3
    apparent_power_total = request.GET.get('pT', None) #pt = Apparent power Total
    active_power1 = request.GET.get('a1', None) #Active power Phase 1
    active_power2 = request.GET.get('a2', None) #Active power Phase 2
    active_power3 = request.GET.get('a3', None) #Active power Phase 3
    active_power_total = request.GET.get('at', None) #Active power Total
    reactive_power1 = request.GET.get('r1', None) #Reactive power Phase 1
    reactive_power2 = request.GET.get('r2', None) #Reactive power Phase 2
    reactive_power3 = request.GET.get('r3', None) #Reactive power Phase 3
    reactive_power_total = request.GET.get('rt', None) #Reactive power Total
    frequency1 = request.GET.get('q1', None) #Frequency Phase 1
    frequency2 = request.GET.get('q2', None) #Frequency Phase 2
    frequency3 = request.GET.get('q3', None) #Frequency Phase 3
    frequency_total = request.GET.get('qT', None) #Frequency Total
    power_factor1 = request.GET.get('f1', None) #Power factor Phase 1
    power_factor2 = request.GET.get('f2', None) #Power factor Phase 2
    power_factor3 = request.GET.get('f3', None) #Power factor Phase 3
    power_factor_total = request.GET.get('fT', None) #Power factor Total
    active_energy1 = request.GET.get('e1', None) #Active energy Phase 1
    active_energy2 = request.GET.get('e2', None) #Active energy Phase 2
    active_energy3 = request.GET.get('e3', None) #Active energy Phase 3
    active_energy_total = request.GET.get('et', None) #Active energy Total
    reactive_energy1 = request.GET.get('o1', None) #Reactive energy Phase 1
    reactive_energy2 = request.GET.get('o2', None) #Reactive energy Phase 2
    reactive_energy3 = request.GET.get('o3', None) #Reactive energy Phase 3
    reactive_energy_total = request.GET.get('ot', None) #Reactive energy Total

    request_handler = RequestHandler()

    measurement = Measurement()

    measurement.mac = mac
    measurement.ip = ip
    measurement.vrms_total = vrms_total
    measurement.timestamp = datetime.datetime.now()

    try:
        if not request_handler.send_measurement(measurement):
            measurement.save()
    except:
        measurement.save()


    return HttpResponse("OK" + mac)


