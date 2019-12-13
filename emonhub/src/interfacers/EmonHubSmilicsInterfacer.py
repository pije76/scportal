'''
    Interface conf:
    [[SMILICS_INTERFACE]]
        Type = EmonHubSmilicsInterfacer
        [[[init_settings]]]
            port = 8080
        [[[runtimesettings]]]
            pubchannels = ToCloud
            subchannels = ToNothing

    Node conf:
    Using the Wibeee mac-address as node id

    [[121111111111]]
        nodename = SMILICS01
        firmware =V120
        hardware = Smilics Wibeee
        [[[rx]]]
           names = power1, power2, power3, power_total, wh1, wh2, wh3, wh_total
           datacodes = h, h, h, h, h, h, h, h
           scales       = 1, 1, 1, 1, 1, 1, 1, 1
           units = W, W, W, W, Wh, Wh, Wh, Wh
'''

import threading
import datetime
import time
import traceback

from BaseHTTPServer import BaseHTTPRequestHandler
from Queue import Queue
from SocketServer import TCPServer, ThreadingMixIn
from urlparse import parse_qs
from pydispatch import dispatcher

import Cargo
import emonhub_coder as ehc
from emonhub_interfacer import EmonHubInterfacer


class ThreadedTCPServer(ThreadingMixIn, TCPServer):
    def serve_forever(self, queue):
        self.RequestHandlerClass.queue = queue
        TCPServer.serve_forever(self)


class ServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = parse_qs(self.path[17:])
        data['timestamp'] = datetime.datetime.now()
        print data
        #self.queue.put(data)


class EmonHubSmilicsInterfacer(EmonHubInterfacer):
    """ Interface for the Smilics Wibee

    Listen for get request on the specified port
    """

    def __init__(self, name, port):
        """
        Args:
            name (str): Configuration name.
            port (int): The port the webserver should listen on.
        """
        super(EmonHubSmilicsInterfacer, self).__init__(name)

        self._settings = {
            'subchannels': ['ch1'],
            'pubchannels': ['ch2'],
        }
        self._queue = Queue()
        self._server = ThreadedTCPServer(("0.0.0.0", int(port)), ServerHandler)
        self.last_reading = None
        self.wh_counter1 = 0
        self.wh_counter2 = 0
        self.wh_counter3 = 0
        self.wh_counter4 = 0
        self.acc_power1 = 0
        self.acc_power2 = 0
        self.acc_power3 = 0
        self.acc_power4 = 0

    def close(self):
        """Cleanup when the interface closes"""
        if self._server is not None:
            self._log.debug('Closing server')
            self._server.shutdown()
            self._server.server_close()

    def run(self):
        """Starts the server on a new thread and processes the queue"""
        server_thread = threading.Thread(
            target=self._server.serve_forever, args=(self._queue,))
        server_thread.daemon = True
        server_thread.start()

        while not self.stop:
            while not self._queue.empty():
                rxc = self._process_rx(self._queue.get(False))
                self._queue.task_done()

                if rxc:
                    for channel in self._settings["pubchannels"]:
                        dispatcher.send(channel, cargo=rxc)
                        self._log.debug(
                            str(rxc.uri) + " Sent to channel' : " +
                            str(channel))
            time.sleep(0.1)

        self.close()

    def _process_rx(self, smilics_dict):
        """ Converts the data recieved on the webserver to an instance of
        the Cargo class

        Args:
            smilics_dict: Dict with smilics data.

        Returns:
            Cargo if successful, None otherwise.
        """
        try:
            c = Cargo.new_cargo()
            if 'mac' not in smilics_dict.keys():
                return None

            c.nodeid = smilics_dict['mac'][0]
            if c.nodeid not in ehc.nodelist.keys():
                self._log.debug(str(c.nodeid) + " Not in config")
                return None

            timestamp = smilics_dict['timestamp']
            if not self.last_reading:
                self.last_reading = timestamp
                return None

            time_between = timestamp - self.last_reading
            time_between = time_between.total_seconds()

            self.last_reading = timestamp

            self.wh_counter1 += float(smilics_dict['a1'][0])
            self.wh_counter2 += float(smilics_dict['a2'][0])
            self.wh_counter3 += float(smilics_dict['a3'][0])
            self.wh_counter4 += float(smilics_dict['at'][0])

            i_delta = self.wh_counter1 / (3600 / time_between)
            self.acc_power1 += i_delta
            self.wh_counter1 -= (i_delta * (3600 / time_between))

            i_delta = self.wh_counter2 / (3600 / time_between)
            self.acc_power2 += i_delta
            self.wh_counter2 -= (i_delta * (3600 / time_between))

            i_delta = self.wh_counter3 / (3600 / time_between)
            self.acc_power3 += i_delta
            self.wh_counter3 -= (i_delta * (3600 / time_between))

            i_delta = self.wh_counter4 / (3600 / time_between)
            self.acc_power4 += i_delta
            self.wh_counter4 -= (i_delta * (3600 / time_between))

            node_config = ehc.nodelist[str(c.nodeid)]

            c.names = node_config['rx']['names']
            c.nodename = node_config['nodename']

            c.realdata = [
                smilics_dict['a1'][0],
                smilics_dict['a2'][0],
                smilics_dict['a3'][0],
                smilics_dict['at'][0],
                self.acc_power1,
                self.acc_power2,
                self.acc_power3,
                self.acc_power4,
            ]
            c.timestamp = time.mktime(timestamp.timetuple())

            return c
        except:
            traceback.print_exc()
            return None

    def set(self, **kwargs):
        """ Override default settings with settings entered in the config file
        """
        for key, setting in self._settings.iteritems():
            if key in kwargs.keys():
                # replace default
                self._settings[key] = kwargs[key]
