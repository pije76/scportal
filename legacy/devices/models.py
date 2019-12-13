# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import datetime

from django.db import models
from django.db.models import Max
from django.db.models import Min
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.translation import ugettext
from django.utils.translation import ugettext_lazy as _

import pytz
from model_utils import Choices

from gridplatform.customer_datasources.models import CustomerDataSource
from gridplatform.datasources.models import RawData
from gridplatform.customers.models import Customer
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.trackuser.managers import CustomerBoundManager
from gridplatform.utils import utilitytypes
from gridplatform.utils.fields import MacAddressField
from gridplatform.utils.format_id import format_mac, format_mbus_enhanced
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.units import UNIT_CHOICES
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import Location


logger = logging.getLogger(__name__)


UNKNOWN = 0
GRIDAGENT = 1
GRIDPOINT1PH = 2
GRIDPOINT3PH = 3
GRIDLINK = 4
GRIDPOINT_S01 = 5
KAMSTRUP_382 = 6
KAMSTRUP_602 = 7
DEIF_4002 = 8
SCHNEIDER_PM9C = 9
MITSUBISHI_FX1S = 10
TEMPERATURE_SENSOR = 11
MODBUS = 12
MBUS = 13
GRIDREPEATER = 14


DEVICE_TYPE_CHOICES = (
    (UNKNOWN, _('Unknown')),
    (GRIDAGENT, _('GridAgent')),
    (GRIDPOINT1PH, _('1 phase GridPoint')),
    (GRIDPOINT3PH, _('3 phase GridPoint')),
    (GRIDLINK, _('GridLink')),
    (GRIDPOINT_S01, _('GridPoint S01 Legacy')),
    (KAMSTRUP_382, _('Kamstrup 382')),
    (KAMSTRUP_602, _('Kamstrup 602')),
    (DEIF_4002, _('DEIF 4002')),
    (SCHNEIDER_PM9C, _('Schneider PM9C')),
    (MITSUBISHI_FX1S, _('Mitsubishi FX1S')),
    (TEMPERATURE_SENSOR, _('Temperature Sensor')),
    (MODBUS, _('Modbus')),
    (MBUS, _('MBus')),
    (GRIDREPEATER, _('GridRepeater')),
)


class VersionsMixin(models.Model):
    """
    Common software/hardware version information for GridManager meters and
    agents.
    """
    device_type = models.IntegerField(
        _('Device type'), choices=DEVICE_TYPE_CHOICES,
        default=UNKNOWN, editable=False)
    device_serial = models.IntegerField(
        _('Device serial number'), null=True, editable=False)
    hw_major = models.PositiveIntegerField(
        _('Hardware major version'), null=True, editable=False)
    hw_minor = models.PositiveIntegerField(
        _('Hardware minor version'), null=True, editable=False)
    hw_revision = models.PositiveIntegerField(
        _('Hardware revision'), null=True, editable=False)
    hw_subrevision = models.CharField(
        _('Hardware extra revision string'), max_length=12, editable=False)
    sw_major = models.PositiveIntegerField(
        _('Software major version'), null=True, editable=False)
    sw_minor = models.PositiveIntegerField(
        _('Software minor version'), null=True, editable=False)
    sw_revision = models.PositiveIntegerField(
        _('Software revision'), null=True, editable=False)
    sw_subrevision = models.CharField(
        _('Software extra revision string'), max_length=12, editable=False)

    class Meta:
        abstract = True

    def compatible_software(self):
        """
        Finds SoftwareImage instances for the hardware model/version.  If
        hardware model/version information is missing, returns an empty
        queryset.
        """
        hw_version = (self.hw_major, self.hw_minor, self.hw_revision)
        if self.device_type == UNKNOWN or any([v is None for v in hw_version]):
            return SoftwareImage.objects.none()
        else:
            return SoftwareImage.objects.filter(
                device_type=self.device_type, hw_major=self.hw_major,
                hw_minor=self.hw_minor, hw_revision=self.hw_revision,
                hw_subrevision=self.hw_subrevision)

    def get_hw_version_display(self):
        hw_version = (self.hw_major, self.hw_minor, self.hw_revision)
        if any([v is None for v in hw_version]):
            return None
        else:
            version = u'{:02d}.{:02d}.{:02d}'.format(*hw_version)
            if self.hw_subrevision:
                version += u'({})'.format(self.hw_subrevision)
        return version

    def get_sw_version_display(self):
        sw_version = (self.sw_major, self.sw_minor, self.sw_revision)
        if any([v is None for v in sw_version]):
            return None
        else:
            version = u'{:02d}.{:02d}.{:02d}'.format(*sw_version)
            if self.sw_subrevision:
                version += u'-{}'.format(self.sw_subrevision)
        return version


