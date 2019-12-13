# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.test import RequestFactory

from gridplatform import trackuser
from gridplatform.customer_datasources.models import CustomerDataSource
from gridplatform.customers.models import Customer
from legacy.measurementpoints.models import Location
from gridplatform.providers.models import Provider
from gridplatform.trackuser import replace_customer
from gridplatform.users.models import User
from legacy.datasequence_adapters.models import ConsumptionAccumulationAdapter
from legacy.datasequence_adapters.models import ProductionAccumulationAdapter
from legacy.devices.models import Agent
from legacy.devices.models import Meter
from legacy.devices.models import PhysicalInput
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils.utilitytypes import OPTIONAL_METER_CHOICES

from .views import ElectricityConsumptionCreateView
from .views import GasConsumptionCreateView
from .views import OilConsumptionCreateView
from .views import DistrictHeatingConsumptionCreateView
from .views import ProductionCreateView
from .views import WaterConsumptionCreateView


@override_settings(ENCRYPTION_TESTMODE=True)
class ElectricityConsumptionCreateViewTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.datasource = CustomerDataSource.objects.create(
            customer=self.customer)
        self.factory = RequestFactory()
        self.view = ElectricityConsumptionCreateView.as_view()

    def test_forms_valid_creates_adapter(self):
        request = self.factory.post(
            'create/',
            {
                'name': 'SOME NAME',
                'pulseperiod_set-TOTAL_FORMS': 1,
                'pulseperiod_set-INITIAL_FORMS': 0,
                'pulseperiod_set-MAX_NUM_FORMS': 1000,
                'pulseperiod_set-0-period_ptr': '',
                'pulseperiod_set-0-datasequence': '',
                'pulseperiod_set-0-from_timestamp': '2014-08-01 00:00',
                'pulseperiod_set-0-to_timestamp': '31.12.9998 00:00:00',
                'pulseperiod_set-0-pulse_quantity': 1,
                'pulseperiod_set-0-output_quantity': 2,
                'pulseperiod_set-0-output_unit': 'milliwatt*hour',
            }
        )
        request.user = User()
        request.user.is_superuser = True
        with replace_customer(self.customer):
            response = self.view(
                request, physicalinput=self.datasource.id, meter=1234)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            ConsumptionAccumulationAdapter.objects.filter(
                datasequence__period__pulseperiod__datasource=self.datasource,
                role=DataRoleField.CONSUMPTION,
                utility_type=OPTIONAL_METER_CHOICES.electricity)
            .exists())


@override_settings(ENCRYPTION_TESTMODE=True)
class GasConsumptionCreateViewTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.datasource = CustomerDataSource.objects.create(
            customer=self.customer)
        self.factory = RequestFactory()
        self.view = GasConsumptionCreateView.as_view()

    def test_forms_valid_creates_adapter(self):
        request = self.factory.post(
            'create/',
            {
                'name': 'SOME NAME',
                'pulseperiod_set-TOTAL_FORMS': 1,
                'pulseperiod_set-INITIAL_FORMS': 0,
                'pulseperiod_set-MAX_NUM_FORMS': 1000,
                'pulseperiod_set-0-period_ptr': '',
                'pulseperiod_set-0-datasequence': '',
                'pulseperiod_set-0-from_timestamp': '2014-08-01 00:00',
                'pulseperiod_set-0-to_timestamp': '31.12.9998 00:00:00',
                'pulseperiod_set-0-pulse_quantity': 1,
                'pulseperiod_set-0-output_quantity': 2,
                'pulseperiod_set-0-output_unit': 'meter*meter*meter',
            }
        )
        request.user = User()
        request.user.is_superuser = True
        with replace_customer(self.customer):
            response = self.view(
                request, physicalinput=self.datasource.id, meter=1234)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            ConsumptionAccumulationAdapter.objects.filter(
                datasequence__period__pulseperiod__datasource=self.datasource,
                role=DataRoleField.CONSUMPTION,
                utility_type=OPTIONAL_METER_CHOICES.gas)
            .exists())


