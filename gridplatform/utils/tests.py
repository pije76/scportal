# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from fractions import Fraction
import datetime
import itertools

from django.db import models
from django.forms import ModelForm
from django.test import TestCase
from django.test import SimpleTestCase
from django.utils import translation
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.test.utils import override_settings

from mock import patch
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
import pytz
from extra_views import InlineFormSet

from gridplatform.customers.models import Customer
from gridplatform.providers.models import Provider
from gridplatform.trackuser import replace_customer
from gridplatform.users.models import User
from gridplatform.consumptions.models import Consumption
from gridplatform.consumptions.models import SingleValuePeriod

from . import condense
from . import fields
from . import first_last
from . import generic_views
from . import utilitytypes
from . import sum_or_none
from .breadcrumbs import Breadcrumb
from .breadcrumbs import Breadcrumbs
from .decorators import virtual
from .format_id import format_mbus_enhanced
from .iter_ext import count_extended
from .iter_ext import pairwise
from .iter_ext import pairwise_extended
from .iter_ext import nwise
from .iter_ext import tee_lookahead
from .models import StoreSubclass
from .models import DateRangeModelMixin
from .models import TimestampRangeModelMixin
from .managers import DateRangeManagerMixin
from .managers import TimestampRangeManagerMixin
from .preferredunits import AbsoluteCelsiusUnitConverter
from .preferredunits import AbsoluteFahrenheitUnitConverter
from .preferredunits import AreaENPIUnitConverter
from .preferredunits import PersonsENPIUnitConverter
from .preferredunits import PhysicalUnitConverter
from .preferredunits import ProductionAENPIUnitConverter
from .preferredunits import ProductionBENPIUnitConverter
from .preferredunits import ProductionCENPIUnitConverter
from .preferredunits import ProductionDENPIUnitConverter
from .preferredunits import ProductionEENPIUnitConverter
from .preferredunits import RelativeCelsiusUnitConverter
from .preferredunits import RelativeFahrenheitUnitConverter
from .relativetimedelta import RelativeTimeDelta
from .unitconversion import IncompatibleUnitsError
from .unitconversion import NotPhysicalQuantityError
from .unitconversion import PhysicalQuantity
from .unitconversion import UnitParseError
from .units import preferred_unit_bases
from .views import HomeViewBase
from .views import CustomerViewBase
from .forms import TimePeriodModelForm
from .forms import HalfOpenTimePeriodModelForm
from .forms import previous_month_initial_values
from .api import next_valid_date_for_datasequence
from .api import previous_valid_date_for_datasequence
from .forms import YearWeekPeriodForm
from .forms import this_week_initial_values


class GenericViewTestCaseMixin(object):
    view_class = None

    def setUp(self):
        super(GenericViewTestCaseMixin, self).setUp()
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(name_plain='test customer')
        self.factory = RequestFactory()

    def get_view_kwargs(self):
        return {}

    def test_get(self):
        request = self.factory.get('/')
        request.user = User(name_plain='test user', is_superuser=True)
        view = self.view_class.as_view()
        response = view(request, **self.get_view_kwargs())
        self.assertNotContains(response, 'XYZXYZXYZ')


def _fields_test_object_hook(json_object):
    """
    JSON object_hook for converting named members to concrete Python
    objects.  This particular hook is only used for testing purposes.
    """
    if "time" in json_object:
        h, m, s = json_object["time"].split(":")
        json_object["time"] = datetime.time(hour=int(h),
                                            minute=int(m),
                                            second=int(s))
    return json_object


class CustomWebDriver(webdriver.Chrome):
    """Our own WebDriver with some helpers added"""

    def __init__(self, *args, **kwargs):
        return super(CustomWebDriver, self).__init__(*args, **kwargs)

    def find_css(self, css_selector, raise_exception=True):
        """
        Shortcut to find elements by CSS. Returns either a list or singleton
        """
        elems = self.find_elements_by_css_selector(css_selector)
        found = len(elems)
        if found == 1:
            return elems[0]
        elif not elems and raise_exception:
            raise NoSuchElementException(css_selector)
        return elems

    def wait_for_css(self, css_selector, timeout=7):
        """ Shortcut for WebDriverWait"""
        return WebDriverWait(self, timeout).until(
            lambda driver: driver.find_css(css_selector))

    def login(self, url, user, password):
        """
        Requires that a user exists, and the driver has been started
        """
        self.get(url)
        self.find_css("#id_username").clear()
        self.find_css("#id_username").send_keys(user)
        self.find_css("#id_password").clear()
        self.find_css("#id_password").send_keys(password)
        self.find_css("input[type=\"submit\"]").click()

    def logout(self):
        self.find_css(".logout a", raise_exception=False).click()


class FieldsTestModel(models.Model):
    """
    Models must be defined in the models.py, otherwise they just
    aren't processed right when running unittests.
    """
    field = fields.JSONField(object_hook=_fields_test_object_hook)


class JSONFieldTest(TestCase):
    def test_basic_serialization(self):
        """
        Tests JSON serialization of various Python objects
        """
        unit = FieldsTestModel()
        unit.field = {"foo": "bar", "baz": ["inktvis", 42, None, True, False]}
        unit.save()
        restored_unit = FieldsTestModel.objects.get(id=unit.id)
        self.assertEqual(unit.field, restored_unit.field)

        unit.field = ""
        unit.save()
        restored_unit = FieldsTestModel.objects.get(id=unit.id)
        self.assertEqual(unit.field, restored_unit.field)

        unit.field = None
        unit.save()
        restored_unit = FieldsTestModel.objects.get(id=unit.id)
        self.assertEqual(unit.field, restored_unit.field)

    def test_object_hook(self):
        """
        Test JSON serialization using object_hook
        """

        unit = FieldsTestModel()
        unit.field = {"foo": "bar", "time": datetime.time(hour=4, minute=42)}
        unit.save()
        restored_unit = FieldsTestModel.objects.get(id=unit.id)
        self.assertEqual(unit.field, restored_unit.field)


