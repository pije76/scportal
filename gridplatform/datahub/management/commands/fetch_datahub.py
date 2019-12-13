# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import json
import StringIO
from operator import itemgetter

import dateutil.parser
import pycurl
import pytz

from django.core.management.base import BaseCommand
from django.conf import settings

from gridplatform.datasources.models import RawData
from gridplatform.datahub.models import DatahubConnection


class Command(BaseCommand):
    help = "Import data from datahub"

    def handle(self, *args, **options):
        b = StringIO.StringIO()
        c = pycurl.Curl()
        url = 'https://eloverblik.dk/api/authorizationsv2'
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.SSLKEY, settings.NETS_KEY_DIR + "/plainkey.pem")
        c.setopt(pycurl.SSLCERT, settings.NETS_KEY_DIR + "/crt.pem")
        c.perform()
        c.close()
        response_body = b.getvalue()

        authorizations = json.loads(response_body)

        connections = DatahubConnection.objects.all()
        now = datetime.date.today()

        for connection in connections:
            if not connection.end_date or connection.end_date < now:
                for customer in authorizations:
                    for meter in customer["ListOfMeteringPoints"]:
                        if meter["MeteringPointIdentification"] == connection.customer_meter_number:
                            connection.start_date = dateutil.parser.parse(
                                customer["StartDate"]).date()
                            connection.end_date = dateutil.parser.parse(
                                customer["EndDate"]).date()
                            connection.authorization_id = customer["Id"]
                            connection.save()

            if connection.end_date and connection.end_date >= now:
                b = StringIO.StringIO()
                c = pycurl.Curl()
                url = 'https://eloverblik.dk/api/timeseries?authorizationid=' + \
                    str(connection.authorization_id) + '&meteringpointid=' + \
                    str(connection.customer_meter_number) + '&period=Month'
                c.setopt(pycurl.URL, url)
                c.setopt(pycurl.WRITEFUNCTION, b.write)
                c.setopt(pycurl.SSLKEY, settings.NETS_KEY_DIR + "/plainkey.pem")
                c.setopt(pycurl.SSLCERT, settings.NETS_KEY_DIR + "/crt.pem")
                c.perform()
                c.close()
                response_body = b.getvalue()
                measurements = json.loads(response_body)

                input_id = connection.meter.physicalinput_set.first().id
                last_value = 0
                last_timestamp = None
                try:
                    last_data = RawData.objects.filter(
                        datasource_id=input_id
                    ).latest('timestamp')
                    last_value = last_data.value
                    last_timestamp = last_data.timestamp
                except RawData.DoesNotExist:
                    pass

                if "Message" in measurements:
                    print measurements["Message"]
                else:
                    sorted_measurements = sorted(
                        measurements, key=itemgetter('DateFrom'))
                    for m in sorted_measurements:
                        timestamp = dateutil.parser.parse(m["DateTo"]).replace(
                            tzinfo=pytz.timezone('Europe/Copenhagen'))
                        if last_timestamp and last_timestamp >= timestamp:
                            continue
                        last_value += int(float(m["Usage"]) * 1000 * 1000)
                        last_timestamp = timestamp

                        RawData.objects.create(
                            timestamp=timestamp, datasource_id=input_id, value=last_value)

    def _update_or_create(self, timestamp, datasource_id, updated_values):
        try:
            obj = RawData.objects.get(
                timestamp=timestamp, datasource_id=datasource_id)
            for key, value in updated_values.iteritems():
                setattr(obj, key, value)
            obj.save()
        except RawData.DoesNotExist:
            updated_values.update(
                {'timestamp': timestamp, 'datasource_id': datasource_id, 'unit': "milliwatt*hour"})
            obj = RawData(**updated_values)
            obj.save()