@override_settings(ENCRYPTION_TESTMODE=True)
class OilConsumptionCreateViewTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.datasource = CustomerDataSource.objects.create(
            customer=self.customer)
        self.factory = RequestFactory()
        self.view = OilConsumptionCreateView.as_view()

    def test_forms_valid_creates_adapter(self):
        request = self.factory.post(
            'create/',
            {
                'name': 'SOME NAME',
                'pulseperiod_set-TOTAL_FORMS': 1,
                'pulseperiod_set-INITIAL_FORMS': 0,
                'pulseperiod_set-MAX_NUM_FORMS': 1000,
                'pulseperiod_set-0-period_ptr': '',
                'pulseperiod_set-0-datasequence': '',
                'pulseperiod_set-0-from_timestamp': '2014-08-01 00:00',
                'pulseperiod_set-0-to_timestamp': '31.12.9998 00:00:00',
                'pulseperiod_set-0-pulse_quantity': 1,
                'pulseperiod_set-0-output_quantity': 2,
                'pulseperiod_set-0-output_unit': 'meter*meter*meter',
            }
        )
        request.user = User()
        request.user.is_superuser = True
        with replace_customer(self.customer):
            response = self.view(
                request, physicalinput=self.datasource.id, meter=1234)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            ConsumptionAccumulationAdapter.objects.filter(
                datasequence__period__pulseperiod__datasource=self.datasource,
                role=DataRoleField.CONSUMPTION,
                utility_type=OPTIONAL_METER_CHOICES.oil)
            .exists())


@override_settings(ENCRYPTION_TESTMODE=True)
class DistrictHeatingConsumptionCreateViewTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.datasource = CustomerDataSource.objects.create(
            customer=self.customer)
        self.factory = RequestFactory()
        self.view = DistrictHeatingConsumptionCreateView.as_view()

    def test_forms_valid_creates_adapter(self):
        request = self.factory.post(
            'create/',
            {
                'name': 'SOME NAME',
                'pulseperiod_set-TOTAL_FORMS': 1,
                'pulseperiod_set-INITIAL_FORMS': 0,
                'pulseperiod_set-MAX_NUM_FORMS': 1000,
                'pulseperiod_set-0-period_ptr': '',
                'pulseperiod_set-0-datasequence': '',
                'pulseperiod_set-0-from_timestamp': '2014-08-01 00:00',
                'pulseperiod_set-0-to_timestamp': '31.12.9998 00:00:00',
                'pulseperiod_set-0-pulse_quantity': 1,
                'pulseperiod_set-0-output_quantity': 2,
                'pulseperiod_set-0-output_unit': 'milliwatt*hour',
            }
        )
        request.user = User()
        request.user.is_superuser = True
        with replace_customer(self.customer):
            response = self.view(
                request, physicalinput=self.datasource.id, meter=1234)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            ConsumptionAccumulationAdapter.objects.filter(
                datasequence__period__pulseperiod__datasource=self.datasource,
                role=DataRoleField.CONSUMPTION,
                utility_type=OPTIONAL_METER_CHOICES.district_heating)
            .exists())