class RelativeTimeDeltaTest(TestCase):
    """
    Test RelativeTimeDelta
    """
    def setUp(self):
        self.timezone = pytz.timezone("Europe/Copenhagen")
        self.to_summer_start = self.timezone.localize(
            datetime.datetime(2013, 3, 31, 0, 0))
        self.to_winter_start = self.timezone.localize(
            datetime.datetime(2013, 10, 27, 0, 0))

    def test_naive_date(self):
        """
        Test L{RelativeTimeDelta} on naive dates.
        """
        delta = RelativeTimeDelta(months=1)
        start_time = datetime.datetime(2013, 1, 1)
        self.assertEqual(start_time + delta, datetime.datetime(2013, 2, 1))
        self.assertEqual(start_time + 4 * delta, datetime.datetime(2013, 5, 1))

    def test_aware_date(self):
        """
        Test L{RelativeTimeDelta} on timezone and daylight savings
        aware dates.
        """
        delta = RelativeTimeDelta(months=1)
        start_time = self.timezone.localize(datetime.datetime(2013, 1, 1))
        self.assertIsInstance(start_time.tzinfo, pytz.tzinfo.BaseTzInfo)
        self.assertEqual(start_time + delta,
                         self.timezone.localize(datetime.datetime(2013, 2, 1)))
        self.assertEqual(start_time + 4 * delta,
                         self.timezone.localize(datetime.datetime(2013, 5, 1)))

    def test_dst_switch(self):
        """
        Test L{RelativeTimeDelta} wrt. DST switch.

        @note: Regression test for bug where 2013-03-31 02:00 STD was followed
        by 2013-03-31 03:00 DST, i.e. a different representation of the same
        timestamp.
        """
        hour = RelativeTimeDelta(hours=1)
        for n in range(6):
            timestamp = self.to_summer_start + n * hour
            self.assertNotEqual(timestamp, timestamp + hour)
            timestamp = self.to_winter_start + n * hour
            self.assertNotEqual(timestamp, timestamp + hour)

    def test_hour_duration_exiting_dst(self):
        hour = RelativeTimeDelta(hours=1)
        absolute_delta = datetime.timedelta(hours=1)
        for n in range(6):
            timestamp = self.to_winter_start + n * hour
            self.assertEqual(
                self.timezone.normalize(timestamp + absolute_delta),
                timestamp + hour)

    def test_hour_duration_entering_dst(self):
        hour = RelativeTimeDelta(hours=1)
        absolute_delta = datetime.timedelta(hours=1)
        for n in range(6):
            timestamp = self.to_summer_start + n * hour
            self.assertEqual(
                self.timezone.normalize(timestamp + absolute_delta),
                timestamp + hour)

    def test_minute_duration_exiting_dst(self):
        minutes = RelativeTimeDelta(minutes=5)
        absolute_delta = datetime.timedelta(minutes=5)
        for n in range(24 * 60 / 5):
            timestamp = self.to_winter_start + n * minutes
            self.assertEqual(
                self.timezone.normalize(timestamp + absolute_delta),
                timestamp + minutes)

    def test_minute_duration_entering_dst(self):
        minutes = RelativeTimeDelta(minutes=5)
        absolute_delta = datetime.timedelta(minutes=5)
        for n in range(24 * 60 / 5):
            timestamp = self.to_summer_start + n * minutes
            self.assertEqual(
                self.timezone.normalize(timestamp + absolute_delta),
                timestamp + minutes)


class CondenseTest(TestCase):
    def test_floor(self):
        for resolution in [
            "minutes",
            "hours",
            "days",
            "months",
            "years"
        ]:
            timestamp = datetime.datetime(
                year=2012,
                month=12,
                day=12,
                hour=12,
                minute=12,
                second=12,
                tzinfo=pytz.utc)

            relative_time_delta = RelativeTimeDelta(**{resolution: 1})
            timestamp = condense.floor(
                timestamp, relative_time_delta, pytz.utc)

            if resolution == "second":
                self.assertEqual(timestamp.microsecond, 00)
            elif resolution == "minutes":
                self.assertEqual(timestamp.microsecond, 00)
                self.assertEqual(timestamp.second, 00)
            elif resolution == "hours":
                self.assertEqual(timestamp.microsecond, 00)
                self.assertEqual(timestamp.second, 00)
                self.assertEqual(timestamp.minute, 00)
            elif resolution == "days":
                self.assertEqual(timestamp.microsecond, 00)
                self.assertEqual(timestamp.second, 00)
                self.assertEqual(timestamp.minute, 00)
                self.assertEqual(timestamp.hour, 00)
            elif resolution == "months":
                self.assertEqual(timestamp.microsecond, 00)
                self.assertEqual(timestamp.second, 00)
                self.assertEqual(timestamp.minute, 00)
                self.assertEqual(timestamp.hour, 00)
                self.assertEqual(timestamp.day, 1)
            elif resolution == "years":
                self.assertEqual(timestamp.microsecond, 00)
                self.assertEqual(timestamp.second, 00)
                self.assertEqual(timestamp.minute, 00)
                self.assertEqual(timestamp.hour, 00)
                self.assertEqual(timestamp.day, 1)
                self.assertEqual(timestamp.month, 1)

    def test_floor_ambiguous_is_dst(self):
        timezone = pytz.timezone('Europe/Copenhagen')

        timestamp = timezone.localize(
            datetime.datetime(2013, 10, 27, 2), is_dst=True)

        self.assertEqual(
            timestamp, condense.floor(timestamp, condense.HOURS, timezone))

    def test_floor_ambiguous_is_not_dst(self):
        timezone = pytz.timezone('Europe/Copenhagen')

        timestamp = timezone.localize(
            datetime.datetime(2013, 10, 27, 2), is_dst=False)

        self.assertEqual(
            timestamp, condense.floor(timestamp, condense.HOURS, timezone))

    def test_floor_exiting_dst(self):
        timezone = pytz.timezone('Europe/Copenhagen')

        timestamp = timezone.localize(datetime.datetime(2013, 6, 1))

        self.assertEqual(
            timezone.localize(datetime.datetime(2013, 1, 1)),
            condense.floor(timestamp, condense.YEARS, timezone))

    def test_floor_entering_dst(self):
        timezone = pytz.timezone('Europe/Copenhagen')

        timestamp = timezone.localize(datetime.datetime(2013, 10, 30))

        self.assertEqual(
            timezone.localize(datetime.datetime(2013, 10, 1)),
            condense.floor(timestamp, condense.MONTHS, timezone))

    def test_ceil_nontrivial(self):
        timezone = pytz.timezone('Europe/Copenhagen')

        timestamp = timezone.localize(datetime.datetime(2013, 10, 20))

        self.assertEqual(
            timezone.localize(datetime.datetime(2013, 11, 1)),
            condense.ceil(timestamp, condense.MONTHS, timezone))

    def test_ceil_identity(self):
        timezone = pytz.timezone('Europe/Copenhagen')

        timestamp = timezone.localize(datetime.datetime(2013, 10, 1))

        self.assertEqual(
            timezone.localize(datetime.datetime(2013, 10, 1)),
            condense.ceil(timestamp, condense.MONTHS, timezone))


class CondenseGetPreferredDateFormatTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')

    def test_no_resolution_within_day(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1)),
            self.timezone.localize(datetime.datetime(2013, 1, 2)))
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(datetime.datetime(2013, 1, 2)))
            mock.assertCalledWith('TIME_FORMAT')

    def test_minutes_resolution_within_day(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1)),
            self.timezone.localize(datetime.datetime(2013, 1, 2)),
            condense.MINUTES)
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(datetime.datetime(2013, 1, 2)))
            mock.assertCalledWith('TIME_FORMAT')

    def test_five_minutes_resolution_within_day(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1)),
            self.timezone.localize(datetime.datetime(2013, 1, 2)),
            condense.FIVE_MINUTES)
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(datetime.datetime(2013, 1, 2)))
            mock.assertCalledWith('TIME_FORMAT')

    def test_hour_resolution_within_day(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1)),
            self.timezone.localize(datetime.datetime(2013, 1, 2)),
            condense.HOURS)
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(datetime.datetime(2013, 1, 2)))
            mock.assertCalledWith('TIME_FORMAT')

    def test_no_resolution_within_24h(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1, 12)),
            self.timezone.localize(datetime.datetime(2013, 1, 2, 12)))
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(
                datetime.datetime(2013, 1, 1, 12)))
            mock.assertCalledWith('SHORT_DATETIME_FORMAT')

    def test_minutes_resolution_within_24h(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1, 12)),
            self.timezone.localize(datetime.datetime(2013, 1, 2, 12)),
            condense.MINUTES)
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(
                datetime.datetime(2013, 1, 1, 12)))
            mock.assertCalledWith('SHORT_DATETIME_FORMAT')

    def test_five_minutes_resolution_within_24h(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1, 12)),
            self.timezone.localize(datetime.datetime(2013, 1, 2, 12)),
            condense.FIVE_MINUTES)
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(
                datetime.datetime(2013, 1, 1, 12)))
            mock.assertCalledWith('SHORT_DATETIME_FORMAT')

    def test_hour_resolution_within_24h(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1, 12)),
            self.timezone.localize(datetime.datetime(2013, 1, 2, 12)),
            condense.HOURS)
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(
                datetime.datetime(2013, 1, 1, 12)))
            mock.assertCalledWith('SHORT_DATETIME_FORMAT')

    def test_day_resolution(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            condense.DAYS)
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(datetime.datetime(2013, 1, 1)))
            mock.assertCalledWith('SHORT_DATETIME_FORMAT')

    def test_month_resolution(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            condense.MONTHS)
        with patch('gridplatform.utils.condense._') as mock:
            formatter(self.timezone.localize(datetime.datetime(2014, 1, 1)))
            mock.assertCalledWith('%m %Y')

    def test_quarter_resolution(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            condense.QUARTERS)
        with patch('gridplatform.utils.condense._') as mock:
            formatter(self.timezone.localize(datetime.datetime(2014, 1, 1)))
            mock.assertCalledWith('Q{quarter} %Y')

    def test_year_resolution(self):
        formatter = condense.get_date_formatter(
            self.timezone.localize(datetime.datetime(2013, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            condense.YEARS)
        with patch('django.utils.formats.date_format') as mock:
            formatter(self.timezone.localize(datetime.datetime(2013, 1, 1)))
            mock.assertCalledWith('YEAR_FORMAT')


def test_view_a(request):
    pass


def test_view_b(request):
    pass


class OuterModel(models.Model):
    name = models.CharField(max_length=16)


class InnerModel(models.Model):
    inner = models.CharField(max_length=8)


class InnerModelForm(ModelForm):
    class Meta:
        model = InnerModel


class UnitConverterBasesTest(TestCase):
    """
    The L{preferred_unit_bases} defines buckingham units suitable for storing a
    selection of other buckingham units that data needs to be converted to and
    from.
    """

    def test_integer_conversion(self):
        """
        Test that a large prime can be stored and recovered without noticable
        loss of precission for all unit and store unit combinations.
        """
        large_prime = 797
        REQUIRED_PRECISSION = 7
        for unit, store_unit in preferred_unit_bases.iteritems():
            stored_number = int(
                PhysicalQuantity(large_prime, unit).convert(store_unit))
            loaded_number = float(PhysicalQuantity(
                stored_number, store_unit).convert(unit))
            self.assertAlmostEqual(
                large_prime, loaded_number, places=REQUIRED_PRECISSION,
                msg='%.8f did not equal large_prime=%d for unit=%s and '
                'store_unit=%s within %d places' % (
                    loaded_number, large_prime, unit, store_unit,
                    REQUIRED_PRECISSION))


class FormatIdTest(TestCase):
    """
    Tests for the format_id.py module.
    """

    def test_format_mbus_enhanced(self):
        """
        Test that format_mbus_enhanced does not crash when mbus medium is
        translated to a string outside the domain of ascii.
        """
        with translation.override("da-dk"):
            format_mbus_enhanced(0xFFFFFF0A)


class TestFirstLast(TestCase):

    def test_empty_list(self):
        """
        Check that L{first_last} raises value error on empty list.
        """
        with self.assertRaises(ValueError):
            first_last([])

    def test_one_element_list(self):
        """
        Check that L{first_last} return the same first and last value for a
        list with one element.
        """
        self.assertEqual(
            (1, 1),
            first_last([1]))

    def test_empty_generator(self):
        """
        Check that L{first_last} raises value error on empty generator.
        """
        def empty_generator():
            if False:
                yield 1

        with self.assertRaises(ValueError):
            first_last(empty_generator())


class StoreBaseModel(StoreSubclass):
    basefield = models.CharField(max_length=16)

    def __repr__(self):
        return 'StoreBaseModel(basefield=%s)' % self.basefield


class StoreSubmodel(StoreBaseModel):
    subfield = models.CharField(max_length=16)

    def __unicode__(self):
        return 'STORE SUB MODEL INSTANCE'

    def __repr__(self):
        return 'StoreSubmodel(basefield=%s, subfield=%s)' % (self.basefield,
                                                             self.subfield)

    def combined_fields(self):
        return '{}+{}'.format(self.basefield, self.subfield)


class StoreProxyModel(StoreSubmodel):
    class Meta:
        proxy = True

    def __repr__(self):
        return 'StoreProxyModel(basefield=%s, subfield=%s)' % (self.basefield,
                                                               self.subfield)

    def combined_fields(self):
        return '{}-{}'.format(self.basefield, self.subfield)


class StoreSubclassTest(TestCase):
    def test_base(self):
        obj = StoreBaseModel.objects.create(basefield='hello')
        loaded = StoreBaseModel.objects.get(pk=obj.id).subclass_instance
        self.assertIsNot(obj, loaded)
        self.assertEqual(obj, loaded)
        self.assertEqual(obj.__class__, loaded.__class__)

    def test_submodel(self):
        obj = StoreSubmodel.objects.create(basefield='hello', subfield='world')
        loaded = StoreBaseModel.objects.get(pk=obj.id).subclass_instance
        self.assertIsNot(obj, loaded)
        self.assertEqual(obj, loaded)
        self.assertEqual(obj.__class__, loaded.__class__)

    def test_proxy(self):
        obj = StoreProxyModel.objects.create(
            basefield='hello', subfield='world')
        loaded = StoreBaseModel.objects.get(pk=obj.id).subclass_instance
        self.assertIsNot(obj, loaded)
        self.assertEqual(obj, loaded)
        self.assertEqual(obj.__class__, loaded.__class__)

    def test_submodel_load(self):
        obj = StoreProxyModel.objects.create(
            basefield='hello', subfield='world')
        loaded_submodel = StoreSubmodel.objects.get(pk=obj.id)
        loaded_proxy = loaded_submodel.subclass_instance
        self.assertIsNot(obj, loaded_submodel)
        self.assertIsNot(obj, loaded_proxy)
        self.assertIsNot(loaded_submodel, loaded_proxy)
        self.assertIsInstance(loaded_submodel, StoreSubmodel)
        self.assertNotIsInstance(loaded_submodel, StoreProxyModel)
        self.assertIsInstance(loaded_proxy, StoreProxyModel)
        self.assertNotEqual(loaded_submodel.combined_fields(),
                            loaded_proxy.combined_fields())

    def test_subclass_model_filter(self):
        StoreProxyModel.objects.create(
            basefield='how are you',
            subfield='gentlemen')

        StoreSubmodel.objects.create(
            basefield='I am not',
            subfield='an octopus')

        StoreBaseModel.objects.create(
            basefield='I am a free man')

        self.assertEqual(
            'how are you-gentlemen',
            StoreBaseModel.objects.get(
                subclass__model='storeproxymodel').
            subclass_instance.combined_fields())

        self.assertEqual(
            'I am not+an octopus',
            StoreBaseModel.objects.get(
                subclass__model='storesubmodel').
            subclass_instance.combined_fields())

        self.assertEqual(
            'I am a free man',
            StoreBaseModel.objects.get(
                subclass__model='storebasemodel').
            subclass_instance.basefield)

    def test_subclass_filter(self):
        base_model = StoreBaseModel.objects.create(
            basefield='I am a free man')

        submodel = StoreSubmodel.objects.create(
            basefield='I am not',
            subfield='an octopus')

        proxy_model = StoreProxyModel.objects.create(
            basefield='how are you',
            subfield='gentlemen')

        self.assertIn(base_model,
                      [m.subclass_instance for m in
                       StoreBaseModel.objects.all()])
        self.assertIn(submodel,
                      [m.subclass_instance for m in
                       StoreBaseModel.objects.all()])
        self.assertIn(proxy_model,
                      [m.subclass_instance for m in
                       StoreBaseModel.objects.all()])

        self.assertIn(base_model,
                      [m.subclass_instance for m in
                       StoreBaseModel.objects.subclass_only().all()])
        self.assertIn(submodel,
                      [m.subclass_instance for m in
                       StoreBaseModel.objects.subclass_only().all()])
        self.assertIn(proxy_model,
                      [m.subclass_instance for m in
                       StoreBaseModel.objects.subclass_only().all()])

        self.assertNotIn(base_model,
                         [m.subclass_instance for m in
                          StoreSubmodel.objects.subclass_only().all()])
        self.assertIn(submodel,
                      [m.subclass_instance for m in
                       StoreSubmodel.objects.subclass_only().all()])
        self.assertIn(proxy_model,
                      [m.subclass_instance for m in
                       StoreSubmodel.objects.subclass_only().all()])

        self.assertNotIn(base_model,
                         [m.subclass_instance for m in
                          StoreProxyModel.objects.subclass_only().all()])
        self.assertNotIn(submodel,
                         [m.subclass_instance for m in
                          StoreProxyModel.objects.subclass_only().all()])
        self.assertIn(proxy_model,
                      [m.subclass_instance for m in
                       StoreProxyModel.objects.subclass_only().all()])

    def test_unicode_no_delegation(self):
        base_model = StoreBaseModel.objects.create(
            basefield='I am a free man')
        unicode(base_model)

    def test_unicode_delegation(self):
        submodel = StoreSubmodel.objects.create(
            basefield='I am not',
            subfield='an octopus')
        base_model = StoreBaseModel.objects.get(id=submodel.id)

        self.assertEqual(
            unicode(base_model),
            'STORE SUB MODEL INSTANCE')

    def test_repr(self):
        repr(StoreBaseModel)


class IterTest(TestCase):
    def test_pairwise(self):
        self.assertListEqual(
            list(pairwise([1, 2, 3])),
            [(1, 2), (2, 3)])

    def test_nwise_2(self):
        self.assertListEqual(
            list(nwise([1, 2, 3], 2)),
            [(1, 2), (2, 3)])

    def test_nwise_5(self):
        self.assertListEqual(
            list(nwise([1, 2, 3, 4, 5, 6, 7], 5)),
            [(1, 2, 3, 4, 5), (2, 3, 4, 5, 6), (3, 4, 5, 6, 7)])

    def test_pairwise_extended(self):
        self.assertListEqual(
            list(pairwise_extended([1, 2, 3])),
            [(1, 2), (2, 3), (3, None)])

    def test_tee_lookahead(self):
        def gen():
            acc = 0
            while True:
                yield acc
                acc += 1
        it, = itertools.tee(gen(), 1)
        self.assertEqual(next(it), 0)
        self.assertEqual(tee_lookahead(it, 2), 3)
        self.assertEqual(next(it), 1)

    def test_count_extended(self):
        it = count_extended(datetime.date(2000, 1, 1),
                            datetime.timedelta(days=1))
        self.assertListEqual(
            list(itertools.islice(it, 5)),
            [datetime.date(2000, 1, 1),
             datetime.date(2000, 1, 2),
             datetime.date(2000, 1, 3),
             datetime.date(2000, 1, 4),
             datetime.date(2000, 1, 5)])


class UnitConverterBaseTest(object):
    def test_extract_value(self):
        raise NotImplementedError(
            'This method is not implemented by %r' % self.__class__)

    def test_display(self):
        self.assertTrue(unicode(self.preferred_unit.get_display_unit()))


class PhysicalUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        self.preferred_unit = PhysicalUnitConverter('kilowatt*hour')

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(1000000, 'milliwatt*hour')),
            1)


class RelativeCelsiusUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        self.preferred_unit = RelativeCelsiusUnitConverter()

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(100, 'kelvin')),
            100)


class AbsoluteCelsiusUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        self.preferred_unit = AbsoluteCelsiusUnitConverter()

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity('273.15', 'kelvin')),
            0)


class RelativeFahrenheitUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        self.preferred_unit = RelativeFahrenheitUnitConverter()

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(72, 'rankine')),
            72)


class AbsoluteFahrenheitUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        self.preferred_unit = AbsoluteFahrenheitUnitConverter()

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity('459.67', 'rankine')),
            0)


class PersonsENPIUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        self.preferred_unit = PersonsENPIUnitConverter('kilowatt*hour')

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(100, 365), 'kilowatt*hour*person^-1*day^-1')),
            100)


class AreaENPIUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        self.preferred_unit = AreaENPIUnitConverter('kilowatt*hour')

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(
                    Fraction(100, 365), 'kilowatt*hour*meter^-2*day^-1')),
            100)


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionAENPIUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        with replace_customer(customer):
            self.preferred_unit = ProductionAENPIUnitConverter('kilowatt*hour')

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(
                    42000, 'watt*hour*production_a^-1')),
            42)


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionBENPIUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        with replace_customer(customer):
            self.preferred_unit = ProductionBENPIUnitConverter('kilowatt*hour')

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(
                    42000, 'watt*hour*production_b^-1')),
            42)


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionCENPIUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        with replace_customer(customer):
            self.preferred_unit = ProductionCENPIUnitConverter(
                'meter*meter*meter')

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(
                    42000, 'liter*production_c^-1')),
            42)


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionDENPIUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        with replace_customer(customer):
            self.preferred_unit = ProductionDENPIUnitConverter('kilowatt*hour')

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(
                    42000, 'watt*hour*production_d^-1')),
            42)


@override_settings(ENCRYPTION_TESTMODE=True)
class ProductionEENPIUnitConverterTest(UnitConverterBaseTest, TestCase):
    def setUp(self):
        Provider.objects.create()
        customer = Customer()
        customer.save()
        with replace_customer(customer):
            self.preferred_unit = ProductionEENPIUnitConverter('kilowatt*hour')

    def test_extract_value(self):
        self.assertEqual(
            self.preferred_unit.extract_value(
                PhysicalQuantity(
                    42000, 'watt*hour*production_e^-1')),
            42)


class PermissionModel(models.Model):
    somefield = models.CharField(max_length=50)


class PermissionRelatedModel(models.Model):
    base = models.ForeignKey(PermissionModel)
    otherfield = models.CharField(max_length=20)


class PermissionRelatedModelInline(InlineFormSet):
    model = PermissionRelatedModel


