#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

#
# ./manage.py syncdb --noinput
# ./manage.py create_encrypted_user root feet
# ./manage.py create_encrypted_user super 123
# ./manage.py create_encrypted_user test 123
#
# python fixture_hack.py

import datetime
from decimal import Decimal
import math
import os
import pytz


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gridplatform.settings.local")

from legacy.measurementpoints.models import Collection
from gridplatform.customers.models import Customer
from legacy.measurementpoints.models import Location
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.measurementpoints.proxies import TemperatureMeasurementPoint
from gridplatform.encryption.testutils import encryption_context
from gridplatform.providers.models import Provider
from gridplatform.users.models import User
from gridplatform.utils import utilitytypes
from legacy.devices.models import Agent
from legacy.devices.models import Meter
from legacy.devices.models import PhysicalInput
from legacy.devices.models import RawData
from legacy.devices.models import SoftwareImage
from legacy.indexes.models import Index
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import CostCalculation
from legacy.measurementpoints.models import DataSeries


def create_customer():
    customer = Customer()
    customer.provider_id = 1
    customer.name_plain = 'test customer'
    customer.vat_plain = '4242'
    customer.address_plain = 'address'
    customer.postal_code_plain = '1234'
    customer.city_plain = 'city'
    customer.phone_plain = '12341234'
    customer.country_code_plain = 'dnk'
    customer.timezone = pytz.timezone('Europe/Copenhagen')
    customer.contact_name_plain = ''
    customer.contact_email_plain = ''
    customer.contact_phone_plain = ''
    customer.created_by = User.objects.get(id=1)
    customer.save()
    return customer


def setup_users(customer):
    superuser = User.objects.create_user(
        'super', '123',
        user_type=User.CUSTOMER_SUPERUSER,
        customer=customer)
    testuser = User.objects.create_user(
        'test', '123',
        user_type=User.CUSTOMER_USER,
        customer=customer)

    superuser.is_staff = False
    superuser.is_superuser = True
    superuser.save()

    testuser.is_staff = False
    testuser.is_superuser = False
    testuser.save()


def create_location(customer):
    location = Location(customer=customer, name_plain='test location')
    location.save()
    return location


def create_agent(customer, location):
    agent = Agent(
        customer=customer, location=location, mac='08:00:27:03:fe:c7',
        device_type=1, hw_major=5, hw_minor=0, hw_revision=0,
        sw_major=2, sw_minor=2, sw_revision=1, sw_subrevision='fixture',
        online=True)
    agent.save()
    return agent


def create_meter(agent, manufactoring_id, connection_type, name):
    customer = agent.customer
    location = agent.location
    meter = Meter(
        customer=customer,
        agent=agent,
        manufactoring_id=manufactoring_id,
        connection_type=connection_type,
        location=location,
        name_plain=name,
        relay_enabled=True,
        online=True)
    meter.save()
    return meter


def create_meters(agent):
    kamstrup_meter = create_meter(
        agent, 155173425101, Meter.GRIDLINK,
        'Kamstrup meter')
    mbus_meter = create_meter(
        agent, 1980720117449728, Meter.GRIDLINK,
        'Mbus meter')
    meter = create_meter(
        agent, 456789, Meter.GRIDLINK,
        'ZigBee elec. test meter')
    gas = create_meter(
        agent, 456790, Meter.GRIDLINK,
        'ZigBee gas meter')
    heat = create_meter(
        agent, 456791, Meter.GRIDLINK,
        'ZigBee heat meter')
    water = create_meter(
        agent, 456792, Meter.GRIDLINK,
        'ZigBee water meter')
    gridlink = create_meter(
        agent, 456793, Meter.GRIDLINK,
        'GridLink')
    return kamstrup_meter, mbus_meter, meter, gas, heat, water, gridlink


