from __future__ import absolute_import

import datetime
import logging
import traceback

from django.db import DatabaseError
from django.db import close_connection
from django.db import transaction
from pytz import utc
from twisted.internet import reactor
from twisted.internet import task
from twisted.internet import threads

from gridagentserver_protocol import server_messages
from gridagentserver_protocol.client_messages import AcknowledgementGaSoftware
from gridagentserver_protocol.client_messages import AcknowledgementGpSoftware
from gridagentserver_protocol.client_messages import ErrorGaSoftware
from gridagentserver_protocol.client_messages import ErrorGpSoftware
from gridagentserver_protocol.server_messages import ConfigGaSoftware
from gridagentserver_protocol.server_messages import ConfigGpSoftware
from gridagentserver_protocol.twisted_protocol import BaseAgentProtocol
from gridagentserver_protocol.twisted_protocol import BaseAgentProtocolFactory
from legacy.devices.models import Agent
from legacy.devices.models import RawData

from . import db
from . import settings


logger = logging.getLogger(__name__)


WATER_FREEZING_POINT_MILLIKELVIN = 273150


class AgentProtocol(BaseAgentProtocol):
    def __init__(self):
        BaseAgentProtocol.__init__(self)
        self.polling = None
        self.syncing = None
        self.incoming.get().addCallback(self.process_message)
        self.agent_mac = None
        # self.software_message = None
        self.sw_version = None
        self.hw_revision = None
        self.serial = None
        self.poll_response_pending = False

    def pause_sending_after(self, message):
        if isinstance(message, (ConfigGpSoftware, ConfigGaSoftware)):
            # self.software_message = message
            return True
        else:
            return False

    def resume_sending_after(self, message):
        if isinstance(message, (AcknowledgementGpSoftware,
                                AcknowledgementGaSoftware)):
            # self.software_message = None
            return True
        elif isinstance(message, (ErrorGpSoftware, ErrorGaSoftware)):
            # self.send_message(self.software_message)
            # return False
            # NOTE: continue normal processing on "error"
            # TODO: put in event log...?
            return True
        else:
            return False

    # Messages from the "incoming" queue should be handled in background
    # threads for the database access, but one at a time to serialise the
    # database access per agent connection...
    def process_message(self, message):
        logger.debug('Processing message %s for %X', message, self.agent_mac)
        background_task = threads.deferToThread(
            self.do_process_message, message)

        # Attach (and possibly immediately call) callback to handle next
        # incoming message as soon as the background processing of the current
        # message is done.  (The return value of the background call is
        # provided as argument.)
        def attach_next_callback(_ignored):
            deferred = self.incoming.get()
            deferred.addCallback(self.process_message)
        background_task.addCallback(attach_next_callback)

    def do_process_message(self, message):
        try:
            message.accept(self)
        except DatabaseError as e:
            logger.warning('DatabaseError on processing message: %s', e)
            logger.warning(traceback.format_exc())
            close_connection()

    def register(self):
        logger.info('Agent %X connected', self.other_id)
        old_replaced = BaseAgentProtocol.register(self)
        if old_replaced:
            logger.info('Replaced old handler for %X', self.agent_mac)
        self.store_online(initial=True)

    def store_online(self, initial=False):
        timestamp = datetime.datetime.utcnow().replace(tzinfo=utc)

        def does_not_exist_handler(failure):
            failure.trap(Agent.DoesNotExist)
            logger.info('Unknown agent %X; disconnecting', self.agent_mac)
            self.transport.loseConnection()
            return failure

        @transaction.commit_on_success
        def background_store_online():
            db.set_agent_online(True, timestamp, self.agent_mac)

        background_task = threads.deferToThread(background_store_online)
        background_task.addErrback(does_not_exist_handler)
        background_task.addCallback(self.stored_online)
        if initial:
            background_task.addCallback(self.delayed_start_periodic)

    def stored_online(self, _ignored=None):
        assert self.agent_mac
        if self.agent_mac not in self.factory.handlers:
            # currently offline, so undo setting it online
            self.store_offline()

    def unregister(self):
        replaced = BaseAgentProtocol.unregister(self)
        self.stop_periodic()
        if not self.agent_mac:
            return
        if replaced:
            logger.info('Agent %X already reconnected', self.agent_mac)
        else:
            logger.info('Agent %X disconnected', self.agent_mac)
            self.store_offline()

    def store_offline(self):
        timestamp = datetime.datetime.utcnow().replace(tzinfo=utc)

        @transaction.commit_on_success
        def background_store_offline():
            db.set_agent_online(False, timestamp, self.agent_mac)
        background_task = threads.deferToThread(background_store_offline)
        background_task.addCallback(self.stored_offline)

    def stored_offline(self, _ignored=None):
        if self.agent_mac and self.agent_mac in self.factory.handlers:
            # currently online, so undo setting it offline...
            self.store_online()

    def start_periodic(self, _ignored=None):
        logger.debug('Starting periodic tasks for %X', self.agent_mac)

        def poll():
            if self.poll_response_pending:
                logger.info(
                    'Agent %s did not respond to poll in time; disconnecting',
                    self.agent_mac)
                self.transport.loseConnection()
            else:
                self.poll_response_pending = True
                self.outgoing.put(server_messages.CommandGaPollMeasurements())

        self.polling = task.LoopingCall(poll)
        self.polling.start(settings.POLL_INTERVAL, now=False)

        def sync():
            timestamp = datetime.datetime.utcnow().replace(tzinfo=utc)
            self.outgoing.put(server_messages.ConfigGaTime(timestamp))

        self.syncing = task.LoopingCall(sync)
        self.syncing.start(settings.TIME_SYNC_INTERVAL.total_seconds(),
                           now=True)

    def delayed_start_periodic(self, _ignored=None):
        reactor.callLater(10, self.start_periodic)

    def stop_periodic(self):
        if self.agent_mac:
            logger.debug('Stopping periodic tasks for %X', self.agent_mac)
        if self.polling:
            self.polling.stop()
        if self.syncing:
            self.syncing.stop()

    @transaction.commit_on_success
    def visit_bulk_measurements(self, message):
        self.poll_response_pending = False
        meter_ids = set([
            meter
            for meter, measurement_sets in message.meter_data])
        meters = {
            meter_id: db.get_meter(meter_id, self.agent_mac)
            for meter_id in meter_ids}

        physicalinput_params = set()

        for meter_id, measurement_sets in message.meter_data:
            for timestamp, measurements in measurement_sets:
                for measurement in measurements:
                    datatype, agent_unit, input_number, value = measurement
                    physicalinput_params.add(
                        (datatype, agent_unit, input_number, meter_id))
        physicalinputs = {
            (datatype, agent_unit, input_number, meter_id):
            db.get_physicalinput(
                datatype, agent_unit, input_number, meters[meter_id])
            for (datatype, agent_unit, input_number, meter_id)
            in physicalinput_params
            if db.get_physicalinput(
                datatype, agent_unit, input_number, meters[meter_id])
        }

        result_measurements = []

        for meter_id, measurement_sets in message.meter_data:
            for timestamp, measurements in measurement_sets:
                if timestamp.tzinfo is None:
                    aware_timestamp = timestamp.replace(tzinfo=utc)
                else:
                    aware_timestamp = timestamp
                for measurement in measurements:
                    datatype, agent_unit, input_number, value = measurement
                    if (datatype, agent_unit, input_number, meter_id) not in \
                            physicalinputs:
                        # Ignore inputs with unsupported units
                        continue
                    physicalinput = physicalinputs[
                        (datatype, agent_unit, input_number, meter_id)]
                    if aware_timestamp > datetime.datetime.now(utc) + \
                            datetime.timedelta(days=1):
                        # FIXME: Temporary workaround for GridLink bug;
                        # sometimes gives spurious future data.  To be removed
                        # ASAP, after making/deploying GridLink fix.
                        # skip storing this wrong data to the database...
                        continue
                    if physicalinput.store_measurements:
                        # FIXME: Temporary work-around for GridAgents reporting
                        # absolute temperatures in Celsius.
                        MILLIKELVIN = 6
                        if agent_unit == MILLIKELVIN:
                            result_measurements.append(
                                RawData(
                                    datasource=physicalinput,
                                    value=(
                                        measurement.value +
                                        WATER_FREEZING_POINT_MILLIKELVIN),
                                    timestamp=aware_timestamp))
                        else:
                            result_measurements.append(
                                RawData(
                                    datasource=physicalinput,
                                    value=measurement.value,
                                    timestamp=aware_timestamp))
        RawData.objects.bulk_create(result_measurements)

    @transaction.commit_on_success
    def visit_notification_ga_add_mode(self, message):
        db.set_agent_add_mode(message.in_add_mode, message.timestamp,
                              self.agent_mac)

    # avoid background thread?
    def visit_notification_ga_time(self, message):
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        diff = message.timestamp.replace(tzinfo=utc) - now
        if abs(diff.total_seconds()) < settings.TIME_SYNC_TOLERANCE:
            reactor.callFromThread(self.outgoing.put,
                                   server_messages.CommandGaPropagateTime())
        else:
            reactor.callFromThread(self.outgoing.put,
                                   server_messages.ConfigGaTime(now))

    @transaction.commit_on_success
    def visit_notification_ga_connected_set(self, message):
        logger.debug('Agent %X reported meters %s',
                     self.agent_mac, message.meters)
        db.set_meters_online(self.agent_mac, message.meters, message.versions,
                             message.device_opts)

    @transaction.commit_on_success
    def visit_notification_gp_state(self, message):
        db.set_meter_state(message.control_manual, message.relay_on,
                           message.online, message.timestamp,
                           message.meter, self.agent_mac)

    @transaction.commit_on_success
    def visit_info_agent_versions(self, message):
        self.sw_version = message.sw_version
        self.device_type = message.device_type
        self.hw_revision = message.hw_revision
        self.serial = message.serial
        if self.serial < 0:
            logger.warning('Invalid serial#: %s, agent: %X',
                           self.serial, self.agent_mac)
            self.serial = 0
        db.set_agent_info(self.agent_mac, self.serial, self.device_type,
                          self.hw_revision, self.sw_version)

    @transaction.commit_on_success
    def visit_info_event_log(self, message):
        db.store_event(
            self.agent_mac,
            message.timestamp,
            message.code,
            message.text)

    # @transaction.commit_on_success
    def send_complete_configuration(self, conn):
        """Obtain and send configuration for agent."""
        # TODO: implement...


# must initialise self.amqp after init
class AgentProtocolFactory(BaseAgentProtocolFactory):
    protocol = AgentProtocol

    def __init__(self):
        BaseAgentProtocolFactory.__init__(self)

    def register(self, handler):
        result = BaseAgentProtocolFactory.register(self, handler)
        self.amqp.add_route('agent.{:012x}'.format(handler.agent_mac))
        return result

    def unregister(self, handler):
        replaced = BaseAgentProtocolFactory.unregister(self, handler)
        if not replaced and handler.agent_mac:
            self.amqp.remove_route('agent.{:012x}'.format(handler.agent_mac))
        return replaced

    def startFactory(self):
        logger.info('Started')

    def stopFactory(self):
        logger.info('Stopping')