class GenericViewPermissionTest(TestCase):
    def test_createview(self):
        class MyView(generic_views.CreateView):
            model = PermissionModel
        unit = MyView()
        self.assertEqual(
            unit.permission_required, 'utils.add_permissionmodel')

    def test_deleteview(self):
        class MyView(generic_views.DeleteView):
            model = PermissionModel
        unit = MyView()
        self.assertEqual(
            unit.permission_required, 'utils.delete_permissionmodel')

    def test_updateview(self):
        class MyView(generic_views.UpdateView):
            model = PermissionModel
        unit = MyView()
        self.assertEqual(
            unit.permission_required, 'utils.change_permissionmodel')

    def test_modelformsetview(self):
        class MyView(generic_views.ModelFormSetView):
            model = PermissionModel
        unit = MyView()
        self.assertEqual(
            unit.permissions, {
                'all': list({
                    'utils.add_permissionmodel',
                    'utils.change_permissionmodel',
                    'utils.delete_permissionmodel',
                }),
            })

    def test_inlineformsetview(self):
        class MyView(generic_views.InlineFormSetView):
            model = PermissionModel
            inline_model = PermissionRelatedModel
        unit = MyView()
        self.assertEqual(
            unit.permissions, {
                'all': list({
                    'utils.add_permissionrelatedmodel',
                    'utils.change_permissionrelatedmodel',
                    'utils.delete_permissionrelatedmodel',
                }),
            })

    def test_createwithinlines(self):
        class MyView(generic_views.CreateWithInlinesView):
            model = PermissionModel
            inlines = [PermissionRelatedModelInline]
        unit = MyView()
        self.assertEqual(
            unit.permissions, {
                'all': list({
                    'utils.add_permissionmodel',
                    'utils.add_permissionrelatedmodel',
                }),
            })

    def test_updatewithinlines(self):
        class MyView(generic_views.UpdateWithInlinesView):
            model = PermissionModel
            inlines = [PermissionRelatedModelInline]
        unit = MyView()
        self.assertEqual(
            set(unit.permissions['all']),
            {
                'utils.add_permissionmodel',
                'utils.change_permissionmodel',
                'utils.delete_permissionmodel',
                'utils.add_permissionrelatedmodel',
                'utils.change_permissionrelatedmodel',
                'utils.delete_permissionrelatedmodel',
            })


class UnitConversionTest(SimpleTestCase):
    def test_construction(self):
        self.assertNotEqual(
            PhysicalQuantity(10, 'meter*second^-1'),
            PhysicalQuantity(10, 'meter/second^2'))
        self.assertEqual(
            PhysicalQuantity(2, 'decimeter^3'),
            PhysicalQuantity(2, 'liter'))
        self.assertEqual(
            PhysicalQuantity('10', 'meter'),
            PhysicalQuantity('10.0', 'meter'))
        self.assertEqual(
            PhysicalQuantity('0.5', 'meter'),
            PhysicalQuantity('1/2', 'meter'))

    def test_construction_error(self):
        with self.assertRaises(UnitParseError):
            PhysicalQuantity(10, 'meter/second/liter')
        with self.assertRaises(UnitParseError):
            PhysicalQuantity(10, 'meter/second*liter')

    def test_add(self):
        a = PhysicalQuantity(2, 'volt')
        b = PhysicalQuantity(3, 'volt')
        self.assertEqual(
            a + b,
            PhysicalQuantity(5, 'volt'))
        self.assertEqual(
            (a + b),
            (b + a))
        with self.assertRaises(NotPhysicalQuantityError):
            a + 5
        with self.assertRaises(NotPhysicalQuantityError):
            PhysicalQuantity(2) + 5

    def test_sub(self):
        a = PhysicalQuantity(2, 'volt')
        b = PhysicalQuantity(3, 'volt')
        self.assertEqual(
            a - b,
            PhysicalQuantity(-1, 'volt'))
        self.assertEqual(
            b - a,
            PhysicalQuantity(1, 'volt'))

    def test_mul(self):
        self.assertEqual(
            PhysicalQuantity(2, 'meter') * 2,
            PhysicalQuantity(4, 'meter'))
        self.assertEqual(
            PhysicalQuantity(4, 'gram') * PhysicalQuantity(7, 'gram'),
            PhysicalQuantity(28, 'gram^2'))
        self.assertEqual(
            3 * PhysicalQuantity(2, 'ampere'),
            PhysicalQuantity(6, 'ampere'))

    def test_div(self):
        self.assertEqual(
            PhysicalQuantity(2) / 1,
            PhysicalQuantity(2))
        self.assertEqual(
            PhysicalQuantity(4) / PhysicalQuantity(7, 'second'),
            PhysicalQuantity('4/7', 'second^-1'))
        self.assertEqual(
            PhysicalQuantity(4, 'meter') / PhysicalQuantity(2, 'meter'),
            PhysicalQuantity(2))
        self.assertEqual(
            1 / PhysicalQuantity(2, 'ampere'),
            PhysicalQuantity('1/2', 'ampere^-1'))

    def test_pow(self):
        self.assertEqual(
            PhysicalQuantity(2, 'meter^2') ** 2,
            PhysicalQuantity(4, 'meter^4'))

    def test_lt(self):
        a = PhysicalQuantity(2, 'meter')
        b = PhysicalQuantity(1, 'kilometer')
        c = PhysicalQuantity(3, 'meter^2')
        self.assertLess(a, b)
        with self.assertRaises(IncompatibleUnitsError):
            a < c

    def test_le(self):
        a = PhysicalQuantity(1000, 'meter')
        b = PhysicalQuantity(1, 'kilometer')
        self.assertLessEqual(a, b)

    def test_gt(self):
        a = PhysicalQuantity(1002, 'meter')
        b = PhysicalQuantity(1, 'kilometer')
        self.assertGreater(a, b)

    def test_ge(self):
        a = PhysicalQuantity(1000, 'meter')
        b = PhysicalQuantity(1, 'kilometer')
        self.assertGreaterEqual(a, b)

    def test_nonzero(self):
        self.assertTrue(PhysicalQuantity(10, 'meter'))
        self.assertFalse(PhysicalQuantity(0, 'liter'))

    def test_units(self):
        self.assertEqual(
            PhysicalQuantity(10, 'meter*kilometer*centimeter').units,
            'meter^3')
        self.assertEqual(
            PhysicalQuantity(1, 'meter*liter').units,
            'meter^4')
        self.assertEqual(
            PhysicalQuantity(1, 'gram*meter*gram').units,
            'meter*gram^2')

    def test_convert(self):
        self.assertEqual(
            PhysicalQuantity(0, 'meter*second^-1').convert(
                'kilometer*hour^-1'),
            0)
        self.assertEqual(
            PhysicalQuantity(1, 'meter^3').convert('liter'),
            1000)
        self.assertIsInstance(
            PhysicalQuantity(1, 'kilometer*hour^-1').convert(
                'kilometer*hour^-1'),
            Fraction)
        with self.assertRaises(IncompatibleUnitsError):
            PhysicalQuantity(1, 'kilometer').convert('kelvin')

    def test_compatible_unit(self):
        self.assertTrue(PhysicalQuantity(1, 'meter').compatible_unit('foot'))
        self.assertFalse(PhysicalQuantity(1, 'kilometer').compatible_unit(
            'watt'))

    def test_compatible_units(self):
        self.assertTrue(PhysicalQuantity.compatible_units('meter', 'foot'))
        self.assertFalse(PhysicalQuantity.compatible_units('meter', 'watt'))

    def test_same_unit(self):
        self.assertTrue(PhysicalQuantity.same_unit('meter*meter', 'meter^2'))
        self.assertFalse(PhysicalQuantity.same_unit('meter', 'foot'))
        self.assertFalse(PhysicalQuantity.same_unit('meter', 'kelvin'))

    def test_repr(self):
        self.assertEqual(
            repr(PhysicalQuantity(100, 'meter')),
            "PhysicalQuantity(100, u'meter')")
        a = PhysicalQuantity(1, 'kilometer')
        b = PhysicalQuantity(5, 'second')
        self.assertEqual(
            eval(repr(a)),
            a)
        self.assertEqual(
            eval(repr(a * b)),
            a * b)

    def test_str(self):
        self.assertEqual(
            str(PhysicalQuantity(100, 'meter')),
            '100 meter')
        self.assertEqual(
            str(PhysicalQuantity(10, 'kilogram')),
            '10000 gram')
        self.assertEqual(
            str(PhysicalQuantity('0.5', 'second')),
            '1/2 second')

    def test_unit_unit(self):
        unit = PhysicalQuantity(1, 'hectoproduction_a')
        self.assertEqual(unit.units, 'production_a')
        self.assertEqual(unit.value, 100)
        self.assertEqual(unit, PhysicalQuantity(100, 'production_a'))


