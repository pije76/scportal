# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext as _

from gridplatform.customers.models import Customer
from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.utils.units import UNIT_CHOICES
from gridplatform.trackuser.managers import CustomerBoundManager
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.units import CURRENCY_CHOICES
from gridplatform.utils import utilitytypes
from legacy.measurementpoints.fields import DataRoleField
from legacy.legacy_utils.preferredunits import get_preferred_unit_converter
from legacy.legacy_utils import get_customer_preferred_unit_attribute_name


class EnergyUseReport(EncryptionCustomerFieldMixin, EncryptedModel):
    """
    A report presenting an overview of areas of energy use, their consumptions
    and their costs.

    @seealso: L{EnergyUseArea}
    """
    title = EncryptedCharField(max_length=50)
    currency_unit = BuckinghamField(_('currency'), choices=CURRENCY_CHOICES,
                                    default='currency_dkk')
    utility_type = models.IntegerField(
        _('utility type'), choices=utilitytypes.METER_CHOICES)
    main_measurement_points = models.ManyToManyField(
        ConsumptionMeasurementPoint, blank=True, null=True)

    objects = CustomerBoundManager()

    def __unicode__(self):
        return self.title_plain

    def get_preferred_unit_display(self):
        return get_preferred_unit_converter(
            DataRoleField.CONSUMPTION, self.utility_type).get_display_unit()

    def get_preferred_unit(self):
        return getattr(
            self.customer,
            get_customer_preferred_unit_attribute_name(
                self.customer, DataRoleField.CONSUMPTION, self.utility_type))

    def get_preferred_co2_emission_unit_display(self):
        return dict(UNIT_CHOICES)[self.get_preferred_co2_emission_unit()]

    def get_preferred_co2_emission_unit(self):
        return 'kilogram'

    def get_utility_type_report_name(self):
        if self.utility_type == utilitytypes.METER_CHOICES.electricity:
            return _('Electricity Use Report')
        elif self.utility_type == utilitytypes.METER_CHOICES.water:
            return _('Water Use Report')
        elif self.utility_type == utilitytypes.METER_CHOICES.gas:
            return _('Gas Use Report')
        elif self.utility_type == utilitytypes.METER_CHOICES.district_heating:
            return _('Heat Use Report')
        elif self.utility_type == utilitytypes.METER_CHOICES.oil:
            return _('Oil Use Report')
        else:
            raise IndexError()

    def get_all_measurementpoint_ids(self):
        """
        Returns a list of ids for all the measurement points
        used in the report.
        """
        mps = ConsumptionMeasurementPoint.objects.filter(
            energyusearea__report=self).values_list('id', flat=True)

        return list(mps) + [mp.id for mp in self.main_measurement_points.all()]


class ReportCustomerBoundManager(CustomerBoundManager):
    _field = 'report__customer'


class EnergyUseArea(EncryptedModel):
    """
    C{EnergyUseArea} is an area of energy use included in an
    L{EnergyUseReport}.  In particular, an area of energy use has a C{name} and
    aggregates a number of C{measurement_points}.
    """
    report = models.ForeignKey(EnergyUseReport)
    name = EncryptedCharField(max_length=50)
    measurement_points = models.ManyToManyField(ConsumptionMeasurementPoint)

    objects = ReportCustomerBoundManager()

    def __unicode__(self):
        return self.name_plain

    def get_encryption_id(self):
        if self.report_id and self.report.customer_id:
            customer_id = self.report.customer_id
        else:
            customer_id = None
        return (Customer, customer_id)
