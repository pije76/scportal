# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import itertools

from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from model_utils import Choices

from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from gridplatform.customers.models import Customer
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.trackuser import get_customer
from gridplatform.trackuser.managers import CustomerBoundManager
from gridplatform.utils import utilitytypes
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.preferredunits import ProductionAENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionBENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionCENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionDENPIUnitConverter
from gridplatform.utils.preferredunits import ProductionEENPIUnitConverter
from gridplatform.utils.unitconversion import PhysicalQuantity
from legacy.legacy_utils.preferredunits import get_preferred_unit_converter
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import DataSeries


class ENPIReport(EncryptionCustomerFieldMixin, EncryptedModel):
    title = EncryptedCharField(_('title'), max_length=50)

    ENERGY_DRIVER_UNIT_CHOICES = Choices(
        ('person', 'person', _('person')),
        ('meter^2', 'square_meter', _('m²')),
        ('watt*kelvin^-1', _('W/K')),
        'production_a',
        'production_b',
        'production_c',
        'production_d',
        'production_e')

    energy_driver_unit = BuckinghamField(
        _('energy driver type'),
        choices=ENERGY_DRIVER_UNIT_CHOICES)

    objects = CustomerBoundManager()

    def __unicode__(self):
        return self.title_plain

    @cached_property
    def energy_unit(self):
        """
        @precondition: At least one L{ENPIUseArea} with at least one
        L{ConsumptionMeasurementPoint} must exist for this C{ENPIReport}
        """
        return DataSeries.objects.filter(
            role=DataRoleField.CONSUMPTION,
            graph__hidden=False,
            graph__collection__in=ConsumptionMeasurementPoint.objects.filter(
                enpiusearea__report_id=self.id).values_list(
                'id', flat=True))[0:1].get().unit

    @cached_property
    def energy_driver_role(self):
        """
        @precondition: At least one L{ENPIUseArea} must exist for this
        C{ENPIReport}
        """
        return DataSeries.objects.filter(
            enpiusearea__report_id=self.id)[0:1].get().role

    @property
    def enpi_role(self):
        if self.energy_driver_role == DataRoleField.EMPLOYEES:
            return DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES
        elif self.energy_driver_role == DataRoleField.AREA:
            return DataRoleField.CONSUMPTION_UTILIZATION_AREA
        elif self.energy_driver_role == DataRoleField.PRODUCTION:
            return DataRoleField.PRODUCTION_ENPI
        elif self.energy_driver_role == DataRoleField.HEATING_DEGREE_DAYS:
            return DataRoleField.HEAT_LOSS_COEFFICIENT

        raise ValueError(
            'An ENPI role for energi driver role %d is not defined' %
            self.energy_driver_role)

    @property
    def enpi_unit_converter(self):
        """
        @precondition: At least one L{ENPIUseArea} must exist for this
        C{ENPIReport}

        @bug: Assumes utility type being electricity.  Utility type may infact
        be mixed, but in particular, it may not need to be energy at some point
        in the future.
        """
        if self.energy_driver_role == DataRoleField.EMPLOYEES:
            return get_preferred_unit_converter(
                DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
                customer=self.customer)
        elif self.energy_driver_role == DataRoleField.AREA:
            return get_preferred_unit_converter(
                DataRoleField.CONSUMPTION_UTILIZATION_AREA,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
                customer=self.customer)
        elif self.energy_driver_role == DataRoleField.PRODUCTION:
            energy_unit_converter = get_preferred_unit_converter(
                DataRoleField.CONSUMPTION,
                utilitytypes.OPTIONAL_METER_CHOICES.electricity)
            if self.energy_driver_unit == 'production_a':
                return ProductionAENPIUnitConverter(
                    energy_unit_converter.physical_unit)
            elif self.energy_driver_unit == 'production_b':
                return ProductionBENPIUnitConverter(
                    energy_unit_converter.physical_unit)
            elif self.energy_driver_unit == 'production_c':
                return ProductionCENPIUnitConverter(
                    energy_unit_converter.physical_unit)
            elif self.energy_driver_unit == 'production_d':
                return ProductionDENPIUnitConverter(
                    energy_unit_converter.physical_unit)
            elif self.energy_driver_unit == 'production_e':
                return ProductionEENPIUnitConverter(
                    energy_unit_converter.physical_unit)
        elif self.energy_driver_role == DataRoleField.HEATING_DEGREE_DAYS:
            return get_preferred_unit_converter(
                DataRoleField.HEAT_LOSS_COEFFICIENT)

        raise ValueError(
            'An ENPI unit converter for energi driver role %d and energy '
            'driver unit %s is not defined' %
            (self.energy_driver_role, self.energy_driver_unit))

    @property
    def enpi_unit(self):
        """
        @precondition: At least one L{ENPIUseArea} must exist for this
        C{ENPIReport}
        """
        return self.enpi_unit_converter.physical_unit

    @classmethod
    def get_energy_driver_choices(cls):
        return itertools.chain(
            (
                (cls.ENERGY_DRIVER_UNIT_CHOICES.person,
                 _('person')),
                (cls.ENERGY_DRIVER_UNIT_CHOICES.square_meter,
                 _('m²')),
            ),
            get_customer().get_production_unit_choices(),
            (('kelvin*day', _('degree days')),))


class ReportCustomerBoundManager(CustomerBoundManager):
    _field = 'report__customer'


class ENPIUseArea(EncryptedModel):
    report = models.ForeignKey(ENPIReport)
    name = EncryptedCharField(max_length=50)
    measurement_points = models.ManyToManyField(ConsumptionMeasurementPoint)
    energy_driver = models.ForeignKey(DataSeries)

    objects = ReportCustomerBoundManager()

    def clean(self):
        if self.energy_driver_id and self.report and \
                not PhysicalQuantity.compatible_units(
                    self.energy_driver.unit,
                    self.report.energy_driver_unit):
            raise ValidationError(
                _(
                    'Energy driver with unit "%s" is invalid for this ENPI '
                    'report with unit "%s".' % (
                        self.energy_driver.unit,
                        self.report.energy_driver_unit)))

    def get_encryption_id(self):
        if self.report_id:
            return (Customer, self.report.customer_id)
        else:
            return (Customer, None)

    def __unicode__(self):
        return self.name_plain
