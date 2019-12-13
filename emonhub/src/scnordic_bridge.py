import datetime
import time
import requests

from configobj import ConfigObj
from requests.auth import AuthBase


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
    def __init__(self, api_key, api_base_url):

        self.auth = TokenAuth(api_key)
        self.base_url = api_base_url
        self.config = ConfigObj('/tmp/endpoint.cache')

    def fetch_endpoint(self, name):
        payload = {'hardware_id': name}
        try:
            r = requests.get('%s/datasources/customer_datasources/' % self.base_url, auth=self.auth, params=payload,
                             timeout=1)
        except:
            return None
        response = {}

        if r.status_code == requests.codes.ok:
            response = r.json()

            if response['count'] == 1:
                self.config[name] = {
                    'timestamp': time.time(),
                    'endpoint': response['results'][0]['rawData']
                }
                self.config.write()
                return response['results'][0]['rawData']
            else:
                return None
        else:
            return None

    def get_endpoint(self, name):
        try:
            cached = self.config[name]

            if (datetime.datetime.fromtimestamp(
                    float(cached['timestamp'])) > datetime.datetime.now() - datetime.timedelta(minutes=10)):
                return cached['endpoint']
            else:
                return self.fetch_endpoint(name)
        except KeyError:
            return self.fetch_endpoint(name)

    # TODO: Handle error logging
    def send_measurement(self, package):
        print package.datasource_name
        endpoint = self.get_endpoint(package.datasource_name)

        if endpoint:
            payload = {
                "timestamp": package.timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                "value": package.value,
                "unit": package.unit,
            }

            try:
                r = requests.post(endpoint, auth=self.auth, data=payload)
                return r.status_code
            except:
                return 500
        return 500