@override_settings(ENCRYPTION_TESTMODE=True)
class WaterConsumptionCreateViewTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.datasource = CustomerDataSource.objects.create(
            customer=self.customer)
        self.factory = RequestFactory()
        self.view = WaterConsumptionCreateView.as_view()

    def test_forms_valid_creates_adapter(self):
        request = self.factory.post(
            'create/',
            {
                'name': 'SOME NAME',
                'pulseperiod_set-TOTAL_FORMS': 1,
                'pulseperiod_set-INITIAL_FORMS': 0,
                'pulseperiod_set-MAX_NUM_FORMS': 1000,
                'pulseperiod_set-0-period_ptr': '',
                'pulseperiod_set-0-datasequence': '',
                'pulseperiod_set-0-from_timestamp': '2014-08-01 00:00',
                'pulseperiod_set-0-to_timestamp': '31.12.9998 00:00:00',
                'pulseperiod_set-0-pulse_quantity': 1,
                'pulseperiod_set-0-output_quantity': 2,
                'pulseperiod_set-0-output_unit': 'meter*meter*meter',
            }
        )
        request.user = User()
        request.user.is_superuser = True
        with replace_customer(self.customer):
            response = self.view(
                request, physicalinput=self.datasource.id, meter=1234)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            ConsumptionAccumulationAdapter.objects.filter(
                datasequence__period__pulseperiod__datasource=self.datasource,
                role=DataRoleField.CONSUMPTION,
                utility_type=OPTIONAL_METER_CHOICES.water)
            .exists())


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionCreateViewTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            production_a_unit_plain='Pøp Cörn')
        self.datasource = CustomerDataSource.objects.create(
            customer=self.customer)
        self.factory = RequestFactory()
        self.view = ProductionCreateView.as_view()

    def test_forms_valid_creates_adapter(self):
        request = self.factory.post(
            'create/',
            {
                'name': 'SOME NAME',
                'pulseperiod_set-TOTAL_FORMS': 1,
                'pulseperiod_set-INITIAL_FORMS': 0,
                'pulseperiod_set-MAX_NUM_FORMS': 1000,
                'pulseperiod_set-0-period_ptr': '',
                'pulseperiod_set-0-datasequence': '',
                'pulseperiod_set-0-from_timestamp': '2014-08-01 00:00',
                'pulseperiod_set-0-to_timestamp': '31.12.9998 00:00:00',
                'pulseperiod_set-0-pulse_quantity': 1,
                'pulseperiod_set-0-output_quantity': 2,
                'pulseperiod_set-0-output_unit': 'production_a',
            }
        )
        request.user = User()
        request.user.is_superuser = True
        with replace_customer(self.customer):
            response = self.view(
                request, physicalinput=self.datasource.id, meter=1234,
                production_unit='production_a')
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            ProductionAccumulationAdapter.objects.filter(
                datasequence__period__pulseperiod__datasource=self.datasource,
                role=DataRoleField.PRODUCTION,
                utility_type=OPTIONAL_METER_CHOICES.unknown)
            .exists())


