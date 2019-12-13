# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from fractions import Fraction

from django.test import TestCase
from django.test.utils import override_settings

from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import utilitytypes
from gridplatform.providers.models import Provider
from gridplatform.customers.models import Customer
from gridplatform.datasequences.models import NonaccumulationDataSequence
from gridplatform.utils.preferredunits import EfficiencyUnitConverter
from legacy.measurementpoints.fields import DataRoleField
from legacy.datasequence_adapters.models import NonaccumulationAdapter

from .models import EfficiencyLink
from .models import EfficiencyMeasurementPoint


class EfficiencyLinkTest(TestCase):
    def setUp(self):
        self.link = EfficiencyLink()

    def test_get_preferred_unit_converter(self):
        self.assertIsInstance(
            self.link.get_preferred_unit_converter(),
            EfficiencyUnitConverter)


@override_settings(ENCRYPTION_TESTMODE=True)
class EfficiencyMeasurementPointTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()

        self.datasequence = NonaccumulationDataSequence.objects.create(
            customer=self.customer,
            unit='millibar')

        self.mp = EfficiencyMeasurementPoint(
            name_plain='Æffiktivitætsmålepønkt',
            customer=self.customer)
        self.mp.input_configuration = NonaccumulationAdapter.objects.create(
            unit='millibar',
            role=DataRoleField.EFFICIENCY,
            customer=self.customer,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.unknown,
            datasequence=self.datasequence)
        self.mp.save()

    def test_graph_has_efficiencylink(self):
        self.assertIsInstance(
            self.mp.graph_set.get().dataseries_set.get().subclass_instance,
            EfficiencyLink)

    def test_resave_doesnt_crash(self):
        self.mp.save()
