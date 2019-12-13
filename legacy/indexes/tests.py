# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module contains unittests for the indexes app.
"""

from decimal import Decimal
from fractions import Fraction
import datetime
import math
import warnings

from django.db.models import ProtectedError
from django.test import TestCase
from django.test.utils import override_settings

import pytz

from gridplatform import trackuser
from gridplatform.customers.models import Customer
from gridplatform.encryption.shell import Request
from gridplatform.encryption.middleware import KeyLoaderMiddleware
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from gridplatform.users.models import User
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.providers.models import Provider
from gridplatform.encryption.testutils import encryption_context

from . import IndexWarning
from .models import Period
from .models import Index
from .models import Entry
from .models.period import normalize_periods
from .models import StandardMonthIndex


@override_settings(ENCRYPTION_TESTMODE=True)
class NormalizePeriodsTest(TestCase):
    """
    Test the L{normalize_periods()} procedure of the L{indexes}
    application.
    """

    def test_no_periods(self):
        """
        Test that the empty list of periods remains the empty list of
        periods.
        """
        self.assertEqual([], list(normalize_periods([])))

    def test_noncontiguous_periods(self):
        """
        Test that noncontiguous periods are not modified.
        """
        periods = [
            (datetime.datetime(2012, 12, 24, 1),
             datetime.datetime(2012, 12, 24, 3)),
            (datetime.datetime(2012, 12, 24, 4),
             datetime.datetime(2012, 12, 24, 7))]

        self.assertEqual(periods, list(normalize_periods(periods)))

    def test_contiguous_periods(self):
        """
        Test that contiguous periods are coalesced.
        """
        periods = [
            (datetime.datetime(2012, 12, 24, 1),
             datetime.datetime(2012, 12, 24, 3)),
            (datetime.datetime(2012, 12, 24, 3),
             datetime.datetime(2012, 12, 24, 7))]

        self.assertIn(
            (datetime.datetime(2012, 12, 24, 1),
             datetime.datetime(2012, 12, 24, 7)),
            normalize_periods(periods))

    def test_overlapping_periods(self):
        """
        Test that normalizing overlapping periods causes an assertion
        error.
        """
        periods = [
            (datetime.datetime(2012, 12, 24, 1),
             datetime.datetime(2012, 12, 24, 4)),
            (datetime.datetime(2012, 12, 24, 3),
             datetime.datetime(2012, 12, 24, 7))]

        with self.assertRaises(AssertionError):
            [p for p in normalize_periods(periods)]


@override_settings(ENCRYPTION_TESTMODE=True)
class IndexTest(TestCase):
    """
    Test L{Index}, L{Entry}, L{DerivedIndexPeriod} and
    L{SeasonIndexPeriod} classes of the L{indexes} application.
    """

    def setUp(self):
        """
        Initializes the Index and Entry tables with a power price cost
        index, from around an interresting period.

        @postcondition: self.unit contains an Index instance,
        representing the mentioned interresting period.
        """
        self.unit = Index(unit="currency_dkk*kilowatt^-1*hour^-1",
                          name="NOE pristabel",
                          role=DataRoleField.ELECTRICITY_TARIFF,
                          data_format=Index.SPOT,
                          customer=None,
                          utility_type=utilitytypes.METER_CHOICES.electricity,
                          timezone='Europe/Copenhagen')
        self.unit.save()

        hour = 0
        # 2011-03-27 2:00 happens to be a point in time where Denmark
        # enters daylight saving time (the clock is set back one
        # hour).
        self.DATETIME = datetime.datetime(2011, 3, 26, 0, tzinfo=pytz.utc)
        for price in [0.20, 0.22, 0.21, 0.25, 0.31, 0.37,   # 0:00
                      0.41, 0.52, 0.52, 0.50, 0.47, 0.47,   # 06:00
                      0.40, 0.40, 0.39, 0.58, 0.63, 0.70,   # 12:00
                      0.65, 0.58, 0.51, 0.46, 0.33, 0.28,   # 18:00
                      0.25, 0.22, 0.21, 0.25, 0.31, 0.37,   # 0:00
                      0.41, 0.51, 0.52, 0.50, 0.41, 0.47,   # 06:00
                      0.40, 0.40, 0.39, 0.58, 0.63, 0.70,   # 12:00
                      0.65, 0.58, 0.56, 0.46, 0.33, 0.28]:  # 18:00
            if hour != 15:
                entry = Entry(
                    index=self.unit,
                    from_timestamp=(
                        self.DATETIME + datetime.timedelta(hours=hour)),
                    to_timestamp=(
                        self.DATETIME + datetime.timedelta(hours=hour + 1)),
                    value=price)
                entry.save()
            hour += 1

        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)

    def assert_warning_category(self, warning_list, category,
                                minimum_count=1):
        """
        Assert that a C{warning} within a given C{category} has been
        issued a C{minimum_count} of times.
        """
        if len(filter(lambda w: w.category == IndexWarning,
                      warning_list)) < minimum_count:
            raise AssertionError(
                "Less than %d warning(s) of category %r was issued" %
                (minimum_count, category))

    def test_assert_warning_category(self):
        """
        Test L{assert_warning_category()}.
        """
        with self.assertRaises(AssertionError):
            self.assert_warning_category([], IndexWarning)

        with warnings.catch_warnings(record=True) as w:
            warnings.warn("this is an IndexWarning!", IndexWarning)
            self.assert_warning_category(w, IndexWarning)

        with warnings.catch_warnings(record=True) as w:
            warnings.warn("this is an IndexWarning!", IndexWarning)
            warnings.warn("this is not an IndexWarning!")
            self.assert_warning_category(w, IndexWarning)

        with warnings.catch_warnings(record=True) as w:
            warnings.warn("this is not an IndexWarning!")
            with self.assertRaises(AssertionError):
                self.assert_warning_category(w, IndexWarning)

    def test_minimize_contiguous_missing_entries(self):
        """
        Test that contiguous minimization across missing entries does not fail.
        """
        result = self.unit.minimize_contiguous(
            self.DATETIME + datetime.timedelta(
                days=1, hours=23),
            self.DATETIME + datetime.timedelta(
                days=2, hours=23),
            datetime.timedelta(hours=2))

        self.assertIsNotNone(result)

    def test_minimize_noncontiguous_missing_entries(self):
        """
        Test that noncontiguous minimization across missing entries does not
        fail.
        """
        result = list(
            self.unit.minimize_noncontiguous(
                self.DATETIME,
                self.DATETIME + datetime.timedelta(
                    days=3),
                datetime.timedelta(hours=60)))

        self.assertNotEqual(len(result), 0)

    def test_minimize_noncontiguous_missing_entries_before(self):
        """
        Test that noncontiguous minimization across missing entries in start of
        interval does not fail.
        """
        self.assertEqual(
            [(self.DATETIME - datetime.timedelta(hours=1),
              self.DATETIME - datetime.timedelta(minutes=30)),
             (self.DATETIME, self.DATETIME + datetime.timedelta(hours=1))],
            list(
                self.unit.minimize_noncontiguous(
                    self.DATETIME - datetime.timedelta(hours=1),
                    self.DATETIME + datetime.timedelta(hours=1),
                    datetime.timedelta(hours=1, minutes=30))))

    def test_minimize_noncontiguous_missing_entries_after(self):
        """
        Test that noncontiguous minimization across missing entries in end of
        interval does not fail.
        """
        self.assertEqual(
            [(self.DATETIME + datetime.timedelta(days=1, hours=23),
              self.DATETIME + datetime.timedelta(days=2, minutes=30))],
            list(
                self.unit.minimize_noncontiguous(
                    self.DATETIME + datetime.timedelta(days=1, hours=23),
                    self.DATETIME + datetime.timedelta(days=2, hours=1),
                    datetime.timedelta(hours=1, minutes=30))))

    def test_minimize_noncontiguous_missing_entries_middle(self):
        """
        Test that noncontiguous minimization across missing entries in middle
        of interval does not fail.
        """
        self.assertEqual(
            [(self.DATETIME + datetime.timedelta(hours=14),
              self.DATETIME + datetime.timedelta(hours=15, minutes=30)),
             (self.DATETIME + datetime.timedelta(hours=16),
              self.DATETIME + datetime.timedelta(hours=17))],
            list(
                self.unit.minimize_noncontiguous(
                    self.DATETIME + datetime.timedelta(hours=14),
                    self.DATETIME + datetime.timedelta(hours=17),
                    datetime.timedelta(hours=2, minutes=30))))

    def test_noncontiguous_minimization_a_bit_expensive(self):
        """
        Test noncontiguous minimization that will include part of the
        most expensive period.
        """
        result = list(
            self.unit.minimize_noncontiguous(
                self.DATETIME + datetime.timedelta(hours=16, minutes=53),
                self.DATETIME + datetime.timedelta(hours=18, minutes=30),
                datetime.timedelta(hours=1, minutes=7)))

        self.assertEqual(len(result), 2)
        self.assertIn(
            (self.DATETIME + datetime.timedelta(hours=16, minutes=53),
             self.DATETIME + datetime.timedelta(hours=17, minutes=30)), result)
        self.assertIn(
            (self.DATETIME + datetime.timedelta(hours=18),
             self.DATETIME + datetime.timedelta(hours=18, minutes=30)), result)

    def test_minimize_contiguous_cheapest_at_end_of_entry(self):
        """
        Test that the L{minimize_contiguous()} method returns the
        right result when the result is at the end of an entry.
        """
        self.assertEqual(
            self.DATETIME + datetime.timedelta(hours=1, minutes=45),
            self.unit.minimize_contiguous(
                self.DATETIME + datetime.timedelta(hours=1, minutes=30),
                self.DATETIME + datetime.timedelta(hours=3, minutes=30),
                datetime.timedelta(hours=1, minutes=15)))

    def test_minimize_contiguous_cheapest_at_start_of_entry(self):
        """
        Test that the L{minimize_contiguous()} method returns the
        right result, when the result is at the start of an entry.
        """
        self.assertEqual(
            self.DATETIME + datetime.timedelta(hours=2),
            self.unit.minimize_contiguous(
                self.DATETIME + datetime.timedelta(hours=2),
                self.DATETIME + datetime.timedelta(hours=4, minutes=30),
                datetime.timedelta(hours=1, minutes=15)))

    def test_minimize_contiguous_cheapest_at_end_of_interval(self):
        """
        Test that the L{Index.minimize_contiguous()} method returns the
        right result, when the result is at the end of the interval.
        """
        self.assertEqual(
            self.DATETIME + datetime.timedelta(days=1, hours=1, minutes=34),
            self.unit.minimize_contiguous(
                self.DATETIME + datetime.timedelta(days=1),
                self.DATETIME + datetime.timedelta(days=1,
                                                   hours=2, minutes=34),
                datetime.timedelta(hours=1)))

    def test_generate_true_periods(self):
        """
        Test the L{Index.generate_true_periods()} method against a selected
        number of operators.
        """
        periods = self.unit.generate_true_periods(
            self.DATETIME,
            self.DATETIME + datetime.timedelta(days=1),
            lambda x: x <= PhysicalQuantity('0.29', self.unit.unit))
        self.assertIn((self.DATETIME,
                       self.DATETIME + datetime.timedelta(hours=4)),
                      periods)
        self.assertIn((self.DATETIME + datetime.timedelta(hours=23),
                       self.DATETIME + datetime.timedelta(hours=24)),
                      periods)

        periods = self.unit.generate_true_periods(
            self.DATETIME,
            self.DATETIME + datetime.timedelta(days=1),
            lambda x: x != PhysicalQuantity('0.40', self.unit.unit))
        self.assertIn((self.DATETIME,
                       self.DATETIME + datetime.timedelta(hours=12)),
                      periods)
        self.assertIn((self.DATETIME + datetime.timedelta(hours=14),
                       self.DATETIME + datetime.timedelta(hours=15)),
                      periods)
        self.assertIn((self.DATETIME + datetime.timedelta(hours=16),
                       self.DATETIME + datetime.timedelta(hours=24)),
                      periods)

    def test_derived_index_with_offset_scenario(self):
        """
        Test the "Derived Index with Offset" scenario.
        """
        derived = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="NOE gr&oslash;n tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.DERIVED,
            timezone="Europe/Copenhagen",
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        derived.save()

        derived.derivedindexperiod_set.create(
            other_index=self.unit,
            from_date=self.DATETIME.date(),
            constant=Decimal("0.07"))

        with warnings.catch_warnings(record=True):
            periods = derived.generate_true_periods(
                self.DATETIME - datetime.timedelta(days=1),
                self.DATETIME + datetime.timedelta(days=3),
                lambda x: x <= PhysicalQuantity('0.29', derived.unit))
            self.assertIn(
                (self.DATETIME,
                 self.DATETIME + datetime.timedelta(hours=3)),
                periods)
            self.assertIn(
                (self.DATETIME + datetime.timedelta(days=1, hours=1),
                 self.DATETIME + datetime.timedelta(days=1, hours=3)),
                periods)
            self.assertEqual(len(periods), 2)

    def test_dependency(self):
        derived = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="NOE gr&oslash;n tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.DERIVED,
            timezone="Europe/Copenhagen",
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        derived.save()

        derived.derivedindexperiod_set.create(
            other_index=self.unit,
            from_date=self.DATETIME.date(),
            constant=Decimal("0.07"))

        self.assertRaises(
            ProtectedError, lambda:
            self.unit.delete())

    def test_derived_index_with_roof_scenario(self):
        """
        Test the "Derived Index with Roof" scenario.
        """
        derived = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="NOE lofttariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.DERIVED,
            timezone="Europe/Copenhagen",
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        derived.save()

        derived.derivedindexperiod_set.create(
            other_index=self.unit,
            from_date=self.DATETIME.date(),
            constant=Decimal("0.12"),
            roof=Decimal("0.50"))

        with warnings.catch_warnings(record=True):
            # The small saving at 2011-03-27 15:00 along with the
            # large savings around 2011-03-27 03:00 is included in the
            # minimal contiguous usage when considering the derived
            # index.
            result = derived.minimize_contiguous(
                self.DATETIME + datetime.timedelta(hours=18),
                self.DATETIME + datetime.timedelta(days=1, hours=18),
                datetime.timedelta(hours=8))
            self.assertEqual(self.DATETIME + datetime.timedelta(hours=22),
                             result)

            # The cost increment at 2011-03-27 17.00 is larger than
            # that of 2011-03-26 19.00 in the original index.
            non_derived_result = self.unit.minimize_contiguous(
                self.DATETIME + datetime.timedelta(hours=18),
                self.DATETIME + datetime.timedelta(days=1, hours=18),
                datetime.timedelta(hours=20))
            self.assertEqual(self.DATETIME + datetime.timedelta(hours=19),
                             non_derived_result)

    def test_derived_index_half_flat_scenario(self):
        """
        Test the "Derived Index - Half Flat" scenario.
        """
        derived = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="NOE 50/50 tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.DERIVED,
            timezone="Europe/Copenhagen",
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        derived.save()

        derived.derivedindexperiod_set.create(
            other_index=self.unit,
            from_date=self.DATETIME.date(),
            constant=Decimal("0.20"),
            coefficient=Decimal("0.50"))

        with warnings.catch_warnings(record=True):
            periods = derived.generate_true_periods(
                self.DATETIME - datetime.timedelta(days=1),
                self.DATETIME + datetime.timedelta(days=3),
                lambda x: x <= PhysicalQuantity('0.35', derived.unit))
            self.assertIn(
                (self.DATETIME,
                 self.DATETIME + datetime.timedelta(hours=4)),
                periods)
            self.assertIn(
                (self.DATETIME + datetime.timedelta(hours=23),
                 self.DATETIME + datetime.timedelta(days=1, hours=4)),
                periods)
            self.assertIn(
                (self.DATETIME + datetime.timedelta(days=1, hours=23),
                 self.DATETIME + datetime.timedelta(days=2, hours=0)),
                periods)
            self.assertEqual(len(periods), 3)

    def test_manual_index_with_seasons_scenario(self):
        """
        Test the "Manual Index with Seasons" scenario.
        """
        seasons = Index(
            unit="currency_eur*kilowatt^-1*hour^-1",
            name="Temporada Alta/Temporada Baja",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SEASONS,
            timezone="Europe/Copenhagen",
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        seasons.save()

        alta_value_at_hour = [Decimal("0.043") for _ in range(24)]
        for i in range(7, 9) + range(17, 20):
            alta_value_at_hour[i] = Decimal("0.052")

        season = seasons.seasonindexperiod_set.create(
            from_date=datetime.date(year=2012, month=4, day=1),
            value_at_hour=alta_value_at_hour)

        self.assertEqual(
            Decimal("0.052"),
            list(
                season.generate_entries(
                    pytz.timezone("Europe/Copenhagen").localize(
                        datetime.datetime(
                            year=2012, month=5, day=1, hour=8)),
                    pytz.timezone("Europe/Copenhagen").localize(
                        datetime.datetime(
                            year=2012, month=5, day=1, hour=9))))[0].value)

        self.assertAlmostEqual(
            seasons.calculate_average_value(
                pytz.timezone("Europe/Copenhagen").localize(
                    datetime.datetime(year=2012, month=5, day=1, hour=8)),
                pytz.timezone("Europe/Copenhagen").localize(
                    datetime.datetime(year=2012, month=5, day=1, hour=9))).
            convert(seasons.unit),
            Fraction('0.052'))

        seasons.seasonindexperiod_set.create(
            from_date=datetime.date(year=2012, month=12, day=20),
            value_at_hour=alta_value_at_hour)

        baja_value_at_hour = [Decimal("0.032") for _ in range(24)]
        for i in range(7, 9) + range(17, 20):
            baja_value_at_hour[i] = Decimal("0.049")

        seasons.seasonindexperiod_set.create(
            from_date=datetime.date(year=2012, month=1, day=1),
            value_at_hour=baja_value_at_hour)

        seasons.seasonindexperiod_set.create(
            from_date=datetime.date(year=2012, month=9, day=1),
            value_at_hour=baja_value_at_hour)

        self.assertAlmostEqual(
            seasons.calculate_average_value(
                pytz.timezone("Europe/Copenhagen").localize(
                    datetime.datetime(year=2012, month=1, day=1, hour=0)),
                pytz.timezone("Europe/Copenhagen").localize(
                    datetime.datetime(year=2012, month=1, day=1, hour=1))).
            convert(seasons.unit),
            Fraction('0.032'))

        # Manually figure out what the definite integral of 2012
        # should equal:
        alta_days = ((datetime.date(year=2012, month=9, day=1)
                      - datetime.date(year=2012, month=4, day=1))
                     + (datetime.date(year=2013, month=1, day=1)
                        - datetime.date(year=2012, month=12, day=20))).days
        baja_days = (
            pytz.timezone("Europe/Copenhagen").localize(
                datetime.datetime(year=2013, month=1, day=1)) -
            pytz.timezone("Europe/Copenhagen").localize(
                datetime.datetime(year=2012, month=1, day=1))).days - alta_days

        expected_result = \
            alta_days * (19 * Fraction('0.043') + 5 * Fraction('0.052')) + \
            baja_days * (19 * Fraction('0.032') + 5 * Fraction('0.049'))

        self.assertAlmostEqual(
            expected_result,
            (
                seasons.calculate_average_value(
                    pytz.timezone("Europe/Copenhagen").localize(
                        datetime.datetime(year=2012, month=1, day=1)),
                    pytz.timezone("Europe/Copenhagen").localize(
                        datetime.datetime(year=2013, month=1, day=1))) * (
                    pytz.timezone("Europe/Copenhagen").localize(
                        datetime.datetime(year=2013, month=1, day=1)) -
                    pytz.timezone("Europe/Copenhagen").localize(
                        datetime.datetime(year=2012, month=1, day=1))
                ).total_seconds() / 3600).convert(seasons.unit))

    def test_satisfies_search(self):
        """
        Check the L{Index.satisfies_search()} method.
        """
        self.assertTrue(self.unit.satisfies_search("ist"))
        self.assertFalse(self.unit.satisfies_search("table"))

    def test_derived_index_period_transition(self):
        """
        Test transition from one period into another for derived
        indexes.
        """
        derived = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="NOE 50/50 tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.DERIVED,
            timezone="Europe/Copenhagen",
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        derived.save()

        first_constant = Decimal("0.20")
        first_coefficient = Decimal("0.50")

        derived.derivedindexperiod_set.create(
            other_index=self.unit,
            from_date=datetime.date(year=2011, month=3, day=26),
            constant=first_constant,
            coefficient=first_coefficient)

        second_constant = Decimal("1.40")
        second_coefficient = Decimal("0.90")

        derived.derivedindexperiod_set.create(
            other_index=self.unit,
            from_date=datetime.date(year=2011, month=3, day=27),
            constant=second_constant,
            coefficient=second_coefficient)

        timezone = pytz.timezone("Europe/Copenhagen")

        start = timezone.localize(datetime.datetime(2011, 3, 26, 12))
        transition = timezone.localize(datetime.datetime(2011, 3, 27, 0))
        end = timezone.localize(datetime.datetime(2011, 3, 27, 12))

        # start to transition has 11 values since 15:00 is excluded (see setUp)
        # transition to end has 11 values due to daylight savings
        expected_result = self.unit.calculate_average_value(
            start, transition) * first_coefficient + \
            PhysicalQuantity(first_constant, derived.unit) * 11 + \
            self.unit.calculate_average_value(transition, end) * \
            second_coefficient + \
            PhysicalQuantity(second_constant, derived.unit) * 11

        actual_result = derived.calculate_average_value(start, end)

        self.assertEqual(actual_result.units, expected_result.units)
        self.assertAlmostEqual(actual_result.value, expected_result.value)

    def test_get_derivatives(self):
        """
        Test the L{Index.get_derivatives()} method.
        """
        # Create derived as a derivative of self.unit.
        derived = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="NOE gr&oslash;n tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.DERIVED,
            timezone="Europe/Copenhagen",
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        derived.save()
        derived.derivedindexperiod_set.create(
            other_index=self.unit,
            from_date=self.DATETIME.date(),
            constant=Decimal("0.07"))

        # The derived Index should be a derivative of self.unit, but
        # not vice versa.
        self.assertIn(derived, self.unit.get_derivatives())
        self.assertNotIn(self.unit, derived.get_derivatives())

        # Create derived2 as a derivative of derived.
        derived2 = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="NOE gr&oslash;n tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.DERIVED,
            timezone="Europe/Copenhagen",
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        derived2.save()
        derived2.derivedindexperiod_set.create(
            other_index=derived,
            from_date=self.DATETIME.date(),
            constant=Decimal("0.07"))

        # Derived2 is a derivative of derived, but not vice versa.
        self.assertIn(derived2, derived.get_derivatives())
        self.assertNotIn(derived, derived2.get_derivatives())

        # Derived 2 is a derivative of self.unit since it is a
        # derivative of derived which is a derivative of self.unit.
        self.assertIn(derived2, self.unit.get_derivatives())

        # Since derived2 is a derivative of self.unit, the inverse
        # does not hold.
        self.assertNotIn(self.unit, derived2.get_derivatives())


class IndexEncryptionTest(TestCase):
    """
    Tests for L{Index} encryption capabilities.
    """

    def setUp(self):
        """
        Establish a C{self.request} L{Request} that can be used to
        encrypt/decrypt L{EncryptedModel} instances having
        C{self.customer} as encryption ID.
        """
        with encryption_context():
            Provider.objects.create()
            self.customer = Customer()
            self.customer.save()
            User.objects.create_user(
                'testuser', 'password',
                user_type=User.CUSTOMER_USER, customer=self.customer)

        self.request = Request('testuser', 'password')
        KeyLoaderMiddleware().process_request(self.request)

        trackuser._set_customer(self.customer)

    def tearDown(self):
        trackuser._set_customer(None)
        trackuser._set_user(None)
        KeyLoaderMiddleware().process_response(self.request, None)

    def test_encryption_with_customer(self):
        """
        Test L{Index._encrypt()} and L{Index._decrypt()} for L{Index}es
        with C{customer != None}.
        """
        index = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="NOE 50/50 tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            timezone="Europe/Copenhagen",
            data_format=Index.DERIVED,
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

        self.assertEqual("NOE 50/50 tariff", index.name_plain)
        self.assertIsNone(index.name)
        index.save()
        self.assertIsNotNone(index.name)

        loaded_index = Index.objects.get(id=index.id)
        self.assertEqual("NOE 50/50 tariff", loaded_index.name_plain)

    def test_encryption_without_customer(self):
        """
        Test L{Index._encrypt()} and L{Index._decrypt()} for L{Index}es
        with C{customer is None}.
        """
        index = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="Nordpool spot-tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            timezone="Europe/Copenhagen",
            data_format=Index.SPOT,
            customer=None,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        index.save()

        loaded_index = Index.objects.get(id=index.id)
        self.assertEqual("Nordpool spot-tariff", loaded_index.name)
        self.assertEqual("Nordpool spot-tariff", loaded_index.name_plain)

    def test_get_condensed_samples(self):
        """
        """
        timezone = pytz.timezone("Europe/Copenhagen")
        index = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name="Nordpool spot-tariff",
            role=DataRoleField.ELECTRICITY_TARIFF,
            timezone=timezone,
            data_format=Index.SPOT,
            customer=None,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
        index.save()

        start_time = timezone.localize(datetime.datetime(2012, 1, 1))
        current_time = start_time
        for i in range(24 * 7):
            index.entry_set.create(
                from_timestamp=current_time,
                to_timestamp=current_time + datetime.timedelta(hours=1),
                value=Decimal(math.sin(i)))
            current_time += datetime.timedelta(hours=1)


@override_settings(ENCRYPTION_TESTMODE=True)
class PeriodTest(TestCase):
    """
    Test the Period abstract class.
    """

    def test_abstract_method(self):
        """
        Test that abstract methods raise L{NotImplementedError}.
        """
        unit = Period()
        self.assertRaises(
            NotImplementedError,
            unit.generate_entries,
            datetime.datetime(year=2012, month=11, day=19, hour=3),
            datetime.datetime(year=2012, month=11, day=19, hour=9))


@override_settings(ENCRYPTION_TESTMODE=True)
class TestStandardMonthIndex(TestCase):
    """
    Test the L{StandardMonthIndex} model.
    """

    def setUp(self):
        Provider.objects.create()
        self.customer = Customer()
        self.customer.save()
        self.unit = StandardMonthIndex.objects.create(
            customer=self.customer,
            role=DataRoleField.STANDARD_HEATING_DEGREE_DAYS,
            unit='kelvin*day',
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating,
            name_plain='standard month index',
            data_format=Index.STANDARD_MONTH_INDEX,
            timezone='Europe/Copenhagen',
            january=Decimal('1.234'),
            february=Decimal('5.678'),
            march=Decimal('9.10'),
            april=Decimal('11.12'),
            may=Decimal('13.14'),
            june=Decimal('151.617'),
            july=Decimal('181.920'),
            august=Decimal('212.223'),
            september=Decimal('242.526'),
            october=Decimal('272.829'),
            november=Decimal('3.0'),
            december=Decimal('31.32'))

    def tearDown(self):
        pass

    def test_get_samples(self):
        """
        Test the L{StandardMonthIndex.get_samples()} method
        """
        samples_iterator = iter(
            self.unit.get_samples(
                datetime.datetime(2012, 12, 24, tzinfo=pytz.utc),
                datetime.datetime(2013, 12, 25, tzinfo=pytz.utc)))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.physical_quantity, PhysicalQuantity(0, 'kelvin*day'))
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2012, 12, 24, tzinfo=pytz.utc))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2012, 12, 31, 23, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity((7 * 24 + 23) * Fraction('31.32') / (31 * 24),
                             'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 1, 31, 23, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') /
                Fraction(31 * 24) + Fraction('1.234'), 'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 2, 28, 23, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / Fraction(31 * 24) +
                Fraction('1.234') + Fraction('5.678'),
                'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 3, 31, 22, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') + Fraction('9.10'),
                'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 4, 30, 22, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') + Fraction('9.10') +
                Fraction('11.12'),
                'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 5, 31, 22, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') +
                Fraction('9.10') + Fraction('11.12') +
                Fraction('13.14'), 'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 6, 30, 22, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') + Fraction('9.10') +
                Fraction('11.12') + Fraction('13.14') + Fraction('151.617'),
                'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 7, 31, 22, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') + Fraction('9.10') +
                Fraction('11.12') + Fraction('13.14') + Fraction('151.617') +
                Fraction('181.920'),
                'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 8, 31, 22, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') + Fraction('9.10') +
                Fraction('11.12') + Fraction('13.14') + Fraction('151.617') +
                Fraction('181.920') + Fraction('212.223'),
                'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 9, 30, 22, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') + Fraction('9.10') +
                Fraction('11.12') + Fraction('13.14') + Fraction('151.617') +
                Fraction('181.920') + Fraction('212.223') +
                Fraction('242.526'),
                'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 10, 31, 23, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') + Fraction('9.10') +
                Fraction('11.12') + Fraction('13.14') + Fraction('151.617') +
                Fraction('181.920') + Fraction('212.223') +
                Fraction('242.526') + Fraction('272.829'),
                'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 11, 30, 23, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') + Fraction('9.10') +
                Fraction('11.12') + Fraction('13.14') + Fraction('151.617') +
                Fraction('181.920') + Fraction('212.223') +
                Fraction('242.526') + Fraction('272.829') + Fraction('3.0'),
                'kelvin*day'))

        sample = next(samples_iterator)
        self.assertEqual(
            sample.timestamp,
            datetime.datetime(2013, 12, 25, tzinfo=pytz.utc))
        self.assertEqual(
            sample.physical_quantity,
            PhysicalQuantity(
                (7 * 24 + 23) * Fraction('31.32') / (31 * 24) +
                Fraction('1.234') + Fraction('5.678') + Fraction('9.10') +
                Fraction('11.12') + Fraction('13.14') + Fraction('151.617') +
                Fraction('181.920') + Fraction('212.223') +
                Fraction('242.526') + Fraction('272.829') + Fraction('3.0') +
                (24 * 24 + 1) * Fraction('31.32') / (31 * 24),
                'kelvin*day'))

        with self.assertRaises(StopIteration):
            sample = next(samples_iterator)

    def test_calculate_development(self):
        """
        Test the L{StandardMonthIndex.calculate_development()} method
        """
        # Check that our calculation equals the actual fraction result.
        self.assertEqual(
            Fraction(35238237, 31000),
            (7 * 24 + 23) * Fraction('31.32') / (31 * 24) + Fraction('1.234') +
            Fraction('5.678') + Fraction('9.10') + Fraction('11.12') +
            Fraction('13.14') + Fraction('151.617') + Fraction('181.920') +
            Fraction('212.223') + Fraction('242.526') + Fraction('272.829') +
            Fraction('3.0') + (24 * 24 + 1) * Fraction('31.32') / (31 * 24))

        self.assertEqual(
            self.unit.calculate_development(
                datetime.datetime(2012, 12, 24, tzinfo=pytz.utc),
                datetime.datetime(2013, 12, 25, tzinfo=pytz.utc)),
            self.unit.create_range_sample(
                datetime.datetime(2012, 12, 24, tzinfo=pytz.utc),
                datetime.datetime(2013, 12, 25, tzinfo=pytz.utc),
                PhysicalQuantity(Fraction(35238237, 31000), self.unit.unit)))