class Agent(VersionsMixin):
    """
    Represents a GridManager GridAgent.  Not directly interesting for
    customers/users, but important to the system as all communication with
    meters is via agents.
    """
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    location = models.ForeignKey(Location, on_delete=models.PROTECT,
                                 blank=True, null=True)
    mac = MacAddressField(_('MAC address'), unique=True)
    online = models.BooleanField(
        _('online'), default=False, editable=False)
    online_since = models.DateTimeField(
        _('online since'), null=True, editable=False)
    add_mode = models.BooleanField(
        _('in add mode'), default=False, editable=False)

    no_longer_in_use = models.BooleanField(
        _('no longer in use'), default=False)

    objects = CustomerBoundManager()

    class Meta:
        verbose_name = _('agent')
        verbose_name_plural = _('agents')
        ordering = ['location', 'mac']

    def __unicode__(self):
        return unicode(self.mac)

    def _set_online(self, online, timestamp):
        # helper for GAS
        change = self.online != online
        if change:
            self.online = bool(online)
            if online:
                self.online_since = timestamp
            else:
                self.online_since = None
            self.save(update_fields=['online', 'online_since'])

    def _set_add_mode(self, add_mode, timestamp):
        # helper for GAS
        change = self.add_mode != add_mode
        if change:
            self.add_mode = add_mode
            self.save(update_fields=['add_mode'])

    def _set_info(self, serial, device_type, hw_version, sw_version):
        # helper for GAS
        self.device_type = device_type
        self.hw_major, self.hw_minor, self.hw_revision, self.hw_subrevision = \
            hw_version
        self.sw_major, self.sw_minor, self.sw_revision, self.sw_subrevision = \
            sw_version
        self.device_serial = serial
        self.save(update_fields=[
            'device_type',
            'hw_major', 'hw_minor', 'hw_revision', 'hw_subrevision',
            'sw_major', 'sw_minor', 'sw_revision', 'sw_subrevision',
            'device_serial'])

    def satisfies_search(self, search):
        elems = [
            self.location,
            self.mac,
            self.connection_state,
        ]
        if self.customer:
            elems.append(self.customer)
        search = search.lower()
        return any([search in unicode(elem).lower() for elem in elems])

    @property
    def connection_state(self):
        if self.online:
            return _('Online')
        else:
            return _('Offline')


