# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django import forms
from south.modelsinspector import add_introspection_rules

from gridplatform.utils.units import preferred_unit_bases
from gridplatform.utils.unitconversion import PhysicalQuantity


class UnitNormalisingField(models.BigIntegerField):
    """
    A model field which normalises data from a customer preferred input unit
    from input forms to the corresponding "base" unit for storage and access
    from code.

    I.e. when accessing a C{UnitNormalisingField} from code, the value held is
    in C{preferred_unit_bases[preferred_unit_getter(model)]}, where
    C{preferred_unit_getter()} is an argument for L{__init__()}, and C{model}
    is the model instance that this field is assigned to.
    """

    def __init__(self, *args, **kwargs):
        """
        @param preferred_unit_getter: Callable which, given the model object
        instance that this field is used with, will return the relevant
        Buckingham preferred unit.
        """
        self.preferred_unit_getter = kwargs.pop('preferred_unit_getter', None)
        super(UnitNormalisingField, self).__init__(*args, **kwargs)

    # NOTE: value_from_object is used to initialise form; serialising uses
    # value_to_string(), DB uses get_prep_value() (and others); we only convert
    # for forms...
    def value_from_object(self, obj):
        """
        Get field value in customer preferred unit.
        """
        normalised = super(UnitNormalisingField, self).value_from_object(obj)
        if normalised is not None:
            preferred_unit = self.preferred_unit_getter(obj)
            if preferred_unit is not None:
                base_unit = preferred_unit_bases[preferred_unit]
                data = float(
                    PhysicalQuantity(normalised, base_unit).convert(
                        preferred_unit))
            else:
                data = None
        else:
            data = None
        return data

    def save_form_data(self, instance, data):
        """
        Normalise and store field value from customer preferred unit.
        """
        if data is not None:
            preferred_unit = self.preferred_unit_getter(instance)
            base_unit = preferred_unit_bases[preferred_unit]
            normalised = int(PhysicalQuantity(
                data, preferred_unit).convert(base_unit))
        else:
            normalised = None
        super(UnitNormalisingField, self).save_form_data(instance, normalised)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.FloatField}
        defaults.update(kwargs)
        return models.Field.formfield(self, **defaults)


add_introspection_rules([], [
    "^gridplatform\.customers\.fields\.UnitNormalisingField"])