class UtilityTypesTest(TestCase):
    def test_electricity_in_meter_utility_type_choices(self):
        self.assertIn(
            utilitytypes.METER_CHOICES.electricity,
            [
                db_value for db_value, _ in
                utilitytypes.METER_CHOICES])


class ExampleBreadcrumbsBuilder(object):
    def build_root_page_breadcrumbs(self):
        return Breadcrumbs((Breadcrumb('Root Page', 'http://test-url/'),))

    def build_node_page_breadcrumbs(self):
        return self.build_root_page_breadcrumbs() + \
            Breadcrumb(self.node_page_name, 'http://test-url/node/')

    def build_leaf_page_breadcrumbs(self):
        return self.build_node_page_breadcrumbs() + \
            Breadcrumb('Leaf Page')


class BreadcrumbsBaseTest(TestCase):
    def test_example_usage(self):
        breadcrumbs_builder = ExampleBreadcrumbsBuilder()
        breadcrumbs_builder.node_page_name = 'Node Page'

        iterator = iter(breadcrumbs_builder.build_leaf_page_breadcrumbs())
        self.assertEqual(
            next(iterator), Breadcrumb('Root Page', 'http://test-url/'))
        self.assertEqual(
            next(iterator), Breadcrumb('Node Page', 'http://test-url/node/'))
        self.assertEqual(next(iterator), Breadcrumb('Leaf Page', None))
        with self.assertRaises(StopIteration):
            next(iterator)


@override_settings(ENCRYPTION_TESTMODE=True)
class HomeViewBaseTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.factory = RequestFactory()

        class HomeView(HomeViewBase):
            def get_redirect_with_customer_url(self, customer_id):
                return "redirect_to_url/%s" % customer_id

            def get_choose_customer_url(self):
                return "choose_customer_url"

        self.view = HomeView.as_view()
        self.session = SessionMiddleware()

    def test_no_customers(self):
        request = self.factory.get('/')
        request.user = User(name_plain='test user')
        request.user.has_perm = lambda perm: True
        self.session.process_request(request)
        response = self.view(request)

        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.url, reverse('provider_site:customer-list'))

    def test_one_customer(self):
        self.customer = Customer(name_plain='test customer')
        self.customer.save()

        request = self.factory.get('/')
        request.user = User(name_plain='test user')
        request.user.has_perm = lambda perm: True
        self.session.process_request(request)
        response = self.view(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.url, "redirect_to_url/%s" % self.customer.id)

    def test_multiple_customers_no_session(self):
        self.customer = Customer(name_plain='test customer')
        self.customer.save()

        self.customer = Customer(name_plain='test customer2')
        self.customer.save()

        request = self.factory.get('/')
        request.user = User(name_plain='test user')
        request.user.has_perm = lambda perm: True
        self.session.process_request(request)
        response = self.view(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.url, "choose_customer_url")

    def test_multiple_customers_with_session(self):
        self.customer = Customer(name_plain='test customer')
        self.customer.save()

        self.customer2 = Customer(name_plain='test customer2')
        self.customer2.save()

        request = self.factory.get('/')
        request.user = User(name_plain='test user')
        request.user.has_perm = lambda perm: True
        self.session.process_request(request)
        request.session['chosen_customer_id'] = self.customer2.id
        response = self.view(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.url, "redirect_to_url/%s" % self.customer2.id)


@override_settings(ENCRYPTION_TESTMODE=True)
class CustomerViewBaseTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer(name_plain='test customer')
        self.customer.save()
        self.factory = RequestFactory()

        class CustomerView(CustomerViewBase):
            def get_redirect_with_customer_url(self, customer_id):
                return "redirect_to_url/%s" % customer_id

        self.view = CustomerView.as_view()
        self.session = SessionMiddleware()

    def test_customer_in_session(self):
        request = self.factory.get('/')
        request.user = User(name_plain='test user')
        request.user.has_perm = lambda perm: True
        self.session.process_request(request)
        response = self.view(request, customer_id=self.customer.id)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.url, "redirect_to_url/%s" % self.customer.id)
        self.assertEqual(
            request.session['chosen_customer_id'], self.customer.id)


class TestTimePeriodModel(models.Model):
    from_timestamp = models.DateTimeField()
    to_timestamp = models.DateTimeField()


class TestTimePeriodModelForm(TimePeriodModelForm):
    class Meta:
        model = TestTimePeriodModel
        fields = ()

    def _get_timezone(self):
        return pytz.timezone('Europe/Copenhagen')


class TimePeriodModelFormTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')

    def test_from_time_initialization_from_instance(self):
        instance = TestTimePeriodModel.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)))

        form = TestTimePeriodModelForm(instance=instance)
        self.assertEqual(form.initial['from_date'], datetime.date(2014, 1, 1))
        self.assertEqual(form.initial['from_hour'], 0)

    def test_to_time_initialization_from_instance_midnight(self):
        instance = TestTimePeriodModel.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)))

        form = TestTimePeriodModelForm(instance=instance)
        self.assertEqual(form.initial['to_date'], datetime.date(2014, 1, 1))
        self.assertEqual(form.initial['to_hour'], 24)

    def test_to_time_initialization_from_instance_noon(self):
        instance = TestTimePeriodModel.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1, 12)))

        form = TestTimePeriodModelForm(instance=instance)
        self.assertEqual(form.initial['to_date'], datetime.date(2014, 1, 1))
        self.assertEqual(form.initial['to_hour'], 12)

    def test_from_time_clean(self):
        form = TestTimePeriodModelForm(data={
            'from_date': '2014-01-01',
            'from_hour': 0,
            'to_date': '2014-01-01',
            'to_hour': 12})
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.instance.from_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 1)))

    def test_from_time_clean_midnight(self):
        form = TestTimePeriodModelForm(data={
            'from_date': '2014-01-01',
            'from_hour': 24,
            'to_date': '2014-01-02',
            'to_hour': 12})
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.instance.from_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 2)))

    def test_to_time_clean(self):
        form = TestTimePeriodModelForm(data={
            'from_date': '2014-01-01',
            'from_hour': 0,
            'to_date': '2014-01-01',
            'to_hour': 12})
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.instance.to_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 1, 12)))

    def test_to_time_clean_midnight(self):
        form = TestTimePeriodModelForm(data={
            'from_date': '2014-01-01',
            'from_hour': 0,
            'to_date': '2014-01-01',
            'to_hour': 24})
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.instance.to_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 2)))

    def test_invalid_from_time_does_not_alter_instance(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1, 12))
        instance = TestTimePeriodModel.objects.create(
            from_timestamp=from_timestamp, to_timestamp=to_timestamp)

        form = TestTimePeriodModelForm(data={
            'from_date': '',
            'from_hour': '',
            'to_date': '2014-01-01',
            'to_hour': 24}, instance=instance)
        self.assertFalse(form.is_valid())
        self.assertEquals(form.instance.from_timestamp, from_timestamp)

    def test_invalid_to_time_does_not_alter_instance(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1, 12))
        instance = TestTimePeriodModel.objects.create(
            from_timestamp=from_timestamp, to_timestamp=to_timestamp)

        form = TestTimePeriodModelForm(data={
            'from_date': '2014-01-01',
            'from_hour': '0',
            'to_date': '',
            'to_hour': ''}, instance=instance)
        self.assertFalse(form.is_valid())
        self.assertEquals(form.instance.to_timestamp, to_timestamp)


