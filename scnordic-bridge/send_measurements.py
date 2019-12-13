import mysql.connector
import redis
import datetime
import time
import requests
import sqlite3
import unicodedata

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
    def __init__(self):
        api_key = ''
        api_base_url = 'https://test.codewizards.dk/api/v3'
        with open('/home/pi/data/emonhub.conf') as f:
            for line in f:
                if api_key == '':
                    api_key = line.strip().replace('# ', '')
                else:
                    api_base_url = line.strip().replace("# ", "")
                    break

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
    def send_measurement(self, measurement):
        endpoint = self.get_endpoint(measurement['name'])

        if endpoint:
            payload = {
                "timestamp": measurement['timestamp'].strftime("%Y-%m-%dT%H:%M:%S"),
            }
            if measurement['unit'] == 'watthour':
                payload['value'] = int(float(measurement['value']) * 1000)
                payload['unit'] = "milliwatt*hour"
            elif measurement['unit'] == 'celcius':
                payload['value'] = int((float(measurement['value']) - 273.15) * 1000)
                payload['unit'] = "millikelvin"
            else:
                # If no tag is set, just return and throw it away
                return 200
            try:
                r = requests.post(endpoint, auth=self.auth, data=payload)
                return r.status_code
            except:
                return 500
        return 500


class MySQLHandler():
    def get_feeds(self):
        feeds = []
        cnx = mysql.connector.connect(user="root", password="raspberry", database="emoncms")
        cursor = cnx.cursor()
        cursor.execute("SELECT id, name, tag FROM feeds")

        for feed in cursor:
            feeds.append({'id': feed[0], 'name': feed[1], 'tag': feed[2]})

        return feeds


# TODO: Send all when enmonpi has been offline
# class FINAReader():
#	def read(feeds, ):
#		p = pyfina('/home/pi')

class RedisHandler():
    def __init__(self):
        self.redis = redis.StrictRedis(host='localhost', port=6379, db=0)

    def get_data(self, feed_id):
        return self.redis.hmget('feed:timevalue:%i' % feed_id, ['time', 'value'])


class SqLiteHandler():
    def __init__(self):
        conn = sqlite3.connect('/tmp/measurements.db')
        c = conn.cursor()
        c.execute(
            'CREATE TABLE IF NOT EXISTS measurements (id INTEGER PRIMARY KEY, name TEXT, timestamp INT, value REAL, unit TEXT);')
        conn.close()

    def save_measurement(self, name, timestamp, value, unit):
        conn = sqlite3.connect('/tmp/measurements.db')
        c = conn.cursor()
        c.execute('SELECT id FROM measurements WHERE name=? AND timestamp=? AND value=? AND unit=?',
                  (name, timestamp, value, unit,))
        if not c.fetchone():
            c.execute('INSERT INTO measurements (name, timestamp, value, unit) VALUES (?, ?, ?, ?)',
                      (name, timestamp, value, unit,))
        conn.commit()
        conn.close()

    def fetch_measurements(self):
        conn = sqlite3.connect('/tmp/measurements.db')
        c = conn.cursor()
        c.execute('SELECT * FROM measurements')
        measurements = c.fetchall()
        conn.close()

        return measurements

    def delete_measurement(self, id):
        conn = sqlite3.connect('/tmp/measurements.db')
        c = conn.cursor()
        c.execute('DELETE FROM measurements WHERE id=?', (id,))
        conn.commit()
        conn.close()


if __name__ == "__main__":
    myhandler = MySQLHandler()
    redishandler = RedisHandler()
    request = RequestHandler()
    feeds = myhandler.get_feeds()
    sqlite = SqLiteHandler()

    for feed in feeds:
        data = redishandler.get_data(feed['id'])
        if data[0] == '':
            continue

        timestamp = datetime.datetime.fromtimestamp(float(data[0]))
        value = data[1]
        sent = request.send_measurement(
            {'name': feed['name'], 'timestamp': timestamp, 'value': value, 'unit': feed['tag']})

        if sent in (500, 502):
            sqlite.save_measurement(feed['name'], data[0], value, feed['tag'])

        else:
            measurements = sqlite.fetch_measurements()
            for measurement in measurements:
                worked = request.send_measurement(
                    {'name': measurement[1], 'timestamp': datetime.datetime.fromtimestamp(float(measurement[2])),
                     'value': measurement[3], 'unit': measurement[4]})
                if not worked == 500:
                    sqlite.delete_measurement(measurement[0])
