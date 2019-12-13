from random import randint

import datetime
import pytz
from RPi import GPIO


class RelayHandler:

    def __init__(self, configuration):
        self.configuration = configuration
        self.prev_port_setting = -1
        self.pins = [2, 3, 4, 17, 27, 22, 10, 9]

        GPIO.setmode(GPIO.BCM)

        for i in self.pins:
            GPIO.setup(i, GPIO.OUT)
            GPIO.output(i, GPIO.HIGH)

    def update_ports(self, forecast_data):
        now = datetime.datetime.now().replace(tzinfo=pytz.utc) # + datetime.timedelta(hours=2)
        port_setting = 0

        if not forecast_data:
            port_setting = 9
        else:
            for setting in forecast_data:
                print setting['timestamp'], now
                if setting['timestamp'] < now < setting['timestamp'] + datetime.timedelta(hours=1):
                    print setting['timestamp'], setting['relay']
                    port_setting = setting['relay']

        if self.prev_port_setting != port_setting:
            for i in self.pins:
                GPIO.output(i, GPIO.HIGH)

            self.open_port(port_setting)
            self.prev_port_setting = port_setting

    def open_port(self, port_number):

        if port_number == 0:
            for i in self.pins:
                GPIO.output(i, GPIO.LOW)
        else:
            self.set_port_state(port_number, GPIO.LOW)

    def close_port(self, port_number):

        self.set_port_state(port_number, GPIO.HIGH)

    def set_port_state(self, port_number, state):
        if 0 < port_number < 9:
            GPIO.output(self.pins[port_number - 1], state)




