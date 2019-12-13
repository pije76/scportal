import requests
import dateutil.parser
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


class RequestHandler:
    def __init__(self, configuration):
        self.configuration = configuration
        self.auth = TokenAuth(self.configuration['api_key'])

    def fetch_forecast(self):

        try:
            r = requests.get(self.configuration['url'], auth=self.auth, timeout=1)
        except Exception as e:
            print e.message
            return None

        if r.status_code == requests.codes.ok:
            response = r.json()

            if response['count'] == 1:
                settings = []
                for setting in response['results'][0]['relaySettings']:
                    settings.append(
                        {'timestamp': dateutil.parser.parse(setting['timestamp']), 'relay': setting['relay']})
                return settings
            else:
                return None
        else:
            return None
