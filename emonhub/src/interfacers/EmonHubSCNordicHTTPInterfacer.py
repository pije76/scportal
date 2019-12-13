"""class EmonHubEmoncmsHTTPInterfacer
"""
import time

from configobj import ConfigObj
from pydispatch import dispatcher
from emonhub_interfacer import EmonHubInterfacer
import emonhub_coder as ehc
from interfacers.portal_package import PortalPackage
from scnordic_bridge import RequestHandler


class EmonHubSCNordicHTTPInterfacer(EmonHubInterfacer):

    def __init__(self, name):
        # Initialization
        super(EmonHubSCNordicHTTPInterfacer, self).__init__(name)
        
        self._name = name
        
        self._settings = {
            'subchannels':['ch1'],
            'pubchannels':['ch2'],
            
            'apikey': "",
            'url': "http://emoncms.org",
            'sendinterval': 20,
            'prev_values_path': "/home/pi/data/prev_values.conf"
        }
        
        self.buffer = []
        self.lastsent = time.time()
        self.queue = []

        self.prev_values = {}
        self.correction_values = {}

    def receiver(self, cargo):
        '''
            Append cargo to sendbuffer if it's not in it allready
        '''

        if not [c for c in self.buffer if c.nodeid == cargo.nodeid]:
            self._log.debug(str(cargo.uri) + " adding cargo to buffer")
            self.buffer.append(cargo)

    def cargo_to_portal_packages(self, cargo):
        packages = []

        for index, value in enumerate(cargo.realdata):
            senddata = ehc.nodelist[str(cargo.nodeid)]['rx']['senddata'][index]
            if senddata == '1':
                unit = ehc.nodelist[str(cargo.nodeid)]['rx']['units'][index]
                name = "%s-%s" % (cargo.nodename, cargo.names[index])
                name = name.upper()
                value = float(value)
                if unit in ['Wh', 'p', 'sec']:
                    value = self.value_check(name, value)

                packages.append(PortalPackage(name, cargo.timestamp, value, unit))

                if unit in ['Wh', 'p', 'sec']:
                    self.prev_values[name] = value

        self.prev_values.write()

        return packages

    def action(self):
        now = time.time()
        
        if (now-self.lastsent) > (int(self._settings['sendinterval'])):
            self.lastsent = now
            # print json.dumps(self.buffer)

            self.bulkpost(self.buffer)
            self.buffer = []
            
    def bulkpost(self, databuffer):
    
        if not 'apikey' in self._settings.keys() or str.__len__(str(self._settings['apikey'])) != 104 \
                or str.lower(str(self._settings['apikey'])) == 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx':
            return

        request = RequestHandler(self._settings['apikey'], self._settings['url'])
        failed_packages = []

        for data in databuffer:
            packages = self.cargo_to_portal_packages(data)

            for package in packages:
                self.queue.append(package)

        failure = False
        for package in self.queue:

            sent = 500
            if not failure:
                sent = request.send_measurement(package)

            if sent in (500, 502):
                failure = True
                self._log.warning("send failure: wanted '200' but got '" + str(sent) + "'")
                failed_packages.append(package)

        self.queue = failed_packages

        return True
            
    def set(self, **kwargs):
        for key,setting in self._settings.iteritems():
            if key in kwargs.keys():
                # replace default
                self._settings[key] = kwargs[key]

        # Subscribe to internal channels
        for channel in self._settings["subchannels"]:
            dispatcher.connect(self.receiver, channel)
            self._log.debug(self._name+" Subscribed to channel' : " + str(channel))

        self.prev_values = ConfigObj(self._settings['prev_values_path'])

    def value_correction(self, name, value):
        return value + float(self.correction_values[name])

    def value_check(self, name, value):

        if name in self.correction_values:
            self._log.debug("Correcting value for: " + name)
            value = self.value_correction(name, value)

        if name in self.prev_values and value < self.prev_values[name]:
            self._log.debug("New value lower than the last. Setting up correction for: " + name)
            self.correction_values[name] = float(self.prev_values[name])
            value = self.value_correction(name, value)

        return value
