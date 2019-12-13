# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytz

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from gridplatform.utils import units
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import condense
from gridplatform.utils.preferredunits import PhysicalUnitConverter
from gridplatform.datasources.models import DataSource
from gridplatform.datasequences.models import CurrencyUnitMixin
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes

from .index import Index


class DataSourceIndexAdapter(CurrencyUnitMixin, Index):
    datasource = models.ForeignKey(
        DataSource, limit_choices_to=models.Q(
            unit__in=units.TARIFF_BASE_UNITS +
            units.CO2_CONVERSION_BASE_UNITS))

    class Meta:
        verbose_name = _('data source index adapter')
        verbose_name_plural = _('data source index adapters')
        app_label = 'indexes'

    sample_resolution = None

    def __unicode__(self):
        return '%s (%s)' % (
            self.datasource,
            self.get_preferred_unit_converter().get_display_unit())

    def _get_samples(self, from_timestamp, to_timestamp):
        assert self.sample_resolution is not None
        rawdata = self.datasource.rawdata_set.filter(
            timestamp__gte=from_timestamp,
            timestamp__lt=to_timestamp).order_by(
                'timestamp').values_list('timestamp', 'value')
        for timestamp, value in rawdata:
            yield self.create_range_sample(
                timestamp,
                timestamp + self.sample_resolution,
                PhysicalQuantity(value, self.datasource.unit))


class DataSourceTariffAdapter(DataSourceIndexAdapter):
    class Meta:
        verbose_name = _('data source tariff adapter')
        verbose_name_plural = _('data source tariff adapters')
        proxy = True

    sample_resolution = condense.HOURS

    def get_preferred_unit_converter(self):
        ENERGY_TARIFF_UNIT = self.currency_unit + '*kilowatt^-1*hour^-1'
        VOLUME_TARIFF_UNIT = self.currency_unit + '*meter^-3'

        if PhysicalQuantity.compatible_units(self.unit, ENERGY_TARIFF_UNIT):
            return PhysicalUnitConverter(ENERGY_TARIFF_UNIT)
        else:
            assert PhysicalQuantity.compatible_units(
                self.unit, VOLUME_TARIFF_UNIT)
            return PhysicalUnitConverter(VOLUME_TARIFF_UNIT)


class DataSourceCo2ConversionAdapter(DataSourceIndexAdapter):
    class Meta:
        verbose_name = _('data source CO₂ conversion adapter')
        verbose_name_plural = _('data source CO₂ conversion adapters')
        proxy = True

    sample_resolution = condense.FIVE_MINUTES


@receiver(post_save)
def autocreate_datasourceadapter(
        sender, instance, created, raw=False, **kwargs):
    if not issubclass(sender, DataSource):
        return

    if created and not raw:
        if any(PhysicalQuantity.compatible_units(instance.unit, tariff_unit)
               for tariff_unit in units.ENERGY_TARIFF_BASE_UNITS):
            # create energy tariff adapters
            DataSourceTariffAdapter.objects.create(
                data_format=DataSourceTariffAdapter.DATASOURCEADAPTER,
                datasource=instance,
                unit=instance.unit,
                role=DataRoleField.ELECTRICITY_TARIFF,
                timezone=pytz.utc,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

            DataSourceTariffAdapter.objects.create(
                data_format=DataSourceTariffAdapter.DATASOURCEADAPTER,
                datasource=instance,
                unit=instance.unit,
                role=DataRoleField.HEAT_TARIFF,
                timezone=pytz.utc,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.
                district_heating)

        elif any(PhysicalQuantity.compatible_units(instance.unit, tariff_unit)
                 for tariff_unit in units.VOLUME_TARIFF_BASE_UNITS):
            # create volume tariff adapters
            DataSourceTariffAdapter.objects.create(
                data_format=DataSourceTariffAdapter.DATASOURCEADAPTER,
                datasource=instance,
                unit=instance.unit,
                role=DataRoleField.GAS_TARIFF,
                timezone=pytz.utc,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas)

            DataSourceTariffAdapter.objects.create(
                data_format=DataSourceTariffAdapter.DATASOURCEADAPTER,
                datasource=instance,
                unit=instance.unit,
                role=DataRoleField.OIL_TARIFF,
                timezone=pytz.utc,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.oil)

            DataSourceTariffAdapter.objects.create(
                data_format=DataSourceTariffAdapter.DATASOURCEADAPTER,
                datasource=instance,
                unit=instance.unit,
                role=DataRoleField.WATER_TARIFF,
                timezone=pytz.utc,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water)

        elif PhysicalQuantity.compatible_units(
                instance.unit, units.VOLUME_CO2_CONVERSION_BASE_UNIT):
            # create volume co2 conversion adapters
            DataSourceCo2ConversionAdapter.objects.create(
                data_format=DataSourceCo2ConversionAdapter.DATASOURCEADAPTER,
                datasource=instance,
                unit=instance.unit,
                role=DataRoleField.CO2_QUOTIENT,
                timezone=pytz.utc,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas)

            DataSourceCo2ConversionAdapter.objects.create(
                data_format=DataSourceCo2ConversionAdapter.DATASOURCEADAPTER,
                datasource=instance,
                unit=instance.unit,
                role=DataRoleField.CO2_QUOTIENT,
                timezone=pytz.utc,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.oil)

        elif PhysicalQuantity.compatible_units(
                instance.unit, units.ENERGY_CO2_CONVERSION_BASE_UNIT):
            # create energy co2 conversion adapters
            DataSourceCo2ConversionAdapter.objects.create(
                data_format=DataSourceCo2ConversionAdapter.DATASOURCEADAPTER,
                datasource=instance,
                unit=instance.unit,
                role=DataRoleField.CO2_QUOTIENT,
                timezone=pytz.utc,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)

            DataSourceCo2ConversionAdapter.objects.create(
                data_format=DataSourceCo2ConversionAdapter.DATASOURCEADAPTER,
                datasource=instance,
                unit=instance.unit,
                role=DataRoleField.CO2_QUOTIENT,
                timezone=pytz.utc,
                utility_type=utilitytypes.OPTIONAL_METER_CHOICES.
                district_heating)