class TestTimePeriodModel(models.Model):
    from_timestamp = models.DateTimeField()
    to_timestamp = models.DateTimeField()


class TestHalfOpenTimePeriodModelForm(HalfOpenTimePeriodModelForm):
    class Meta:
        model = TestTimePeriodModel
        fields = ()

    def _get_timezone(self):
        return pytz.timezone('Europe/Copenhagen')


class HalfOpenTimePeriodModelFormTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')

    def test_cleared_to_date_alter_instance_to_timestamp(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1, 12))
        instance = TestTimePeriodModel.objects.create(
            from_timestamp=from_timestamp, to_timestamp=to_timestamp)

        form = TestHalfOpenTimePeriodModelForm(data={
            'from_date': '2014-01-01',
            'from_hour': '0',
            'to_date': '',
            'to_hour': '24'}, instance=instance)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.instance.to_timestamp)


@override_settings(ENCRYPTION_TESTMODE=True)
class PreviousMonthInitialValuesTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.timezone('Europe/Copenhagen'))

    def test_transition(self):
        timestamp = self.customer.timezone.localize(
            datetime.datetime(2014, 2, 1))
        with replace_customer(self.customer):
            initial = previous_month_initial_values(timestamp)

        self.assertEqual(initial['from_date'], datetime.date(2014, 1, 1))
        self.assertEqual(initial['to_date'], datetime.date(2014, 1, 31))
        self.assertEqual(initial['from_hour'], 0)
        self.assertEqual(initial['to_hour'], 24)

    def test_regular(self):
        timestamp = self.customer.timezone.localize(
            datetime.datetime(2014, 2, 15))
        with replace_customer(self.customer):
            initial = previous_month_initial_values(timestamp)

        self.assertEqual(initial['from_date'], datetime.date(2014, 1, 1))
        self.assertEqual(initial['to_date'], datetime.date(2014, 1, 31))
        self.assertEqual(initial['from_hour'], 0)
        self.assertEqual(initial['to_hour'], 24)

    def test_now(self):
        with replace_customer(self.customer):
            initial = previous_month_initial_values()
        self.assertIsInstance(initial['from_date'], datetime.date)
        self.assertIsInstance(initial['to_date'], datetime.date)
        self.assertEqual(initial['from_hour'], 0)
        self.assertEqual(initial['to_hour'], 24)


class VirtualBaseModel(StoreSubclass):
    @virtual
    def __unicode__(self):
        return 'Base class'

    @virtual
    def compute(self, a, b):
        return a + b


class VirtualSubModel(VirtualBaseModel):
    def __unicode__(self):
        return 'Subclass'

    @virtual
    def compute(self, a, b):
        return a * b


@override_settings(ENCRYPTION_TESTMODE=True)
class TestVirtual(TestCase):
    def test_base(self):
        obj = VirtualBaseModel.objects.create()
        loaded = VirtualBaseModel.objects.get(pk=obj.id)
        self.assertEqual(unicode(loaded), 'Base class')

    def test_submodel(self):
        obj = VirtualSubModel.objects.create()
        loaded = VirtualBaseModel.objects.get(pk=obj.id)
        self.assertEqual(unicode(loaded), 'Subclass')

    def test_parameterised(self):
        obj_base = VirtualBaseModel.objects.create()
        obj_sub = VirtualSubModel.objects.create()
        loaded_base = VirtualBaseModel.objects.get(pk=obj_base.id)
        loaded_sub = VirtualBaseModel.objects.get(pk=obj_sub.id)
        self.assertEqual(loaded_base.compute(2, 3), 5)
        self.assertEqual(loaded_sub.compute(2, 3), 6)


@override_settings(ENCRYPTION_TESTMODE=True)
class DateRangeModelMixinTest(TestCase):
    def test_empty_period(self):
        unit = DateRangeModelMixin(
            from_date=datetime.date(2000, 1, 2),
            to_date=datetime.date(2000, 1, 1))

        with self.assertRaises(ValidationError):
            unit.clean()

    def test_one_day_period(self):
        unit = DateRangeModelMixin(
            from_date=datetime.date(2000, 1, 1),
            to_date=datetime.date(2000, 1, 1))
        unit.clean()

    def test_default_period(self):
        with replace_customer(Customer(timezone=pytz.utc)):
            unit = DateRangeModelMixin()
        self.assertIsInstance(unit.from_date, datetime.date)
        self.assertIsNone(unit.to_date)
        unit.clean()


@override_settings(ENCRYPTION_TESTMODE=True)
class DateRangeModelMixinTimestampRangeIntersectionTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')

    def test_timestamp_within_range(self):
        daterangemodel = DateRangeModelMixin(
            from_date=datetime.date(2014, 1, 1))

        intersection = daterangemodel.timestamp_range_intersection(
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 2)),
            self.timezone)

        self.assertEqual(
            intersection.from_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 1)))

        self.assertEqual(
            intersection.to_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 2)))

    def test_timestamp_before_range(self):
        daterangemodel = DateRangeModelMixin(
            from_date=datetime.date(2014, 1, 1))

        intersection = daterangemodel.timestamp_range_intersection(
            self.timezone.localize(datetime.datetime(2013, 1, 1)),
            self.timezone.localize(datetime.datetime(2013, 1, 2)),
            self.timezone)

        self.assertIsNone(intersection)

    def test_timestamp_after_range(self):
        daterangemodel = DateRangeModelMixin(
            from_date=datetime.date(2014, 1, 1),
            to_date=datetime.date(2014, 1, 2))

        intersection = daterangemodel.timestamp_range_intersection(
            self.timezone.localize(datetime.datetime(2014, 1, 3, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 4)),
            self.timezone)

        self.assertIsNone(intersection)

    def test_timestamp_overlap_range(self):
        daterangemodel = DateRangeModelMixin(
            from_date=datetime.date(2014, 1, 1))

        intersection = daterangemodel.timestamp_range_intersection(
            self.timezone.localize(datetime.datetime(2013, 12, 24)),
            self.timezone.localize(datetime.datetime(2014, 1, 2)),
            self.timezone)

        self.assertEqual(
            intersection.from_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 1)))

        self.assertEqual(
            intersection.to_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 2)))

    def test_timestamp_match_range(self):
        daterangemodel = DateRangeModelMixin(
            from_date=datetime.date(2014, 1, 1),
            to_date=datetime.date(2014, 1, 1))

        intersection = daterangemodel.timestamp_range_intersection(
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 2)),
            self.timezone)

        self.assertEqual(
            intersection.from_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 1)))

        self.assertEqual(
            intersection.to_timestamp,
            self.timezone.localize(datetime.datetime(2014, 1, 2)))


