# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import datetime
from datetime import timedelta

from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse

import pytz

from gridplatform import trackuser
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from gridplatform.encryption.shell import Request
from legacy.indexes.models import Index
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.models import ChainLink
from legacy.measurementpoints.models import DataSeries
from legacy.projects.models import BenchmarkProject
from gridplatform.users.models import User
from gridplatform.utils import DATETIME_MIN
from legacy.devices.models import PhysicalInput


@override_settings(ENCRYPTION_TESTMODE=True)
class DisplayProjectsTest(TestCase):
    fixtures = ["manage_indexes_test.json"]

    def setUp(self):
        self.client.post('/login/', {"username": "super",
                                     'password': "123"})

        self.customer = User.objects.get(
            id=self.client.session["_auth_user_id"]).customer
        trackuser._set_customer(self.customer)

        self.request = Request('super', '123')

        self.electricity_index = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="electricity index",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SEASONS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            timezone='Europe/Copenhagen')
        self.electricity_index.save()

        self.measurement_point = ConsumptionMeasurementPoint(
            name_plain='Test measurement point',
            role=ConsumptionMeasurementPoint.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.tariff_list = [ChainLink(
            valid_from=DATETIME_MIN,
            data_series=self.electricity_index)]

        self.measurement_point.consumption = DataSeries(
            role=DataRoleField.CONSUMPTION,
            unit='kilowatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.measurement_point.save()

    def tearDown(self):
        trackuser._set_customer(None)

    def test_dependencies(self):
        NOW = datetime.datetime.now(pytz.utc)

        project = BenchmarkProject.objects.create(
            name_plain="Test project",
            utility_type=PhysicalInput.ELECTRICITY,
            baseline_from_timestamp=NOW,
            baseline_to_timestamp=NOW + timedelta(days=1),
            result_from_timestamp=NOW + timedelta(days=2),
            result_to_timestamp=NOW + timedelta(days=3))

        project.baseline_measurement_points.add(self.measurement_point)
        project.result_measurement_points.add(self.measurement_point)

        # Verify that the MP which this project depends on cannot be deleted.
        response = self.client.get(
            reverse(
                'manage_measurementpoints:measurement_point-update',
                args=(self.measurement_point.id, )))
        self.assertContains(response, 'data-reason')
