"""class EmonHubTesterGenInterfacer

"""
import time
import Cargo
from pydispatch import dispatcher
from emonhub_interfacer import EmonHubInterfacer

class EmonHubTesterInterfacer(EmonHubInterfacer):

    def __init__(self, name, mqtt_host="127.0.0.1", mqtt_port=1883):
        # Initialization
        super(EmonHubTesterInterfacer, self).__init__(name)
        
        self._name = name
        
        self._settings = {
            'subchannels':['ch1'],
            'pubchannels':['ch2']
        };
        

    def run(self):

        last = time.time()
        consumption = 0
        time_consumption = 0
        while not self.stop:
            # Read the input and process data if available
            
            now = time.time()
            if (now-last)>5.0:
                time_consumption += int(now-last)
                last = now

                #if time_consumption == 30:
                #    consumption = 0
                
                self._log.debug("5s loop")
                rxc = Cargo.new_cargo()
                rxc.nodeid = 10
                rxc.nodename = "EMONTEST"
                rxc.names = ['power1', 'power2', 'power3', 'power4', 'Vrms', 'pulse',
                             'Wh1', 'Wh2', 'Wh3', 'Wh4', 'RunHours1', 'RunHours2', 'RunHours3', 'RunHours4']

                rxc.realdata = [10,10,10,10,230,0,consumption,consumption,consumption,consumption,
                                time_consumption,time_consumption,time_consumption,time_consumption]

                consumption += 10


                for channel in self._settings["pubchannels"]:
                    dispatcher.send(channel, cargo=rxc)
                    self._log.debug(str(rxc.uri) + " Sent to channel' : " + str(channel))
                  
            # Don't loop to fast
            time.sleep(0.1)
            # Action reporter tasks
            # self.action()

    def receiver(self, cargo):
        pass
        
    
    def set(self, **kwargs):
        for key,setting in self._settings.iteritems():
            if key in kwargs.keys():
                # replace default
                self._settings[key] = kwargs[key]
        
        # Subscribe to internal channels   
        for channel in self._settings["subchannels"]:
            dispatcher.connect(self.receiver, channel)
            self._log.debug(self._name+" Subscribed to channel' : " + str(channel))
