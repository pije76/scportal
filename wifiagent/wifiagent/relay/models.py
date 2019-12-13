import requests

from django.db import models


class Measurement(models.Model):
	mac = models.CharField("mac", max_length=50)
	ip = models.CharField("source ip", max_length=50)
	timestamp = models.DateTimeField() # TODO: No timezone...
	vrms_total = models.FloatField("Volt");
		

class EndpointCache(models.Model):
	mac = models.CharField("mac", max_length=50)
	endpoint = models.CharField("endpoint", max_length=256)
	timestamp = models.DateTimeField() # TODO: No timezone...
