import datetime
import requests

from requests.auth import AuthBase
from django.conf import settings

from .models import EndpointCache


class TokenAuth(AuthBase):
    """Attaches HTTP Token Authentication to the given Request object."""
    def __init__(self, token):
        # setup any auth-related data here
        self.token = token

    def __call__(self, r):
        # modify and return the request
        r.headers['Authorization'] = "token %s" % self.token
        return r


class RequestHandler():

    def __init__(self):
        if settings.DEBUG:
            self.auth = TokenAuth('9dc8c71d767673d21552055c856977c1a33700925ad44d85db2f76a91d829efba50ac4f50dec8d39dd354eb3e9180780b55f8506')
            self.base_url = "http://192.168.13.37:8000/api/v3" 
        else:
            self.auth = TokenAuth(settings.API_TOKEN)
            self.base_url = settings.API_BASE_URL

    def fetch_endpoint(self, mac):
        payload = {'hardware_id': mac}
        r = requests.get('%s/datasources/customer_datasources/' % self.base_url, auth=self.auth, params=payload, timeout=1)
        response = {}
        
        if r.status_code == requests.codes.ok:
            response = r.json()

            if response['count'] == 1:
                EndpointCache.objects.update_or_create(
                    mac=response['results'][0]['hardwareId'], defaults={'timestamp': datetime.datetime.now(), 'endpoint': response['results'][0]['rawData']})
                return response['results'][0]['rawData']

            else: 
                return None
        else:
            return None

    def get_endpoint(self, mac):
        cached = EndpointCache.objects.filter(mac=mac)
        if cached and cached[0].timestamp.replace(tzinfo=None) > datetime.datetime.now() - datetime.timedelta(minutes=10):
            return cached[0].endpoint

        else:
            return self.fetch_endpoint(mac)

    # TODO: Handle error logging
    def send_measurement(self, measurement):
        endpoint = self.get_endpoint(measurement.mac)

        if endpoint:
            payload = {
                "timestamp": measurement.timestamp.strftime("%Y-%m-%dT%H:%M:%S"), 
                "value": int(measurement.vrms_total), 
                "unit": "volt"
            }

            r = requests.post(endpoint, auth=self.auth, data=payload)

            return r.status_code == requests.codes.created 

        return False

