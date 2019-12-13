# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module contains tests for the manage_indexes Django app.
"""

import json
from collections import namedtuple

from django.test import TestCase
from django.test.utils import override_settings

from gridplatform import trackuser
from gridplatform.encryption.shell import Request
from gridplatform.encryption.middleware import KeyLoaderMiddleware
from legacy.indexes.models import Index
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from gridplatform.utils import choices_extract_python_identifier
from gridplatform.users.models import User


@override_settings(ENCRYPTION_TESTMODE=True)
class ViewTest(TestCase):
    """
    Tests for the view module.
    """
    fixtures = ["manage_indexes_test.json"]

    def setUp(self):
        """
        Setup test fixture as if we are logged in as some user called
        super.
        """
        self.client.post('/login/', {"username": "super",
                                     'password': "123"})
        self.user = User.objects.get(
            id=self.client.session["_auth_user_id"])
        self.customer = self.user.customer
        trackuser._set_customer(self.customer)

        self.request = Request('super', '123')
        KeyLoaderMiddleware().process_request(self.request)

        Index_map = namedtuple('Index_map', 'role, utility_types')
        self.index_matrix = (
            Index_map(
                role='tariff',
                utility_types=('electricity', 'water', 'gas',
                               'district_heating', 'oil')),
            Index_map(role='employees',
                      utility_types=('unknown',)),
            Index_map(role='area',
                      utility_types=('unknown',)))

    def tearDown(self):
        KeyLoaderMiddleware().process_response(self.request, None)
        trackuser._set_customer(None)

    def get_all_indexes(self):
        """
        This method creates all possible index types and returns
        a list with the created objects.
        """
        index_el = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="electricity index",
            role=DataRoleField.ELECTRICITY_TARIFF,
            data_format=Index.SEASONS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            timezone='Europe/Copenhagen')
        index_el.save()

        index_water = Index(
            unit="currency_dkk*liter^-1",
            name_plain="water index",
            role=DataRoleField.WATER_TARIFF,
            data_format=Index.SEASONS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water,
            timezone='Europe/Copenhagen')
        index_water.save()

        index_gas = Index(
            unit="currency_dkk*liter^-1",
            name_plain="gas index",
            role=DataRoleField.GAS_TARIFF,
            data_format=Index.SEASONS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas,
            timezone='Europe/Copenhagen')
        index_gas.save()

        index_heat = Index(
            unit="currency_dkk*kilowatt^-1*hour^-1",
            name_plain="heat index",
            role=DataRoleField.HEAT_TARIFF,
            data_format=Index.SEASONS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating,
            timezone='Europe/Copenhagen')
        index_heat.save()

        index_oil = Index(
            unit="currency_dkk*liter^-1",
            name_plain="oil index",
            role=DataRoleField.OIL_TARIFF,
            data_format=Index.SEASONS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.oil,
            timezone='Europe/Copenhagen')
        index_oil.save()

        index_area = Index(
            unit="meter^2",
            name_plain="area index",
            role=DataRoleField.CONSUMPTION_UTILIZATION_AREA,
            data_format=Index.SEASONS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            timezone='Europe/Copenhagen')
        index_area.save()

        index_employee = Index(
            unit="person",
            name_plain="employees index",
            role=DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
            data_format=Index.SEASONS,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            timezone='Europe/Copenhagen')
        index_employee.save()

        return (index_el, index_water, index_gas, index_heat,
                index_oil, index_area, index_employee)

    def test_list_json(self):
        """
        Test the C{list_json()} view.
        """
        response = self.client.get("/indexes/list-json/")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.content, "")
        result = json.loads(response.content)
        self.assertIn("total", result)
        self.assertIn("data", result)

    def test_list(self):
        """
        Test the C{list()} view.
        """
        self.assertEqual(self.client.get("/indexes/").status_code, 200)

    def test_form_create_derived(self):
        """
        Test the C{form()} view when creating a derived index.
        Only tariff indexes can be derived indexes.
        """
        for index in [index for index in self.get_all_indexes()
                      if index.role in DataRoleField.TARIFFS]:
            utility_type_string = choices_extract_python_identifier(
                utilitytypes.METER_CHOICES, index.utility_type)
            response = self.client.get(
                "/indexes/form/derived/tariff/%s" % utility_type_string)
            self.assertContains(response, index.name_plain)

            # Creating derived index with valid input
            response = self.client.post(
                "/indexes/form/derived/tariff/%s" % utility_type_string,
                {
                    "name": "Derived index",
                    "collection": "",
                    'unit': index.unit,
                    "timezone": "Europe/Copenhagen",
                    "derivedindexperiod_set-TOTAL_FORMS": "1",
                    "derivedindexperiod_set-INITIAL_FORMS": "0",
                    "derivedindexperiod_set-MAX_NUM_FORMS": "1000",
                    "derivedindexperiod_set-0-id": "",
                    "derivedindexperiod_set-0-index": "",
                    "derivedindexperiod_set-0-from_date": "2013-05-01",
                    "derivedindexperiod_set-0-other_index": str(index.id),
                    "derivedindexperiod_set-0-coefficient": "1.000",
                    "derivedindexperiod_set-0-constant": "2",
                    "derivedindexperiod_set-0-roof": "3",
                    "save_return": "Save and return to list"})
            self.assertNotContains(response, 'error', status_code=302)

            # Creating derived index with invalid input
            response = self.client.post(
                "/indexes/form/derived/tariff/%s" % utility_type_string,
                {
                    "name": "Yet another derived index",
                    "collection": "",
                    "timezone": "Europe/Copenhagen",
                    "derivedindexperiod_set-TOTAL_FORMS": "1",
                    "derivedindexperiod_set-INITIAL_FORMS": "0",
                    "derivedindexperiod_set-MAX_NUM_FORMS": "1000",
                    "derivedindexperiod_set-0-id": "",
                    "derivedindexperiod_set-0-index": "",
                    "derivedindexperiod_set-0-from_date": "2013-05-01",
                    "derivedindexperiod_set-0-other_index": str(index.id),
                    "derivedindexperiod_set-0-coefficient": "1.000",
                    "derivedindexperiod_set-0-constant": "2",
                    "derivedindexperiod_set-0-roof": "3",
                    "save_return": "Save and return to list"})
            self.assertContains(response, 'error')

    def test_form_update_derived(self):
        """
        Test the C{form()} view when updating a derived index.
        Only derived tariff indexes can be updated.
        """
        indexes = []
        for base_index in [base_index for base_index in self.get_all_indexes()
                           if base_index.role in DataRoleField.TARIFFS]:

            derived_index = Index(
                unit=base_index.unit,
                name_plain="Derived " + base_index.name_plain,
                role=base_index.role,
                data_format=Index.DERIVED,
                customer=self.customer,
                utility_type=base_index.utility_type,
                timezone='Europe/Copenhagen')
            derived_index.save()
            indexes.append((base_index, derived_index))

        for base_index, derived_index in indexes:
            self.assertContains(
                self.client.get(derived_index.get_absolute_url()),
                derived_index.name_plain)

            # Updating derived index with valid input
            response = self.client.post(
                derived_index.get_absolute_url(),
                {
                    "name": "Altered",
                    "timezone": "Europe/Copenhagen",
                    "derivedindexperiod_set-TOTAL_FORMS": "1",
                    "derivedindexperiod_set-INITIAL_FORMS": "0",
                    "derivedindexperiod_set-MAX_NUM_FORMS": "",
                    "derivedindexperiod_set-0-from_date": "01.11.2012",
                    "derivedindexperiod_set-0-other_index": "%d" % (
                        base_index.id),
                    "derivedindexperiod_set-0-coefficient": "1.00",
                    "derivedindexperiod_set-0-constant": "0.12",
                    "derivedindexperiod_set-0-roof": "0.70",
                    "derivedindexperiod_set-0-id": "",
                    "derivedindexperiod_set-0-index": str(derived_index.id),
                    "save_return": "Save and return to list"})
            self.assertNotContains(response, 'error', status_code=302)

            # Updating derived index with 'save' button
            response = self.client.post(
                derived_index.get_absolute_url(),
                {
                    "name": "Altered",
                    "timezone": "Europe/Copenhagen",
                    "derivedindexperiod_set-TOTAL_FORMS": "1",
                    "derivedindexperiod_set-INITIAL_FORMS": "0",
                    "derivedindexperiod_set-MAX_NUM_FORMS": "",
                    "derivedindexperiod_set-0-from_date": "01.11.2012",
                    "derivedindexperiod_set-0-other_index": "%d" % (
                        base_index.id),
                    "derivedindexperiod_set-0-coefficient": "1.00",
                    "derivedindexperiod_set-0-constant": "0.12",
                    "derivedindexperiod_set-0-roof": "0.70",
                    "derivedindexperiod_set-0-id": "",
                    "derivedindexperiod_set-0-index": str(derived_index.id),
                    "save": "Save"})
            self.assertNotContains(response, 'error', status_code=302)

            # Updating derived index with invalid other index
            response = self.client.post(
                derived_index.get_absolute_url(),
                {
                    "name": "Altered",
                    "timezone": "Europe/Copenhagen",
                    "derivedindexperiod_set-TOTAL_FORMS": "1",
                    "derivedindexperiod_set-INITIAL_FORMS": "0",
                    "derivedindexperiod_set-MAX_NUM_FORMS": "",
                    "derivedindexperiod_set-0-from_date": "01.11.2012",
                    "derivedindexperiod_set-0-other_index": "%d" % (
                        derived_index.id),
                    "derivedindexperiod_set-0-coefficient": "1.00",
                    "derivedindexperiod_set-0-constant": "0.12",
                    "derivedindexperiod_set-0-roof": "0.70",
                    "derivedindexperiod_set-0-id": "",
                    "derivedindexperiod_set-0-index": str(derived_index.id),
                    "save_return": "Save and return to list"})
            self.assertContains(response, 'error')

    def test_form_create_seasons(self):
        """
        Create seasons indexes with all index combinations.
        """
        for index in self.index_matrix:
            for utility_type in index.utility_types:
                self.assertEqual(self.client.get(
                    "/indexes/form/seasons/%s/%s"
                    % (index.role, utility_type)).status_code, 200)

                if utility_type in ('electricity', 'district_heating'):
                    unit = 'currency_eur*kilowatt^-1*hour^-1'
                elif utility_type in ('water', 'gas', 'oil'):
                    unit = 'currency_dkk*meter^-3'
                else:
                    unit = 'some string that certainly is not used'

                response = self.client.post(
                    "/indexes/form/seasons/%s/%s" % (
                        index.role, utility_type),
                    {
                        "name": "Test index",
                        "collection": "",
                        'unit': unit,
                        "timezone": "Europe/Copenhagen",
                        "seasonindexperiod_set-TOTAL_FORMS": "1",
                        "seasonindexperiod_set-INITIAL_FORMS": "0",
                        "seasonindexperiod_set-MAX_NUM_FORMS": "1000",
                        "seasonindexperiod_set-0-id": "",
                        "seasonindexperiod_set-0-index": "",
                        "seasonindexperiod_set-0-from_date": "2013-08-02",
                        "seasonindexperiod_set-0-value_at_hour_0": "1",
                        "seasonindexperiod_set-0-value_at_hour_1": "1",
                        "seasonindexperiod_set-0-value_at_hour_2": "1",
                        "seasonindexperiod_set-0-value_at_hour_3": "1",
                        "seasonindexperiod_set-0-value_at_hour_4": "1",
                        "seasonindexperiod_set-0-value_at_hour_5": "1",
                        "seasonindexperiod_set-0-value_at_hour_6": "1",
                        "seasonindexperiod_set-0-value_at_hour_7": "1",
                        "seasonindexperiod_set-0-value_at_hour_8": "1",
                        "seasonindexperiod_set-0-value_at_hour_9": "1",
                        "seasonindexperiod_set-0-value_at_hour_10": "1",
                        "seasonindexperiod_set-0-value_at_hour_11": "1",
                        "seasonindexperiod_set-0-value_at_hour_12": "1",
                        "seasonindexperiod_set-0-value_at_hour_13": "1",
                        "seasonindexperiod_set-0-value_at_hour_14": "1",
                        "seasonindexperiod_set-0-value_at_hour_15": "1",
                        "seasonindexperiod_set-0-value_at_hour_16": "1",
                        "seasonindexperiod_set-0-value_at_hour_17": "1",
                        "seasonindexperiod_set-0-value_at_hour_18": "1",
                        "seasonindexperiod_set-0-value_at_hour_19": "1",
                        "seasonindexperiod_set-0-value_at_hour_20": "1",
                        "seasonindexperiod_set-0-value_at_hour_21": "1",
                        "seasonindexperiod_set-0-value_at_hour_22": "1",
                        "seasonindexperiod_set-0-value_at_hour_23": "1",
                        "save_return": "Save and return to list"})
                self.assertNotContains(response, 'error', status_code=302)

    def test_form_update_seasons(self):
        """
        Update seasons indexes with all roles.
        """
        indexes = self.get_all_indexes()

        for index in indexes:
            assert index.data_format == Index.SEASONS

            self.assertEqual(
                self.client.get(index.get_absolute_url()).status_code,
                200)

            # Update the form with valid data
            response = self.client.post(
                index.get_absolute_url(), {
                    "name": "New name",
                    "collection": "",
                    "seasonindexperiod_set-TOTAL_FORMS": "1",
                    "seasonindexperiod_set-INITIAL_FORMS": "0",
                    "seasonindexperiod_set-MAX_NUM_FORMS": "1000",
                    "seasonindexperiod_set-0-id": "",
                    "seasonindexperiod_set-0-index": "",
                    "seasonindexperiod_set-0-from_date": "2012-01-01",
                    "seasonindexperiod_set-0-value_at_hour_0": "2",
                    "seasonindexperiod_set-0-value_at_hour_1": "2",
                    "seasonindexperiod_set-0-value_at_hour_2": "2",
                    "seasonindexperiod_set-0-value_at_hour_3": "2",
                    "seasonindexperiod_set-0-value_at_hour_4": "2",
                    "seasonindexperiod_set-0-value_at_hour_5": "2",
                    "seasonindexperiod_set-0-value_at_hour_6": "2",
                    "seasonindexperiod_set-0-value_at_hour_7": "2",
                    "seasonindexperiod_set-0-value_at_hour_8": "2",
                    "seasonindexperiod_set-0-value_at_hour_9": "2",
                    "seasonindexperiod_set-0-value_at_hour_10": "2",
                    "seasonindexperiod_set-0-value_at_hour_11": "2",
                    "seasonindexperiod_set-0-value_at_hour_12": "2",
                    "seasonindexperiod_set-0-value_at_hour_13": "2",
                    "seasonindexperiod_set-0-value_at_hour_14": "2",
                    "seasonindexperiod_set-0-value_at_hour_15": "2",
                    "seasonindexperiod_set-0-value_at_hour_16": "2",
                    "seasonindexperiod_set-0-value_at_hour_17": "2",
                    "seasonindexperiod_set-0-value_at_hour_18": "2",
                    "seasonindexperiod_set-0-value_at_hour_19": "2",
                    "seasonindexperiod_set-0-value_at_hour_20": "2",
                    "seasonindexperiod_set-0-value_at_hour_21": "2",
                    "seasonindexperiod_set-0-value_at_hour_22": "2",
                    "seasonindexperiod_set-0-value_at_hour_23": "2",
                    "save_return": "Save and return to list"})
            self.assertNotContains(response, 'error', status_code=302)

            # Update the form with valid data, using 'save' button
            response = self.client.post(
                index.get_absolute_url(), {
                    "name": "New name",
                    "collection": "",
                    "timezone": "Europe/Copenhagen",
                    "seasonindexperiod_set-TOTAL_FORMS": "1",
                    "seasonindexperiod_set-INITIAL_FORMS": "0",
                    "seasonindexperiod_set-MAX_NUM_FORMS": "1000",
                    "seasonindexperiod_set-0-id": "",
                    "seasonindexperiod_set-0-index": "",
                    "seasonindexperiod_set-0-from_date": "2012-01-01",
                    "seasonindexperiod_set-0-value_at_hour_0": "2",
                    "seasonindexperiod_set-0-value_at_hour_1": "2",
                    "seasonindexperiod_set-0-value_at_hour_2": "2",
                    "seasonindexperiod_set-0-value_at_hour_3": "2",
                    "seasonindexperiod_set-0-value_at_hour_4": "2",
                    "seasonindexperiod_set-0-value_at_hour_5": "2",
                    "seasonindexperiod_set-0-value_at_hour_6": "2",
                    "seasonindexperiod_set-0-value_at_hour_7": "2",
                    "seasonindexperiod_set-0-value_at_hour_8": "2",
                    "seasonindexperiod_set-0-value_at_hour_9": "2",
                    "seasonindexperiod_set-0-value_at_hour_10": "2",
                    "seasonindexperiod_set-0-value_at_hour_11": "2",
                    "seasonindexperiod_set-0-value_at_hour_12": "2",
                    "seasonindexperiod_set-0-value_at_hour_13": "2",
                    "seasonindexperiod_set-0-value_at_hour_14": "2",
                    "seasonindexperiod_set-0-value_at_hour_15": "2",
                    "seasonindexperiod_set-0-value_at_hour_16": "2",
                    "seasonindexperiod_set-0-value_at_hour_17": "2",
                    "seasonindexperiod_set-0-value_at_hour_18": "2",
                    "seasonindexperiod_set-0-value_at_hour_19": "2",
                    "seasonindexperiod_set-0-value_at_hour_20": "2",
                    "seasonindexperiod_set-0-value_at_hour_21": "2",
                    "seasonindexperiod_set-0-value_at_hour_22": "2",
                    "seasonindexperiod_set-0-value_at_hour_23": "2",
                    "save": "Save"})
            self.assertNotContains(response, 'error', status_code=302)

            # Update the form with invalid data
            response = self.client.post(
                index.get_absolute_url(), {
                    "name": "New name",
                    "collection": "",
                    "seasonindexperiod_set-TOTAL_FORMS": "1",
                    "seasonindexperiod_set-INITIAL_FORMS": "0",
                    "seasonindexperiod_set-MAX_NUM_FORMS": "1000",
                    "seasonindexperiod_set-0-id": "",
                    "seasonindexperiod_set-0-index": "",
                    "seasonindexperiod_set-0-from_date": "2012-01-01",
                    "seasonindexperiod_set-0-value_at_hour_0": "a",
                    "seasonindexperiod_set-0-value_at_hour_1": "a",
                    "seasonindexperiod_set-0-value_at_hour_2": "a",
                    "seasonindexperiod_set-0-value_at_hour_3": "a",
                    "seasonindexperiod_set-0-value_at_hour_4": "a",
                    "seasonindexperiod_set-0-value_at_hour_5": "a",
                    "seasonindexperiod_set-0-value_at_hour_6": "a",
                    "seasonindexperiod_set-0-value_at_hour_7": "a",
                    "seasonindexperiod_set-0-value_at_hour_8": "a",
                    "seasonindexperiod_set-0-value_at_hour_9": "a",
                    "seasonindexperiod_set-0-value_at_hour_10": "a",
                    "seasonindexperiod_set-0-value_at_hour_11": "a",
                    "seasonindexperiod_set-0-value_at_hour_12": "a",
                    "seasonindexperiod_set-0-value_at_hour_13": "a",
                    "seasonindexperiod_set-0-value_at_hour_14": "a",
                    "seasonindexperiod_set-0-value_at_hour_15": "a",
                    "seasonindexperiod_set-0-value_at_hour_16": "a",
                    "seasonindexperiod_set-0-value_at_hour_17": "a",
                    "seasonindexperiod_set-0-value_at_hour_18": "a",
                    "seasonindexperiod_set-0-value_at_hour_19": "a",
                    "seasonindexperiod_set-0-value_at_hour_20": "a",
                    "seasonindexperiod_set-0-value_at_hour_21": "a",
                    "seasonindexperiod_set-0-value_at_hour_22": "a",
                    "seasonindexperiod_set-0-value_at_hour_23": "a",
                    "save_return": "Save and return to list"})
            self.assertContains(response, 'error')
