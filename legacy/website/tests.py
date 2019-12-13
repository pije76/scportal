# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Tests for the C{website} django app.
"""

import os
import time
import pytz

from pyvirtualdisplay import Display


from django.test import LiveServerTestCase
from django.test.utils import override_settings
from django.utils.unittest import skipIf
from django.conf import settings


from gridplatform.utils.tests import CustomWebDriver
from django.core.management import call_command

from gridplatform.encryption.shell import Request
from gridplatform.encryption.base import EncryptionContext
from gridplatform.customers.models import Customer
from legacy.measurementpoints.models import Location
from legacy.devices.models import Agent
from legacy.devices.models import Meter
from legacy.devices.models import PhysicalInput
from gridplatform.users.models import User
from gridplatform import trackuser
from gridplatform.encryption import _store as encryption_store
from gridplatform.trackuser import _store as trackuser_store
from gridplatform.providers.models import Provider

from legacy.manage_users.views import UserForm
from legacy.manage_users.views import UserProfileForm
from legacy.manage_users.views import create_user


def setup():
    Provider.objects.create()

    # Setup root user and request
    call_command('create_encrypted_user', 'root', 'feet', 'admin')
    request = Request('root', 'feet')

    encryption_store.encryption_context = EncryptionContext()
    trackuser_store.user = request.user

    # Setup customer
    customer = Customer(
        name_plain='test customer',
        vat_plain='4242',
        address_plain='address',
        postal_code_plain='1234',
        city_plain='city',
        phone_plain='12341234',
        country_code_plain='dnk',
        timezone=pytz.timezone('Europe/Copenhagen'),
        contact_name_plain='',
        contact_email_plain='',
        contact_phone_plain='')
    customer.save()

    trackuser._store.customer = customer
    assert customer is trackuser.get_customer()

    # setup customer super user
    username = 'super@gridmanager.dk'
    user_form = UserForm({
        'e_mail': username,
        'phone': '33334433',
        'mobile': '34343333',
        'name': 'Super User',
        'user_type': str(User.CUSTOMER_SUPERUSER),
    })

    user_profile = UserProfileForm({
        'collections': ''
    })

    user_form.is_valid()
    user_profile.is_valid()
    user, password = create_user(request, customer, user_form, user_profile)

    # Location
    location = Location.objects.create(
        customer=customer, name_plain="Test Location")

    # Agent
    agent = Agent.objects.create(
        customer=customer, location=location, mac='08:00:27:03:fe:c7',
        device_type=1, hw_major=5, hw_minor=0, hw_revision=0,
        sw_major=2, sw_minor=2, sw_revision=1, sw_subrevision='fixture',
        online=True)

    # Meters
    def create_meter(agent, manufactoring_id, connection_type, name, request):
        customer = agent.customer
        location = agent.location
        meter = Meter(
            customer=customer,
            agent=agent,
            manufactoring_id=manufactoring_id,
            connection_type=connection_type,
            location=location,
            name_plain=name,
            relay_enabled=True,
            online=True)
        meter.save()
        return meter

    create_meter(
        agent, 155173425101, Meter.GRIDLINK,
        'Kamstrup meter', request)
    mbus_meter = create_meter(
        agent, 1980720117449728, Meter.GRIDLINK,
        'Mbus meter', request)
    meter = create_meter(
        agent, 456789, Meter.GRIDLINK,
        'ZigBee elec. test meter', request)
    gas = create_meter(
        agent, 456790, Meter.GRIDLINK,
        'ZigBee gas meter', request)
    heat = create_meter(
        agent, 456791, Meter.GRIDLINK,
        'ZigBee heat meter', request)
    water = create_meter(
        agent, 456792, Meter.GRIDLINK,
        'ZigBee water meter', request)
    oil = create_meter(
        agent, 456794, Meter.GRIDLINK,
        'ZigBee oil meter', request)
    gridlink = create_meter(
        agent, 456793, Meter.GRIDLINK,
        'GridLink', request)

    # Physical inputs
    PhysicalInput.objects.create(
        customer=customer,
        unit='milliwatt*hour', type=1,
        meter=mbus_meter, order=0,
        name_plain='M-Bus consumption')

    PhysicalInput.objects.create(
        customer=customer,
        unit='milliwatt', type=1,
        meter=mbus_meter, order=0, name_plain='M-Bus power')

    PhysicalInput.objects.create(
        customer=customer,
        unit='impulse',
        type=PhysicalInput.UNKNOWN_ORIGIN,
        meter=meter, order=2,
        name_plain='Pulse meter')

    gas = PhysicalInput.objects.create(
        customer=customer,
        unit='milliliter',
        type=PhysicalInput.UNKNOWN_ORIGIN, meter=gas, order=0,
        name_plain="Gas consumption")

    heat = PhysicalInput.objects.create(
        customer=customer,
        unit='milliwatt*hour',
        type=PhysicalInput.DISTRICT_HEATING, meter=heat, order=0,
        name_plain="Heat consumption")

    water = PhysicalInput.objects.create(
        customer=customer,
        unit='milliliter',
        type=PhysicalInput.WATER, meter=water,
        order=0, name_plain="Water consumption")

    oil = PhysicalInput.objects.create(
        customer=customer,
        unit='milliliter',
        type=PhysicalInput.OIL, meter=oil,
        order=1, name_plain="Oil consumption")

    PhysicalInput.objects.create(
        customer=customer,
        unit='impulse',
        type=PhysicalInput.UNKNOWN_ORIGIN, meter=gridlink,
        order=0, name_plain="GridLink input 1")
    PhysicalInput.objects.create(
        customer=customer,
        unit='impulse',
        type=PhysicalInput.UNKNOWN_ORIGIN, meter=gridlink,
        order=1, name_plain="GridLink input 2")
    PhysicalInput.objects.create(
        customer=customer,
        unit='impulse',
        type=PhysicalInput.UNKNOWN_ORIGIN, meter=gridlink,
        order=2, name_plain="GridLink input 3")

    return username, password, customer


@override_settings(
    DEBUG=True,
    MIDDLEWARE_CLASSES=[
        x for x in settings.MIDDLEWARE_CLASSES
        if x != "debug_toolbar.middleware.DebugToolbarMiddleware"],
    INSTALLED_APPS=[
        x for x in settings.INSTALLED_APPS if x != "debug_toolbar"])
class SeleniumLiveServerTestCase(LiveServerTestCase):
    def setUp(self, *args, **kwargs):
        super(SeleniumLiveServerTestCase, self).setUp(*args, **kwargs)
        self.username, self.password, self.customer = setup()

    def tearDown(self):
        encryption_store.encryption_context = None
        trackuser_store.user = None
        trackuser._store.customer = None


# DB DUMP:
# ./manage.py dumpdata --format=json --indent=2 --natural rules.rule
# customers.customer customers.location auth.user users.user
# customers.userprofile encryption.encryptionkey >
# gridplatform/website/fixtures/website_rule_test.json


@skipIf(os.environ.get('SELENIUM_SERVER') != "TRUE", 'Selenium test')
class WebsiteUITest(SeleniumLiveServerTestCase):

    def setUp(self):
        super(WebsiteUITest, self).setUp()
        self.display = Display(visible=0, size=(1024, 768))
        self.display.start()
        self.driver = CustomWebDriver()
        self.driver.implicitly_wait(30)
        self.base_url = self.live_server_url
        self.verificationErrors = []

    def test_login(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.assertTrue(self.driver.find_css('#dashboard'))

    def tearDown(self):
        super(WebsiteUITest, self).tearDown()
        self.driver.logout()
        self.driver.quit()
        self.display.stop()
        self.assertEqual([], self.verificationErrors)


@skipIf(os.environ.get('SELENIUM_SERVER') != "TRUE", 'Selenium test')
class WebsiteMenuUITest(SeleniumLiveServerTestCase):
    def setUp(self):
        super(WebsiteMenuUITest, self).setUp()

        self.display = Display(visible=0, size=(1024, 768))
        self.display.start()
        self.driver = CustomWebDriver()
        self.driver.implicitly_wait(5)
        self.base_url = self.live_server_url
        self.verificationErrors = []

    def test_details(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css("div.menu-item.mp a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#mp-page #measurementpoints'))

    def test_indexes(self):
        self.driver.set_page_load_timeout(10)
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css("div.menu-item.indexes a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#indexes-page #indexes'))

    def test_reports(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css("div.menu-item.reports a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#reports-page'))

    def test_projects(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css("div.menu-item.projects a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#projects-page'))

    def test_detail_settings(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css(".settings-btn").click()
        # wait for settings menu to move down
        time.sleep(1)
        self.driver.find_css("div.menu-item.mps a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#mps-page'))

    def test_groups(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css(".settings-btn").click()
        # wait for settings menu to move down
        time.sleep(1)
        self.driver.find_css("div.menu-item.groups a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#groups-page'))

    def test_rules(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css(".settings-btn").click()
        # wait for settings menu to move down
        time.sleep(1)
        self.driver.find_css("div.menu-item.rules a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#rules-page'))

    def test_index_settings(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css(".settings-btn").click()
        # wait for settings menu to move down
        time.sleep(1)
        self.driver.find_css("div.menu-item.indexsettings a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#indexsettings-page'))

    def test_devices(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css(".settings-btn").click()
        # wait for settings menu to move down
        time.sleep(1)
        self.driver.find_css("div.menu-item.devices a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#devices-page'))

    def test_locations(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css(".settings-btn").click()
        # wait for settings menu to move down
        time.sleep(1)
        self.driver.find_css("div.menu-item.locations a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#locations-page'))

    def test_users(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css(".settings-btn").click()
        # wait for settings menu to move down
        time.sleep(1)
        self.driver.find_css("div.menu-item.users a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#users-page'))

    def test_userprofile(self):
        self.driver.login(
            self.base_url, self.username, self.password)
        self.driver.find_css(".settings-btn").click()
        # wait for settings menu to move down
        time.sleep(1)
        self.driver.find_css("div.menu-item.userprofile a span").click()
        self.assertNotIn('XYZXYZXYZ', self.driver.page_source)
        self.assertTrue(self.driver.find_css('#userprofile-page'))

    def tearDown(self):
        super(WebsiteMenuUITest, self).tearDown()
        self.driver.logout()
        self.driver.quit()
        self.display.stop()
        self.assertEqual([], self.verificationErrors)
