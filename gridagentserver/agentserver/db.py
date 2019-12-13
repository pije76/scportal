"""
Database interface exposing (limited) functionality as functions.
"""
# TODO: calculation points and rules are not yet defined in GridPlatform
import logging
import numbers

from legacy.devices.models import Agent, Meter, PhysicalInput, AgentEvent

logger = logging.getLogger(__name__)


BUCKINGHAM_MAP = {
    0: 'none',  # unknown unit
    1: "milliwatt*hour",
    2: "milliwatt",
    3: "impulse",
    4: "milliliter",
    5: "milliliter*hour^-1",
    6: "millikelvin",
    7: "millivolt",
    8: "milliampere",
    9: "millihertz",
    10: "gram",
    11: "millibar",
    12: "second",
    13: "none",  # "binary states"
    14: "millinone",  # "milli" power factor
}


# for models with encrypted fields, we store the empty string for those fields
# (representing the encrypted form of the empty string) but we still need
# "something" for an initialisation vector to avoid special cases in decryption
fake_iv = bytearray('\x00' * 16)

# TODO: We need a cache clean-up method once we introduce GAS load
# balancing
value_cache = {}


def agent_exists(agent_mac):
    return Agent.objects.filter(mac=agent_mac).exists()


def get_agent(agent_mac):
    if isinstance(agent_mac, Agent):
        return agent_mac
    elif isinstance(agent_mac, numbers.Number):
        return Agent.objects.get(mac=agent_mac)
    else:
        raise Exception('Invalid data type for agent MAC: {}'.format(
            agent_mac))


def set_agent_info(agent_mac, serial, device_type, hw_version, sw_version):
    agent = get_agent(agent_mac)
    agent._set_info(serial, device_type, hw_version, sw_version)


def get_meter(meter_id, agent_mac):
    agent = get_agent(agent_mac)
    connection_type, manufactoring_id = meter_id
    obj, created = Meter.objects.get_or_create(
        connection_type=connection_type,
        manufactoring_id=manufactoring_id,
        agent=agent,
        customer_id=agent.customer_id,
        defaults={
            'encryption_data_initialization_vector': fake_iv,
            'location_id': agent.location_id,
        })
    return obj


def get_physicalinput(datatype, agent_unit, input_number, meter):
    if agent_unit in BUCKINGHAM_MAP:
        obj, created = PhysicalInput.objects.get_or_create(
            customer_id=meter.customer_id,
            type=datatype, unit=BUCKINGHAM_MAP[agent_unit],
            order=input_number, meter=meter,
            defaults={
                'encryption_data_initialization_vector': fake_iv,
                'store_measurements': True,
                'hardware_id':
                'GA-{agent_id:012x}-{meter_id:016x}-{input_id}'.format(
                    agent_id=int(meter.agent.mac),
                    meter_id=meter.manufactoring_id,
                    input_id=input_number,
                )
            })
        return obj
    else:
        logger.warning(
            'Unsupported unit %s from meter %d input %d.' % (
                agent_unit, meter, input_number))
        return None


def set_meter_state(control_manual, relay_on, online, timestamp,
                    meter_id, agent_mac):
    meter = get_meter(meter_id, agent_mac)
    meter._set_state(control_manual, relay_on, online, timestamp)


def set_agent_online(online, timestamp, agent_mac):
    agent = get_agent(agent_mac)
    agent._set_online(online, timestamp)


def set_agent_add_mode(add_mode, timestamp, agent_mac):
    agent = get_agent(agent_mac)
    agent._set_add_mode(add_mode, timestamp)


def store_event(mac, timestamp, code, text):
    agent = Agent.objects.get(mac=mac)
    AgentEvent.objects.create(
        agent=agent, timestamp=timestamp, code=code, message=text)


def set_meters_online(mac, meter_list, version_list, device_opts_list):
    agent = get_agent(mac)
    if version_list and device_opts_list:
        for meter_id, versions, device_opts in \
                zip(meter_list, version_list, device_opts_list):
            connection_type, manufactoring_id = meter_id
            try:
                meter = Meter.objects.get(
                    connection_type=connection_type,
                    manufactoring_id=manufactoring_id,
                    agent=agent,
                    customer_id=agent.customer_id)
            except Meter.DoesNotExist:
                # Quick fix for bug in GridAgent SW version 2.3.0.
                # It sometimes sends junk in the meters connected set.
                continue
            meter.online = True
            meter.device_type = device_opts[0]
            meter.hw_major = versions[0].major
            meter.hw_minor = versions[0].minor
            meter.hw_revision = versions[0].revision
            meter.hw_subrevision = \
                versions[0].revisionstring.decode('iso8859-1')
            meter.sw_major = versions[1].major
            meter.sw_minor = versions[1].minor
            meter.sw_revision = versions[1].revision
            meter.sw_subrevision = \
                versions[1].revisionstring.decode('iso8859-1')
            meter.save(update_fields=[
                'online',
                'device_type',
                'hw_major', 'hw_minor', 'hw_revision', 'hw_subrevision',
                'sw_major', 'sw_minor', 'sw_revision', 'sw_subrevision',
            ])
    else:
        # missing version_list or device_opts_list --- data from old agent
        # sw version which does not provide this...
        for meter_id in meter_list:
            connection_type, manufactoring_id = meter_id
            try:
                meter = Meter.objects.get(
                    connection_type=connection_type,
                    manufactoring_id=manufactoring_id,
                    agent=agent,
                    customer_id=agent.customer_id)
            except Meter.DoesNotExist:
                # Quick fix for bug in GridAgent SW version 2.3.0.
                # It sometimes sends junk in the meters connected set.
                continue
            meter.online = True
            meter.save(update_fields=['online'])
