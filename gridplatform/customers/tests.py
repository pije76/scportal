# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db.models import Model
from django.forms import ModelForm
from django.test import TestCase

from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.units import preferred_unit_bases

from .fields import UnitNormalisingField
from .models import Customer


class ModelWithUnitNormalisingField(Model):
    field = UnitNormalisingField(
        preferred_unit_getter=lambda obj: 'kilowatt')


class ModelWithUnitNormalisingFieldForm(ModelForm):
    class Meta:
        model = ModelWithUnitNormalisingField


class TestUnitNormalisingField(TestCase):
    def test_form_input(self):
        form = ModelWithUnitNormalisingFieldForm({'field': '5'})
        self.assertTrue(form.is_valid())
        obj = form.save(commit=False)
        preferred_unit_value = float(
            PhysicalQuantity(5, 'kilowatt').convert(
                preferred_unit_bases['kilowatt']))
        self.assertEqual(obj.field, preferred_unit_value)

    def test_form_output(self):
        preferred_unit_value = float(
            PhysicalQuantity('140.2', 'kilowatt').convert(
                preferred_unit_bases['kilowatt']))
        obj = ModelWithUnitNormalisingField(field=preferred_unit_value)
        self.assertEqual(obj.field, preferred_unit_value)
        form = ModelWithUnitNormalisingFieldForm(instance=obj)
        self.assertEqual(form.initial['field'], 140.2)

    def test_save_load(self):
        obj = ModelWithUnitNormalisingField(field=123456)
        obj.save()
        loaded = ModelWithUnitNormalisingField.objects.get(id=obj.id)
        self.assertEqual(loaded.field, 123456)


class CustomerGetProductionUnitChoicesTest(TestCase):
    def setUp(self):
        self.customer = Customer()

    def test_no_production_units(self):
        production_unit_choices = self.customer.get_production_unit_choices()

        self.assertFalse(hasattr(production_unit_choices, 'production_a'))
        self.assertFalse(hasattr(production_unit_choices, 'production_b'))
        self.assertFalse(hasattr(production_unit_choices, 'production_c'))
        self.assertFalse(hasattr(production_unit_choices, 'production_d'))
        self.assertFalse(hasattr(production_unit_choices, 'production_e'))

    def test_one_production_unit(self):
        self.customer.production_b_unit_plain = 'barrels of coffee'
        production_unit_choices = self.customer.get_production_unit_choices()

        self.assertFalse(hasattr(production_unit_choices, 'production_a'))
        self.assertTrue(hasattr(production_unit_choices, 'production_b'))
        self.assertFalse(hasattr(production_unit_choices, 'production_c'))
        self.assertFalse(hasattr(production_unit_choices, 'production_d'))
        self.assertFalse(hasattr(production_unit_choices, 'production_e'))

    def test_multiple_production_units(self):
        self.customer.production_b_unit_plain = 'barrels of coffee'
        self.customer.production_e_unit_plain = 'tonnes of cake'
        production_unit_choices = self.customer.get_production_unit_choices()

        self.assertFalse(hasattr(production_unit_choices, 'production_a'))
        self.assertTrue(hasattr(production_unit_choices, 'production_b'))
        self.assertFalse(hasattr(production_unit_choices, 'production_c'))
        self.assertFalse(hasattr(production_unit_choices, 'production_d'))
        self.assertTrue(hasattr(production_unit_choices, 'production_e'))
