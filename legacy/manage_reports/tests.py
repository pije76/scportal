# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from decimal import Decimal

from django.test import TestCase
from django.test.utils import override_settings
from django.conf import settings

import pytz

from gridplatform import trackuser
from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.models import CollectionConstraint
from gridplatform.customers.models import Customer
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.energy_use_reports.models import EnergyUseArea
from legacy.energy_use_reports.models import EnergyUseReport
from legacy.indexes.models import Index
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.models import ChainLink
from legacy.measurementpoints.models import DataSeries
from legacy.measurementpoints.models import StoredData
from gridplatform.providers.models import Provider
from gridplatform.trackuser import replace_user
from gridplatform.users.models import User
from gridplatform.utils import DATETIME_MAX
from gridplatform.utils import DATETIME_MIN

from .views import GenerateReportForm


@override_settings(
    ENCRYPTION_TESTMODE=True,
    MIDDLEWARE_CLASSES=[
        x for x in settings.MIDDLEWARE_CLASSES
        if x != 'gridplatform.trackuser.middleware.TrackUserMiddleware'])
class TestGenerateReportForm(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(name_plain='Test customer', timezone=pytz.utc)
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.client.login(username='testuser', password='testpassword')

        self.tariff1 = Index.objects.create(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="Test eltariff",
            timezone="Europe/Copenhagen",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SEASONS,
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.tariff1.seasonindexperiod_set.create(
            from_date=DATETIME_MIN,
            value_at_hour=[Decimal("1") for _ in range(24)])

        self.collection = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain="Test Collection",
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.collection.consumption = DataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.collection.tariff_list = [ChainLink(
            valid_from=DATETIME_MIN,
            data_series=self.tariff1)]
        self.collection.save()

        StoredData.objects.create(
            data_series=self.collection.consumption,
            value=1,
            timestamp=DATETIME_MIN)
        StoredData.objects.create(
            data_series=self.collection.consumption,
            value=2,
            timestamp=DATETIME_MAX)

    def tearDown(self):
        trackuser._set_customer(None)

    def test_dependency(self):
        collection = Collection.objects.create(
            name='test collection',
            customer=self.customer,
            role=Collection.GROUP,
            utility_type=0)

        collection2 = Collection.objects.create(
            name='test collection 2',
            customer=self.customer,
            role=Collection.GROUP,
            utility_type=0)

        self.user = User.objects.create_user(
            'username', 'password', user_type=0)
        self.user.save()
        with replace_user(self.user):
            form = GenerateReportForm()
            self.assertIn(
                (collection.id, collection.name),
                form.fields['collections'].choices)
            self.assertIn(
                (collection2.id, collection2.name),
                form.fields['collections'].choices)

            CollectionConstraint.objects.create(
                collection_id=collection2.id,
                userprofile=self.user.userprofile)

            assert list(
                self.user.userprofile.collections.all()) == [collection2]

            form = GenerateReportForm()

            self.assertNotIn(
                (collection.id, collection.name),
                form.fields['collections'].choices)
            self.assertIn(
                (collection2.id, collection2.name),
                form.fields['collections'].choices)

            self.assertEqual(len(form.get_collections()), 1)

    def test_valid_tariff(self):
        user = User.objects.create_user(
            'username', 'password', user_type=0)
        with replace_user(user):
            response = self.client.post(
                '/reports/request/',
                data={
                    'collections': str(self.collection.id),
                    'from_date': str(DATETIME_MIN.date()),
                    'to_date': str(DATETIME_MAX.date()),
                    'include_cost': 'on'
                }
            )
            self.assertNotContains(response, 'form_errors')
            self.client.logout()


@override_settings(ENCRYPTION_TESTMODE=True)
class TestEnergyUseReports(TestCase):
    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(name_plain='Test customer', timezone=pytz.utc)
        self.customer.save()
        trackuser._set_customer(self.customer)

        self.super_user = User.objects.create_user(
            username='testsuperuser', password='testpassword',
            user_type=User.CUSTOMER_SUPERUSER, customer=self.customer)

        self.client.login(username='testsuperuser', password='testpassword')

        self.main_mp_1 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain="First main measurement point",
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.main_mp_1.consumption = DataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.main_mp_1.save()

        self.main_mp_2 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain="Second main measurement point",
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.main_mp_2.consumption = DataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.main_mp_2.save()

        self.mp_1 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain="Test MP 1",
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.mp_1.consumption = DataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.mp_1.save()

        self.mp_2 = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain="Test MP 2",
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.mp_2.consumption = DataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.mp_2.save()

        self.mp_heat = ConsumptionMeasurementPoint(
            customer=self.customer,
            name_plain="Test MP DISTRICT_HEATING",
            role=Collection.CONSUMPTION_MEASUREMENT_POINT,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating)
        self.mp_heat.consumption = DataSeries.objects.create(
            customer=self.customer,
            role=DataRoleField.CONSUMPTION,
            unit='milliwatt*hour',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating)
        self.mp_2.save()

        self.report = EnergyUseReport.objects.create(
            customer=self.customer,
            title_plain="Test report",
            currency_unit='currency_dkk',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        self.report.main_measurement_points.add(
            *[self.main_mp_1, self.main_mp_2])

        self.area = EnergyUseArea.objects.create(
            report=self.report,
            name_plain="Test Area")
        self.area.measurement_points.add(*[self.mp_1, self.mp_2])

    def tearDown(self):
        trackuser._set_customer(None)

    def test_report_index_page(self):
        response = self.client.get(
            '/reports/')

        self.assertNotContains(response, 'XYZXYZXYZ')
        self.assertContains(response, self.report.title_plain)

    def test_create_form_get(self):
        response = self.client.get(
            '/reports/create/energy_use/electricity/')

        self.assertNotContains(response, 'XYZXYZXYZ')

    def test_create_empty_fail(self):
        response = self.client.post(
            '/reports/create/energy_use/electricity/',
            data={
                'title': '',
                'currency_unit': '',
                'main_measurement_points': '',
                'energyusearea_set-TOTAL_FORMS': '1',
                'energyusearea_set-INITIAL_FORMS': '0',
                'energyusearea_set-MAX_NUM_FORMS': '1000',
                'energyusearea_set-0-name': '',
                'energyusearea_set-0-measurement_points': '',
            })

        self.assertContains(response, 'errorlist')
        self.assertNotContains(response, 'XYZXYZXYZ')

    def test_create_success(self):
        response = self.client.post(
            '/reports/create/energy_use/electricity/',
            data={
                'title': 'Test report',
                'currency_unit': 'currency_dkk',
                'main_measurement_points': [
                    self.main_mp_1.id,
                    self.main_mp_2.id,
                ],
                'energyusearea_set-TOTAL_FORMS': '1',
                'energyusearea_set-INITIAL_FORMS': '0',
                'energyusearea_set-MAX_NUM_FORMS': '1000',
                'energyusearea_set-0-name': 'Lighting',
                'energyusearea_set-0-measurement_points': [
                    self.mp_2.id,
                    self.mp_1.id,
                ],
            })
        self.assertNotContains(response, 'XYZXYZXYZ', 302)
        created_report = EnergyUseReport.objects.latest('id')
        self.assertEqual(created_report.energyusearea_set.count(), 1)
        self.assertEqual(created_report.energyusearea_set.get().
                         measurement_points.count(), 2)
        self.assertEqual(created_report.main_measurement_points.count(), 2)

    def test_update_form_get(self):
        response = self.client.get(
            '/reports/update/energy_use/%s/' % self.report.id)
        self.assertNotContains(response, 'XYZXYZXYZ')

    def test_update_empty_fail(self):
        response = self.client.post(
            '/reports/update/energy_use/%s/' % self.report.id,
            data={
                'title': '',
                'currency_unit': '',
                'main_measurement_points': '',
                'energyusearea_set-TOTAL_FORMS': '1',
                'energyusearea_set-INITIAL_FORMS': '0',
                'energyusearea_set-MAX_NUM_FORMS': '1000',
                'energyusearea_set-0-name': '',
                'energyusearea_set-0-measurement_points': '',
            })
        self.assertContains(response, 'errorlist')
        self.assertNotContains(response, 'XYZXYZXYZ')

    def test_update_success(self):
        response = self.client.post(
            '/reports/update/energy_use/%s/' % self.report.id,
            data={
                'title': 'Altered report',
                'currency_unit': 'currency_dkk',
                'main_measurement_points': self.main_mp_1.id,
                'energyusearea_set-TOTAL_FORMS': '1',
                'energyusearea_set-INITIAL_FORMS': '0',
                'energyusearea_set-MAX_NUM_FORMS': '1000',
                'energyusearea_set-0-name': 'Lights',
                'energyusearea_set-0-measurement_points': self.mp_1.id,
                'energyusearea_set-1-id': '',
                'energyusearea_set-1-name': 'Production line',
                'energyusearea_set-1-measurement_points': self.mp_2.id
            })
        self.assertNotContains(response, 'XYZXYZXYZ', status_code=302)
        altered_report = EnergyUseReport.objects.get(id=self.report.id)
        self.assertEqual(altered_report.energyusearea_set.count(), 2)
        self.assertEqual(altered_report.main_measurement_points.count(), 1)