def create_physicalinputs(kamstrup_meter, mbus_meter, meter, gas, heat,
                          water, gridlink):
    accum = PhysicalInput(
        customer=mbus_meter.customer,
        unit='milliwatt*hour', type=1,
        meter=mbus_meter, order=0,
        name_plain='M-Bus consumption')
    accum.save()
    power = PhysicalInput(
        customer=mbus_meter.customer,
        unit='milliwatt', type=1,
        meter=mbus_meter, order=0, name_plain='M-Bus power')
    power.save()
    current = PhysicalInput(
        customer=mbus_meter.customer,
        unit='milliampere', type=1,
        meter=mbus_meter, order=0,
        name_plain='M-Bus current')
    current.save()
    voltage = PhysicalInput(
        customer=mbus_meter.customer,
        unit='millivolt', type=1,
        meter=mbus_meter, order=0,
        name_plain='M-Bus voltage')
    voltage.save()
    physicalinput = PhysicalInput(
        customer=meter.customer,
        unit='impulse',
        type=PhysicalInput.UNKNOWN_ORIGIN,
        meter=meter, order=2,
        name_plain='Pulse meter')
    physicalinput.save()

    gas = PhysicalInput(
        customer=gas.customer,
        unit='milliliter',
        type=PhysicalInput.UNKNOWN_ORIGIN, meter=gas, order=0,
        name_plain="Gas consumption")
    gas.save()

    heat = PhysicalInput(
        customer=heat.customer,
        unit='milliwatt*hour',
        type=PhysicalInput.DISTRICT_HEATING, meter=heat, order=0,
        name_plain="Heat consumption")
    heat.save()

    water = PhysicalInput(
        customer=water.customer,
        unit='milliliter',
        type=PhysicalInput.WATER, meter=water,
        order=0, name_plain="Water consumption")
    water.save()

    gl1 = PhysicalInput(
        customer=gridlink.customer,
        unit='impulse',
        type=PhysicalInput.UNKNOWN_ORIGIN, meter=gridlink,
        order=0, name_plain="GridLink input 1")
    gl2 = PhysicalInput(
        customer=gridlink.customer,
        unit='impulse',
        type=PhysicalInput.UNKNOWN_ORIGIN, meter=gridlink,
        order=1, name_plain="GridLink input 2")
    gl3 = PhysicalInput(
        customer=gridlink.customer,
        unit='impulse',
        type=PhysicalInput.UNKNOWN_ORIGIN, meter=gridlink,
        order=2, name_plain="GridLink input 3")
    gl1.save()
    gl2.save()
    gl3.save()

    powerfactor = PhysicalInput(
        customer=mbus_meter.customer,
        unit='millinone', type=1,
        meter=mbus_meter, order=0,
        name_plain='M-Bus Power Factor')
    powerfactor.save()

    return accum, power, physicalinput, heat


def create_groups(customer):
    collection = Collection(
        customer=customer,
        name_plain='Hal A',
        role=Collection.GROUP,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)
    collection.save()

    collection = Collection(
        customer=customer,
        name_plain='Hal B',
        role=Collection.GROUP,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)
    collection.save()

    collection = Collection(
        customer=customer,
        parent=collection,
        name_plain='Hal C',
        role=Collection.GROUP,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown)
    collection.save()

    collection = Collection.objects.get(id=1)

    return collection


def create_indexes():
    timezone = pytz.timezone("Europe/Copenhagen")

    elindex = Index(
        unit="currency_dkk*kilowatt^-1*hour^-1",
        role=DataRoleField.ELECTRICITY_TARIFF,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
        data_format=Index.SPOT,
        name_plain="Random el",
        timezone=timezone)
    elindex.save()

    start_time = timezone.localize(datetime.datetime.now()).replace(
        hour=0, minute=0, second=0, microsecond=0)
    current_time = start_time
    for i in range(24 * 7):
        elindex.entry_set.create(
            from_timestamp=current_time,
            to_timestamp=current_time + datetime.timedelta(hours=1),
            value=Decimal(0.3 * math.sin(i * 7.0 / 24.0) + 0.3))
        current_time += datetime.timedelta(hours=1)

    gasindex = Index(
        unit="currency_dkk*liter^-1",
        role=DataRoleField.GAS_TARIFF,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas,
        data_format=Index.SPOT,
        name_plain="Random Gas",
        timezone=timezone)
    gasindex.save()

    start_time = timezone.localize(datetime.datetime.now()).replace(
        hour=0, minute=0, second=0, microsecond=0)
    current_time = start_time
    for i in range(24 * 7):
        gasindex.entry_set.create(
            from_timestamp=current_time,
            to_timestamp=current_time + datetime.timedelta(hours=1),
            value=Decimal(0.1 * math.sin(i * 3.0 / 24.0) + 0.15))
        current_time += datetime.timedelta(hours=1)

    return elindex, gasindex


def create_swimage():
    swimage = SoftwareImage(device_type=1,
                            hw_major=5, hw_minor=0, hw_revision=0,
                            sw_major=2, sw_minor=2, sw_revision=1)
    swimage.save()
    return swimage


