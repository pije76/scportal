import argparse
import sys
import signal
import time

import datetime
from RPi import GPIO

from forecast_configuration import ForecastConfiguration
from relay_handler import RelayHandler
from request_handler import RequestHandler


class Forecast:
    __version__ = "Forecast v0.1"

    def __init__(self, configuration):
        self._exit = False
        self.configuration = configuration
        self.last_request_time = None

    def run(self):
        signal.signal(signal.SIGINT, self._sigint_handler)
        request = RequestHandler(self.configuration)
        relay = RelayHandler(self.configuration)
        forecast_data = None

        while not self._exit:
            if not self.last_request_time or \
                    datetime.datetime.now() >= self.last_request_time + datetime.timedelta(seconds=10):
                new_data = request.fetch_forecast()
                print new_data
                if new_data:
                    forecast_data = new_data
                self.last_request_time = datetime.datetime.now()

            relay.update_ports(forecast_data)

            time.sleep(0.2)

    def _sigint_handler(self, signal, frame):
        self._exit = True
        GPIO.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SC Nordic Forecast Relay")

    parser.add_argument("--config-file", action="store", help="Path to configuration file", default="forecast.conf")

    parser.add_argument("--version", action="store_true", help="Display version number")

    args = parser.parse_args()

    if args.version:
        print Forecast.__version__
        sys.exit()

    configuration = None
    try:
        configuration = ForecastConfiguration(args.config_file)
        
    except Exception as e:
        print e.message
        sys.exit()
    
    try:
        forecast = Forecast(configuration.configuration)
        
    except Exception as e:
        print e.message
        sys.exit("Could not start Forecast daemon")
    else:
        forecast.run()