@override_settings(ENCRYPTION_TESTMODE=True)
class ManageUserTest(TestCase):
    """
    Test that admin user can view and edit customers devices
    """

    fixtures = ["display_measurementpoints_test.json"]

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer(name_plain='Test customer')
        self.customer.save()
        trackuser._set_customer(self.customer)
        assert self.customer is trackuser.get_customer()

        self.client.post('/login/', {'username': 'root',
                                     'password': 'feet'})

        self.location = Location.objects.create(
            customer=self.customer,
            name_plain='Test location')

        self.agent = Agent.objects.create(
            customer=self.customer,
            location=self.location,
            mac='AB:CD:DE:F0:12:34')

        self.meter = Meter.objects.create(
            agent=self.agent,
            location=self.location,
            manufactoring_id='1234567891234',
            connection_type=Meter.GRIDPOINT,
            manual_mode=False,
            relay_on=False,
            relay_enabled=True,
            online=True,
            customer=self.customer,
            name_plain='Test meter')

    def tearDown(self):
        trackuser._set_customer(None)

    def test_admin_meter_list(self):
        """
        Test that admin can view meters for a customer
        """
        response = self.client.get(reverse('manage_customers-list-json'))
        self.assertContains(response, self.customer.name_plain)

        response = self.client.get(
            reverse('manage_customers-meter-list-json',
                    kwargs={'customer': self.customer.id}))
        self.assertContains(response, self.meter.name_plain)

    def test_unauthorized_cannot_edit_meter(self):
        """
        Test that super user for another customer cannot view or edit the meter
        """
        self.client.post('/login/', {'username': 'super',
                                     'password': '123'})

        response = self.client.get(reverse('manage_customers-list-json'))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            reverse('manage_customers-meter-list-json',
                    kwargs={'customer': self.customer.id}))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse('manage_devices-meter-update',
                                           kwargs={'pk': self.meter.id}))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            reverse('manage_devices-meter-update',
                    kwargs={'pk': self.meter.id}),
            {
                'name': 'New name',
                'location': self.location.id,
            })
        self.assertEqual(response.status_code, 404)

    def test_admin_agent_list(self):
        """
        Test that admin can view agents for a customer
        """
        response = self.client.get(reverse('manage_customers-list-json'))
        self.assertContains(response, self.customer.name_plain)

        response = self.client.get(
            reverse('manage_customers-agent-list-json',
                    kwargs={'customer': self.customer.id}))
        self.assertContains(response, self.agent.mac)

    def test_admin_agent_edit(self):
        """
        Test that admin can view and edit an agent for a customer
        """
        response = self.client.get(
            reverse('manage_devices-agent-form', kwargs={'pk': self.agent.id}))
        self.assertContains(response, self.agent.mac)

        response = self.client.post(
            reverse('manage_devices-agent-update',
                    kwargs={'pk': self.agent.id}),
            {
                'location': '',
            })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('errorlist', response.content)

    def test_unauthorized_cannot_edit_agent(self):
        """
        Test that super user for another customer cannot view or edit the agent
        """
        self.client.post('/login/', {'username': 'super',
                                     'password': '123'})

        response = self.client.get(reverse('manage_customers-list-json'))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            reverse('manage_customers-agent-list-json',
                    kwargs={'customer': self.customer.id}))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            reverse('manage_devices-agent-form', kwargs={'pk': self.agent.id}))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            reverse('manage_devices-agent-update',
                    kwargs={'pk': self.agent.id}),
            {
                'location': self.location.id,
            })
        self.assertEqual(response.status_code, 404)


@override_settings(ENCRYPTION_TESTMODE=True)
class MeterTest(TestCase):
    def setUp(self):
        self.username = 'root'
        self.password = 'feeet'
        self.user = User.objects.create_user(
            self.username, self.password,
            user_type=User.ADMIN)
        self.user.is_staff = True
        self.user.name_plain = "Test User {}".format(self.username)
        self.user.e_mail_plain = '{}@gridmanager.dk'.format(self.username)
        self.user.save()
        self.client.post(
            '/login/',
            {'username': self.username, 'password': self.password})
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.agent = Agent.objects.create(
            mac='AB:CD:DE:F0:12:34',
            customer=self.customer)
        self.meter = Meter.objects.create(
            customer=self.customer,
            agent=self.agent,
            manufactoring_id='1234567891234',
            connection_type=Meter.GRIDPOINT,
            manual_mode=False,
            relay_on=False,
            relay_enabled=True,
            online=True,
            name_plain='Test meter')
        self.pulseinput = PhysicalInput.objects.create(
            customer=self.customer,
            unit='impulse',
            type=PhysicalInput.UNKNOWN_ORIGIN,
            meter=self.meter,
            order=0,
            name_plain='')
        self.elinput = PhysicalInput.objects.create(
            customer=self.customer,
            unit='milliwatt*hour',
            type=PhysicalInput.ELECTRICITY,
            meter=self.meter,
            order=1,
            name_plain='')

    def test_meter_update(self):
        update_url = reverse(
            'manage_devices-meter-update',
            kwargs={'pk': self.meter.id})

        response = self.client.get(update_url)
        self.assertContains(response, b'Test meter')
        self.assertNotContains(response, 'XYZXYZXYZ')

        response = self.client.post(
            update_url, {
                'item_id': self.meter.id,
                'name': 'new name',
                'location': '',
                'relay_enabled': 'on'
            })
        self.assertEqual(response.status_code, 302)

        response = self.client.get(update_url)
        self.assertNotContains(response, b'Test meter')
        self.assertContains(response, b'new name')