def main():
    root = User.objects.create_user(
        'root', 'feet',
        user_type=User.ADMIN)
    root.is_staff = True
    root.is_superuser = True
    root.save()

    Provider.objects.create(name_plain='GridManager Energy Service')

    customer = create_customer()
    setup_users(customer)
    from gridplatform.trackuser import _set_customer
    _set_customer(customer)
    location = create_location(customer)
    agent = create_agent(customer, location)
    kamstrup_meter, mbus_meter, meter, gas, heat, water, gridlink = \
        create_meters(agent)
    accum, power, physicalinput, heat_accum = create_physicalinputs(
        kamstrup_meter, mbus_meter, meter, gas, heat, water, gridlink)

    ph_production = meter.physicalinput_set.create(
        customer=meter.customer,
        unit='milliwatt*hour',
        type=PhysicalInput.ELECTRICITY,
        order=10,
        name_plain='Production data')
    from productiondata import MEASUREMENTS
    RawData.objects.bulk_create(
        [
            RawData(
                datasource=ph_production,
                value=value,
                timestamp=timestamp)
            for timestamp, value in MEASUREMENTS])

    collection = create_groups(customer)

    mpa = ConsumptionMeasurementPoint(
        customer=customer, parent=collection,
        name_plain='Lighting',
        role=Collection.CONSUMPTION_MEASUREMENT_POINT,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

    from gridplatform.consumptions.models import NonpulsePeriod
    from legacy.datasequence_adapters.models import ConsumptionAccumulationAdapter  # noqa
    period = NonpulsePeriod.objects.get(datasource=accum)
    ds = ConsumptionAccumulationAdapter.objects.get(
        datasequence__period=period)
    mpa.consumption_input = ds
    mpa.consumption.customer = customer
    mpa.save()
    mpa.enable_rate = True

    meter = Meter.objects.get(manufactoring_id=456789)
    mpa.relay = meter
    mpa.save()

    mpb = ConsumptionMeasurementPoint(
        customer=customer, parent=collection, name_plain='Production',
        role=Collection.CONSUMPTION_MEASUREMENT_POINT,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

    mpb.consumption_input = ds
    mpb.consumption.customer = customer
    mpb.save()

    mpc = ConsumptionMeasurementPoint(
        customer=customer, parent=collection,
        name_plain='Heating (total)',
        role=Collection.CONSUMPTION_MEASUREMENT_POINT,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating)
    period = NonpulsePeriod.objects.get(datasource=heat_accum)
    ds = ConsumptionAccumulationAdapter.objects.get(
        datasequence__period=period)
    mpc.consumption_input = ds
    mpc.consumption.customer = customer
    mpc.save()
    mpc.enable_rate = True

    create_indexes()

    tariff = DataSeries.objects.filter(
        role=DataRoleField.ELECTRICITY_TARIFF)[0]

    cost_graph = mpa.graph_set.create(
        role=DataRoleField.COST)

    CostCalculation.objects.create(
        graph=cost_graph,
        role=DataRoleField.COST,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
        unit="millicurrency_dkk",
        customer=customer,
        tariff=tariff,
        consumption=mpa.consumption)

    create_swimage()

    temperature = PhysicalInput(
        customer=meter.customer,
        unit='millikelvin',
        type=PhysicalInput.TEMPERATURE,
        meter=meter,
        order=3,
        name_plain='Temperature input')
    temperature.save()

    temperature_measurement_point = TemperatureMeasurementPoint(
        name_plain='Outdoor temperature',
        customer=customer,
        parent=collection)

    assert customer

    from gridplatform.datasequences.models import NonaccumulationPeriod
    from legacy.datasequence_adapters.models import NonaccumulationAdapter  # noqa
    period = NonaccumulationPeriod.objects.get(datasource=temperature)
    ds = NonaccumulationAdapter.objects.get(
        datasequence__period_set=period)

    temperature_measurement_point.input_configuration = ds
    temperature_measurement_point.save()

    # The automatically created input periods will be have their from_timestamp
    # initialized to creation time, which is naturally in real life, bug
    # useless in this fixture setup:
    import gridplatform.consumptions.models
    gridplatform.consumptions.models.Period.objects.all().update(
        from_timestamp=datetime.datetime(2000, 1, 1, tzinfo=pytz.utc))
    NonaccumulationPeriod.objects.all().update(
        from_timestamp=datetime.datetime(2000, 1, 1, tzinfo=pytz.utc))

    from django.contrib.auth.models import Group, Permission
    all_permission_group = Group.objects.create(name='All permissions')
    all_permissions = Permission.objects.all()
    all_permission_group.permissions.add(*all_permissions)

    from gridplatform.customer_datasources.models import CustomerDataSource
    from gridplatform.utils.units import ENERGY_PER_VOLUME_BASE_UNITS
    conversion_rate = CustomerDataSource(
        name_plain='conversion rate',
        customer=customer,
        unit=ENERGY_PER_VOLUME_BASE_UNITS[0])
    conversion_rate.save()


if __name__ == "__main__":
    with encryption_context():
        main()