class AgentStateChange(models.Model):
    """
    Changelog/history for Agent.
    """
    agent = models.ForeignKey(Agent, editable=False, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(_('timestamp'), editable=False)
    online = models.BooleanField(
        _('online'), editable=False, default=False)
    add_mode = models.BooleanField(
        _('in add mode'), editable=False, default=False)


class AgentEvent(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    code = models.SmallIntegerField()
    message = models.CharField(max_length=128)

    class Meta:
        ordering = ['timestamp']


class Meter(EncryptedModel, VersionsMixin):
    """
    Represents a meter, GridMeter or otherwise.  Meters are automatically
    created in the system by the GridAgentServer when reported by GridAgents.
    Only location ande name are editable by users --- all other properties are
    automatically set based on reported information from agents.
    """
    UNKNOWN = 0
    GRIDPOINT = 1
    GRIDPOINT_S01 = 2
    GRIDLINK = 3
    MITSUBISHI_FX1S = 4
    RESERVED = 5
    MBUS = 6
    MODBUS = 7
    MODBUS_ZWAVE = 8
    TEMPERATURE_SENSOR = 9
    GRIDREPEATER = 10
    GRIDPOINT_LVL2 = 11
    WIBEEE = 12

    CONNECTION_TYPE_CHOICES = (
        (UNKNOWN, _('Unknown')),
        (GRIDPOINT, _('GridPoint')),
        (GRIDPOINT_S01, _('GridPoint S01 Legacy')),
        (GRIDLINK, _('GridLink')),
        (MITSUBISHI_FX1S, _('Mitsubishi FX1S')),
        (RESERVED, _('Reserved')),
        (MBUS, _('MBus')),
        (MODBUS, _('Modbus')),
        (MODBUS_ZWAVE, _('Modbus via Z-wave')),
        (TEMPERATURE_SENSOR, _('Temperature sensor')),
        (GRIDREPEATER, _('GridRepeater')),
        (GRIDPOINT_LVL2, _('GridPoint Level 2')),
        (WIBEEE, _('Wibeee')),
    )
    MEASUREMENTS_INFO = Choices(
        (0, 'all_is_well', ''),
        (1, 'no_measurements_ever', _('No measurements ever.')),
        (2, 'no_measurements_within_24_hours',
         _('No measurements within the last 24 hours or more.')),
        (3, 'no_change', _('Measurements for last 24 hours are all equal.')),
    )
    CONNECTION_STATES = Choices(
        (0, 'agent_offline', _('Agent offline.')),
        (1, 'agent_online', _('Agent online.')),
    )
    ERROR_STATES = Choices(
        (0, 'no_error', ''),
        (1, 'warning', ''),
        (2, 'error', ''),
    )
    agent = models.ForeignKey(Agent, editable=False, on_delete=models.PROTECT)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT,
                                 editable=False)
    manufactoring_id = models.BigIntegerField(editable=False)
    connection_type = models.IntegerField(
        _('connection type'),
        choices=CONNECTION_TYPE_CHOICES,
        editable=False)
    manual_mode = models.BooleanField(
        _('in manual mode'), editable=False, default=False)
    relay_on = models.BooleanField(
        _('relay on'), editable=False, default=False)
    online = models.BooleanField(
        _('online'), editable=False, default=False)
    online_since = models.DateTimeField(
        _('online since'), null=True, editable=False)
    joined = models.BooleanField(_('joined'), editable=False, default=True)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, blank=True, null=True)
    relay_enabled = models.BooleanField(default=False)
    name = EncryptedCharField(_('name'), max_length=50, blank=True)
    hardware_id = models.CharField(
        _('hardware id'), max_length=120, blank=True)

    objects = CustomerBoundManager()

    objects_encrypted = models.Manager()

    class Meta:
        verbose_name = _('meter')
        verbose_name_plural = _('meters')
        ordering = ['connection_type', 'manufactoring_id', 'id']

    def __unicode__(self):
        name = unicode(self.name_plain or self.name)
        if name == '' or name is None:
            name = unicode(self.get_manufactoring_id_display())
        return name

    def _set_state(self, control_manual, relay_on, online, timestamp):
        # helper for GAS
        change = (self.manual_mode != control_manual or
                  self.relay_on != relay_on or
                  self.online != online)
        if change:
            if online != self.online:
                if online:
                    self.online_since = timestamp
                else:
                    self.online_since = None
            self.control_manual = control_manual
            self.relay_on = relay_on
            self.online = online
            self.save(update_fields=[
                'manual_mode', 'relay_on', 'online', 'online_since'])

    def satisfies_search(self, search):
        elems = [
            self,
            self.get_connection_type_display(),
            self.get_manufactoring_id_display(),
            self.agent,
            self.location,
            self.get_control_mode_display(),
            self.get_relay_state_display(),
            self.connection_state,
        ]
        search = search.lower()
        return any([search in unicode(elem).lower() for elem in elems])

    def get_encryption_id(self):
        return (Customer, self.customer_id)

    def get_manufactoring_id_display(self):
        # Everything is formatted like 8-byte MAC adresses --- because in
        # reality, everything is in various custom formats defined by the
        # GridAgent...
        return format_mac(self.manufactoring_id, 8)
        if self.connection_type == self.ZIGBEE or \
                self.connection_type == self.MBUS:
            return format_mac(self.manufactoring_id, 8)
        elif self.connection_type == self.KAMSTRUP_UTILIDRIVER:
            return format_mac(self.manufactoring_id, 6)
        elif self.connection_type == self.MBUS_ENHANCED:
            return format_mbus_enhanced(self.manufactoring_id)
        else:
            return str(self.manufactoring_id)

    def get_control_mode_display(self):
        if self.manual_mode:
            return _('Manual')
        else:
            return _('Automatic')

    def get_relay_state_display(self):
        if self.relay_on:
            return _('On')
        else:
            return _('Off')

    @cached_property
    def latest_update(self):
        """
        Returns the latest measurement update timestamp.
        """
        input_ids = list(
            self.physicalinput_set.values_list('id', flat=True))
        result = None
        for input_id in input_ids:
            try:
                input_updated = RawData.objects.filter(
                    datasource_id=input_id
                ).latest('timestamp').timestamp
                if not result or\
                        result < input_updated:
                    result = input_updated
            except RawData.DoesNotExist:
                pass

        return result

    @cached_property
    def _measurement_change_within_24_hours(self):
        """
        This method returns True if change has been measured
        within last 24 hours, False otherwise.
        """
        now = datetime.datetime.now(pytz.utc)
        input_ids = list(
            self.physicalinput_set.values_list('id', flat=True))
        for input_id in input_ids:
            aggregates = RawData.objects.filter(
                datasource_id=input_id,
                timestamp__gt=now - datetime.timedelta(hours=24)).\
                aggregate(
                    min_value=Min('value'),
                    max_value=Max('value'))
            if aggregates['min_value'] != aggregates['max_value']:
                return True
        return False

    @cached_property
    def _connection_state(self):
        if not self.agent.online:
            return Meter.CONNECTION_STATES.agent_offline
        else:
            return Meter.CONNECTION_STATES.agent_online

    @cached_property
    def _measurements_info(self):
        now = datetime.datetime.now(pytz.utc)
        if self.latest_update is None:
            return Meter.MEASUREMENTS_INFO.no_measurements_ever
        elif self.latest_update <= now - datetime.timedelta(days=1):
            return Meter.MEASUREMENTS_INFO.no_measurements_within_24_hours
        elif not self._measurement_change_within_24_hours:
            return Meter.MEASUREMENTS_INFO.no_change
        else:
            return Meter.MEASUREMENTS_INFO.all_is_well

    @cached_property
    def _error_state(self):
        if self._measurements_info in [
            Meter.MEASUREMENTS_INFO.no_measurements_ever,
            Meter.MEASUREMENTS_INFO.no_measurements_within_24_hours,
        ]:
            return Meter.ERROR_STATES.error
        elif self._measurements_info == Meter.MEASUREMENTS_INFO.no_change:
            return Meter.ERROR_STATES.warning
        elif self._connection_state in [
            Meter.CONNECTION_STATES.agent_offline,
        ]:
            return Meter.ERROR_STATES.warning
        else:
            return Meter.ERROR_STATES.no_error

    @cached_property
    def connection_state(self):
        if self._error_state == Meter.ERROR_STATES.error:
            return _('Error: %s %s') % (
                Meter.CONNECTION_STATES[self._connection_state],
                Meter.MEASUREMENTS_INFO[self._measurements_info])
        elif self._error_state == Meter.ERROR_STATES.warning:
            return _('Warning: %s %s') % (
                Meter.CONNECTION_STATES[self._connection_state],
                Meter.MEASUREMENTS_INFO[self._measurements_info])
        else:
            return Meter.CONNECTION_STATES[self._connection_state]

    def get_pulse_inputs(self):
        return self.physicalinput_set.filter(unit='impulse')

    def get_non_pulse_inputs(self):
        return self.physicalinput_set.exclude(unit='impulse')