class DateRangeTestModelManager(
        DateRangeManagerMixin, models.Manager):
    pass


class DateRangeTestModel(DateRangeModelMixin):
    objects = DateRangeTestModelManager()


@override_settings(ENCRYPTION_TESTMODE=True)
class DateRangeManagerMixinTest(TestCase):
    def setUp(self):
        self.in_range = DateRangeTestModel.objects.create(
            from_date=datetime.date(2000, 1, 1))
        self.out_of_range = DateRangeTestModel.objects.create(
            from_date=datetime.date(2000, 1, 1),
            to_date=datetime.date(2001, 9, 11))

    def test_all(self):
        self.assertEqual(2, DateRangeTestModel.objects.all().count())

    def test_none_in_range(self):
        self.assertFalse(
            DateRangeTestModel.objects.in_range(
                from_date=datetime.date(1990, 1, 1),
                to_date=datetime.date(1999, 12, 31)).exists())

    def test_in_range(self):
        self.assertEqual(
            [self.in_range.id],
            list(
                DateRangeTestModel.objects.in_range(
                    from_date=datetime.date(2002, 1, 1),
                    to_date=datetime.date(2002, 1, 1)).
                values_list('id', flat=True)))


class TimestampRangeTestModelManager(
        TimestampRangeManagerMixin, models.Manager):
    pass


class TimestampRangeTestModel(TimestampRangeModelMixin):
    objects = TimestampRangeTestModelManager()


@override_settings(ENCRYPTION_TESTMODE=True)
class TimestampRangeManagerMixinTest(TestCase):
    def setUp(self):
        self.timezone = pytz.utc
        self.in_range = TimestampRangeTestModel.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2000, 1, 1)))
        self.out_of_range = TimestampRangeTestModel.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2000, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2001, 9, 11)))

    def test_all(self):
        self.assertEqual(2, TimestampRangeTestModel.objects.all().count())

    def test_none_in_range(self):
        self.assertFalse(
            TimestampRangeTestModel.objects.in_range(
                from_timestamp=self.timezone.localize(
                    datetime.datetime(1990, 1, 1)),
                to_timestamp=self.timezone.localize(
                    datetime.datetime(1999, 12, 31))).exists())

    def test_in_range(self):
        self.assertEqual(
            [self.in_range.id],
            list(
                TimestampRangeTestModel.objects.in_range(
                    from_timestamp=self.timezone.localize(
                        datetime.datetime(2002, 1, 1)),
                    to_timestamp=self.timezone.localize(
                        datetime.datetime(2002, 1, 1))).
                values_list('id', flat=True)))


@override_settings(ENCRYPTION_TESTMODE=True)
class TimestampRangeModelMixinTest(TestCase):
    def setUp(self):
        self.timezone = pytz.utc

    def test_clean_no_to_timestamp_success(self):
        instance = TimestampRangeTestModel(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)))
        instance.clean()

    def test_clean_success(self):
        instance = TimestampRangeTestModel(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))
        instance.clean()

    def test_clean_empty_lifespan(self):
        instance = TimestampRangeTestModel(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)))
        with self.assertRaises(ValidationError):
            instance.clean()

    def test_unicode_without_to_timestamp(self):
        instance = TimestampRangeTestModel(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)))

        unicode(
            instance.format_timestamp_range_unicode('pøp cörn', self.timezone))

    def test_unicode_with_to_timestamp(self):
        instance = TimestampRangeTestModel(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 2)))

        unicode(
            instance.format_timestamp_range_unicode('pøp cörn', self.timezone))


class SumOrNoneTest(TestCase):
    def test_empty_sum(self):
        self.assertIsNone(sum_or_none([]))

    def test_sum_of_physical_quantities(self):
        self.assertEqual(
            PhysicalQuantity(sum(range(4)), 'meter'),
            sum_or_none(PhysicalQuantity(i, 'meter') for i in range(4)))


@override_settings(
    ENCRYPTION_TESTMODE=True)
class ValidDateForDataSequenceTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.customer = Customer.objects.create(timezone=self.timezone)

        self.consumption1 = Consumption.objects.create(
            unit='kilowatt*hour', customer=self.customer)
        self.consumption2 = Consumption.objects.create(
            unit='kilowatt*hour', customer=self.customer)

        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            datasequence=self.consumption1,
            value=423,
            unit='kilowatt*hour')

        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 2, 5)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 2, 5)),
            datasequence=self.consumption2,
            value=423,
            unit='kilowatt*hour')

    def test_next_valid_date_for_datasequence(self):
        self.assertEqual(
            datetime.date(2014, 2, 5),
            next_valid_date_for_datasequence(
                [self.consumption1, self.consumption2],
                datetime.date(2014, 1, 15),
                self.timezone))

    def test_previous_valid_date_for_datasequence(self):
        self.assertEqual(
            datetime.date(2013, 12, 31),
            previous_valid_date_for_datasequence(
                [self.consumption1, self.consumption2],
                datetime.date(2014, 1, 15),
                self.timezone))


class TestYearWeekPeriodForm(YearWeekPeriodForm):
    def _get_timezone(self):
        return pytz.timezone('Europe/Copenhagen')


@override_settings(
    ENCRYPTION_TESTMODE=True)
class YearWeakPeriodFormTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')

    def test_get_timestamps(self):
        form = TestYearWeekPeriodForm(data={'week': 1, 'year': 2014})
        form.is_valid()
        self.assertEqual(
            (self.timezone.localize(datetime.datetime(2013, 12, 30, 0, 0)),
             self.timezone.localize(datetime.datetime(2014, 1, 6, 0, 0))),
            form.get_timestamps())

    def test_get_timestamps_middle_year(self):
        form = TestYearWeekPeriodForm(data={'week': 25, 'year': 2014})
        form.is_valid()
        self.assertEqual(
            (self.timezone.localize(datetime.datetime(2014, 6, 16, 0, 0)),
             self.timezone.localize(datetime.datetime(2014, 6, 23, 0, 0))),
            form.get_timestamps())

    def test_no_week_53(self):
        form = TestYearWeekPeriodForm(data={'week': 53, 'year': 2005})
        form.is_valid()
        with self.assertRaises(ValidationError):
            form.clean()

    def test_initial_values(self):
        form = TestYearWeekPeriodForm(data=this_week_initial_values(
            self.timezone.localize(datetime.datetime(2014, 1, 3, 0, 0))))
        form.is_valid()
        self.assertEqual(
            (self.timezone.localize(datetime.datetime(2013, 12, 30, 0, 0)),
             self.timezone.localize(datetime.datetime(2014, 1, 6, 0, 0))),
            form.get_timestamps())