class MeterStateChange(models.Model):
    """
    Changelog/history for Meter.
    """
    meter = models.ForeignKey(Meter, editable=False, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(_('timestamp'), editable=False)
    manual_mode = models.BooleanField(
        _('in manual mode'), editable=False, default=False)
    relay_on = models.BooleanField(
        _('relay'), editable=False, default=False)
    online = models.BooleanField(
        _('online'), editable=False, default=False)


class MeterCustomerBoundManager(CustomerBoundManager):
    _field = 'meter__customer'


class PhysicalInput(CustomerDataSource):
    """
    Represent an "input" on a meter.  A physical meter may report several
    different values; e.g. current power and accumulated consumption or volume
    flow and temperature --- these must be separately selectable for use in
    monitored equipment.

    @ivar order: An integer that along with type helps make a physical
    input unique for any L{Meter}.  For instance, on a three-phased
    Meter, each phase have similar physical input, and it makes sense
    to track which is which.

    @note: UNKNOWN_UNIT and UNKNOWN_TYPE are used when the GridAgent reports
    that it does not know the unit or type.  This is conceptually different
    from what would be expressed by NULL/None --- "UNKNOWN" is here treated as
    a normal/actual value on the server side.
    """
    UNKNOWN_ORIGIN = 0
    ELECTRICITY = 1
    DISTRICT_HEATING = 2
    TEMPERATURE = 3
    INPUT_STATES = 4
    OUTPUT_STATES = 5
    GAS = 6
    WATER = 7

    TYPE_CHOICES = (
        (UNKNOWN_ORIGIN, _('unknown type')),
        (ELECTRICITY, _('electricity')),
        (WATER, _('water')),
        (GAS, _('gas')),
        (DISTRICT_HEATING, _('heat')),
        (TEMPERATURE, _('temperature')),
        (INPUT_STATES, _('input states')),
        (OUTPUT_STATES, _('output states')),
    )
    type = models.IntegerField(choices=TYPE_CHOICES, editable=False)
    meter = models.ForeignKey(Meter, editable=False, on_delete=models.PROTECT)
    order = models.IntegerField(editable=False)
    store_measurements = models.BooleanField(default=True)

    objects = MeterCustomerBoundManager()
    objects_encrypted = models.Manager()

    class Meta:
        # unique_together = (("type", "unit", "meter", "order"))
        ordering = ['order', 'type']
        verbose_name = _('physical input')
        verbose_name_plural = _('physical inputs')

    def __unicode__(self):
        order_to_input_map = {
            0: ugettext('Consumption all phases'),
            1: ugettext('Consumption phase 1'),
            2: ugettext('Consumption phase 2'),
            3: ugettext('Consumption phase 3'),
            4: ugettext('Power phase 1'),
            5: ugettext('Power phase 2'),
            6: ugettext('Power phase 3'),
            7: ugettext('Voltage phase 1'),
            8: ugettext('Voltage phase 2'),
            9: ugettext('Voltage phase 3'),
            10: ugettext('Current phase 1'),
            11: ugettext('Current phase 2'),
            12: ugettext('Current phase 3'),
        }
        if self.name_plain:
            return _(u'%(meter_name)s: %(input_name)s') % {
                'meter_name': self.meter,
                'input_name': self.name_plain,
            }
        elif self.meter.connection_type == Meter.GRIDPOINT_LVL2 and \
                self.order in order_to_input_map:
            return '{}: {}'.format(self.meter, order_to_input_map[self.order])

        else:
            return _(u'%(meter_name)s: (%(unit)s #%(order)s)') % {
                'meter_name': self.meter,
                'unit': self.get_unit_display(),
                'order': self.order,
            }

    def save(self, *args, **kwargs):
        self.check_invariant()
        super(PhysicalInput, self).save(*args, **kwargs)

    def get_encryption_id(self):
        return (Customer, self.meter.customer_id)

    ACCUMULATION_UNITS = ('milliwatt*hour', 'impulse', 'milliliter',
                          'gram', 'second')

    NONACCUMULATION_UNITS = ('milliwatt', 'millikelvin', 'millivolt',
                             'milliampere', 'millihertz', 'milliliter*hour^-1',
                             'millibar', 'millinone')

    UNKNOWN_UNITS = ('none', )

    def is_accumulation(self):
        return any(
            PhysicalQuantity.compatible_units(self.unit, unit)
            for unit in self.ACCUMULATION_UNITS)

    @property
    def is_pulse(self):
        return PhysicalQuantity.compatible_units(self.unit, 'impulse')

    def get_unit_display(self):
        return dict(UNIT_CHOICES).get(self.unit, self.unit)

    def check_invariant(self):
        assert self.unit in self.ACCUMULATION_UNITS or \
            self.unit in self.NONACCUMULATION_UNITS or \
            self.unit in self.UNKNOWN_UNITS, \
            '%s not in %s + %s + %s' % (
                self.unit, self.ACCUMULATION_UNITS,
                self.NONACCUMULATION_UNITS, self.UNKNOWN_UNITS)

    def get_utility_type(self):
        if self.type == self.ELECTRICITY:
            return utilitytypes.METER_CHOICES.electricity
        elif self.type == self.DISTRICT_HEATING:
            return utilitytypes.METER_CHOICES.district_heating
        elif self.type == self.GAS:
            return utilitytypes.METER_CHOICES.gas
        elif self.type == self.WATER:
            return utilitytypes.METER_CHOICES.water
        return None


# Same fields as in the VersionsMixin abstract model --- but all fields are
# required here; not editable and may be null there...
class SoftwareImage(models.Model):
    """
    An indication that a specific software release exists.
    """
    device_type = models.IntegerField(
        _('Device type'), choices=DEVICE_TYPE_CHOICES)
    hw_major = models.PositiveIntegerField(_('Hardware major version'))
    hw_minor = models.PositiveIntegerField(_('Hardware minor version'))
    hw_revision = models.PositiveIntegerField(_('Hardware revision'))
    hw_subrevision = models.CharField(
        _('Hardware extra revision string'), max_length=12)
    sw_major = models.PositiveIntegerField(_('Software major version'))
    sw_minor = models.PositiveIntegerField(_('Software minor version'))
    sw_revision = models.PositiveIntegerField(_('Software revision'))
    sw_subrevision = models.CharField(
        _('Software extra revision string'), max_length=12)

    class Meta:
        verbose_name = _('software image')
        verbose_name_plural = _('software images')
        ordering = ['device_type',
                    'hw_major', 'hw_minor', 'hw_revision', 'hw_subrevision',
                    'sw_major', 'sw_minor', 'sw_revision', 'sw_subrevision']

    def get_hw_version_display(self):
        version = u'{:02d}.{:02d}.{:02d}'.format(
            self.hw_major, self.hw_minor, self.hw_revision)
        if self.hw_subrevision:
            version += u'({})'.format(self.hw_subrevision)
        return version

    def get_sw_version_display(self):
        version = u'{:02d}.{:02d}.{:02d}'.format(
            self.sw_major, self.sw_minor, self.sw_revision)
        if self.sw_subrevision:
            version += u'({})'.format(self.sw_subrevision)
        return version


# NOTE: copy from datasequences/models/__init__.py --- but makes more sense
# here...
TYPE_UNIT_PAIR_TO_ROLE_MAP = {
    (PhysicalInput.ELECTRICITY, 'milliwatt*hour'): DataRoleField.CONSUMPTION,
    (PhysicalInput.ELECTRICITY, 'milliwatt'): DataRoleField.POWER,
    (PhysicalInput.ELECTRICITY, 'millivolt'): DataRoleField.VOLTAGE,
    (PhysicalInput.ELECTRICITY, 'milliampere'): DataRoleField.CURRENT,
    (PhysicalInput.ELECTRICITY, 'millinone'): DataRoleField.POWER_FACTOR,

    (PhysicalInput.DISTRICT_HEATING, 'milliwatt*hour'): (
        DataRoleField.CONSUMPTION),
    (PhysicalInput.DISTRICT_HEATING, 'milliwatt'): DataRoleField.POWER,
    (PhysicalInput.DISTRICT_HEATING, 'milliliter'): DataRoleField.VOLUME,
    (PhysicalInput.DISTRICT_HEATING, 'milliliter*hour^-1'): (
        DataRoleField.VOLUME_FLOW),

    (PhysicalInput.GAS, 'milliliter'): DataRoleField.CONSUMPTION,
    (PhysicalInput.GAS, 'milliliter*hour^-1'): DataRoleField.VOLUME_FLOW,

    (PhysicalInput.WATER, 'milliliter'): DataRoleField.CONSUMPTION,
    (PhysicalInput.WATER, 'milliliter*hour^-1'): DataRoleField.VOLUME_FLOW,

    (PhysicalInput.TEMPERATURE, 'millikelvin'): (
        DataRoleField.ABSOLUTE_TEMPERATURE),

    # UGLY-HACK: While we wait for agent to support unspecified register values
    # for modbus, we cheat and use millibar for efficiency.
    (PhysicalInput.ELECTRICITY, 'millibar'): DataRoleField.EFFICIENCY,
}


@receiver(post_save, sender=PhysicalInput)
def autocreate_datasequence(sender, instance, created, raw=False, **kwargs):
    from gridplatform.consumptions.models import Consumption
    from gridplatform.consumptions.models import NonpulsePeriod
    from gridplatform.datasequences.models import NonaccumulationDataSequence
    from gridplatform.datasequences.models import NonaccumulationPeriod
    from legacy.datasequence_adapters.models import NonaccumulationAdapter
    from legacy.datasequence_adapters.models import ConsumptionAccumulationAdapter  # noqa

    type_unit_pair = (instance.type, instance.unit)

    if created and not raw and type_unit_pair in TYPE_UNIT_PAIR_TO_ROLE_MAP:
        customer = instance.meter.customer
        if not customer:
            return

        role = TYPE_UNIT_PAIR_TO_ROLE_MAP[type_unit_pair]
        utility_type = instance.get_utility_type()
        from_timestamp = datetime.datetime.now(pytz.utc).replace(
            minute=0, second=0, microsecond=0)

        fake_iv = bytearray(b'\x00' * 16)

        if instance.is_accumulation():
            if utility_type is None:
                return
            datasequence = Consumption.\
                objects.create(
                    customer=customer,
                    unit=instance.unit,
                    encryption_data_initialization_vector=fake_iv,
                    name='')
            NonpulsePeriod.objects.create(
                from_timestamp=from_timestamp,
                datasequence=datasequence,
                datasource=instance)
            ConsumptionAccumulationAdapter.objects.create(
                customer=customer,
                datasequence=datasequence,
                utility_type=utility_type,
                role=role,
                unit=datasequence.unit)
        else:
            # non-accumulations
            if utility_type is None:
                utility_type = utilitytypes.OPTIONAL_METER_CHOICES.unknown
            datasequence = NonaccumulationDataSequence.objects.create(
                customer=customer,
                unit=instance.unit,
                encryption_data_initialization_vector=fake_iv,
                name='')
            NonaccumulationPeriod.objects.create(
                from_timestamp=from_timestamp,
                datasequence=datasequence,
                datasource=instance)
            NonaccumulationAdapter.objects.create(
                customer=customer,
                datasequence=datasequence,
                utility_type=utility_type,
                role=role,
                unit=instance.unit)
