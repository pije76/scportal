# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from collections import OrderedDict

import rest_framework.viewsets
import rest_framework.reverse

import gridplatform.rest.routers
import gridplatform.consumptions.viewsets
import gridplatform.cost_compensations.viewsets
import gridplatform.customer_datasources.viewsets
import gridplatform.customers.viewsets
import gridplatform.datasequences.viewsets
import gridplatform.energyperformances.viewsets
import gridplatform.energyperformances.views
import gridplatform.global_datasources.viewsets
import gridplatform.productions.viewsets
import gridplatform.provider_datasources.viewsets
import gridplatform.tariffs.viewsets
import energymanager.price_relay_site.viewsets


class EnergyPerformances(rest_framework.viewsets.ViewSet):
    _ignore_model_permissions = True

    def list(self, request, format=None):
        return rest_framework.response.Response(OrderedDict(sorted([
            ('production_energyperformances', rest_framework.reverse.reverse(
                'api:energyperformances:productionenergyperformance-list',
                request=request, format=format)),
            ('time_energyperformances', rest_framework.reverse.reverse(
                'api:energyperformances:timeenergyperformance-list',
                request=request, format=format)),
        ])))


class DataSequences(rest_framework.viewsets.ViewSet):
    _ignore_model_permissions = True

    def list(self, request, format=None):
        return rest_framework.response.Response(OrderedDict(sorted([
            ('main_consumptions', rest_framework.reverse.reverse(
                'api:consumptions:mainconsumption-list',
                request=request, format=format)),
            ('consumption_groups', rest_framework.reverse.reverse(
                'api:consumptions:consumptiongroup-list',
                request=request, format=format)),
            ('consumption_datasequences', rest_framework.reverse.reverse(
                'api:consumptions:consumption-list',
                request=request, format=format)),
            ('production_groups', rest_framework.reverse.reverse(
                'api:productions:productiongroup-list',
                request=request, format=format)),
            ('production_datasequences', rest_framework.reverse.reverse(
                'api:productions:production-list',
                request=request, format=format)),
            ('energy_per_volume_datasequences', rest_framework.reverse.reverse(
                'api:datasequences:energypervolumedatasequence-list',
                request=request, format=format)),
            ('nonaccumulation_datasequences', rest_framework.reverse.reverse(
                'api:datasequences:nonaccumulationdatasequence-list',
                request=request, format=format)),
            ('energy_tariff_datasequences', rest_framework.reverse.reverse(
                'api:tariffs:energytariff-list',
                request=request, format=format)),
            ('volume_tariff_datasequences', rest_framework.reverse.reverse(
                'api:tariffs:volumetariff-list',
                request=request, format=format)),
            ('cost_compensation_datasequences', rest_framework.reverse.reverse(
                'api:cost_compensations:costcompensation-list',
                request=request, format=format)),
        ])))


class DataSources(rest_framework.viewsets.ViewSet):
    _ignore_model_permissions = True

    def list(self, request, format=None):
        return rest_framework.response.Response(OrderedDict(sorted([
            ('global_datasources', rest_framework.reverse.reverse(
                'api:global_datasources:globaldatasource-list',
                request=request, format=format)),
            ('provider_datasources', rest_framework.reverse.reverse(
                'api:provider_datasources:providerdatasource-list',
                request=request, format=format)),
            ('customer_datasources', rest_framework.reverse.reverse(
                'api:customer_datasources:customerdatasource-list',
                request=request, format=format)),
        ])))


root_routes = gridplatform.rest.routers.DefaultRouter()
root_routes.description = """
# Welcome to the GridPlatform API.

The URL
[https://portal.grid-manager.com/api/current](https://portal.grid-manager.com/api/current)
will always redirect to the current version of the API.

Authentication is either done by logging in with username and password, which
is practical when navigating the browsable API to familiarise oneself with the
available resources, or it can be done using an authentication token, which is
the normal way of accessing the API programmatically.

To get an authentication token you must contact your GridPlatform access
provider and make then issue you a suitable one.

The token must be part of the header of every HTTP request. The HTTP headers
should be extended with the following line:

    Authorization: token <token>

where <token> is the API authentication token. A token is just a text string
and might look something like this:

    9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b


## Filter Fields
* GET list resource data has a property called `filterFields` containing
  a list of field names. Each name is this list can be used a querystring
  parameter for filtering the list results on equality for the that fields
  value.
* OPTIONS for a list resource shows all the possible actions for that
  resource, and more. One of the properties for each field is `filterField`.
  It is either `null` (i.e. the field is not a filter field) or contains the
  query string parameter name corresponding to that field. The query string
  parameter can be used for filtering the list, checking for equality on that
  field.

## Bulk Actions
* OPTIONS for list a resource may contain a `bulkActions` property containing a
  list of HTTP actions that support bulk operation. Currently only bulk
  creation (POST) is supported, and that is only on the various data source
  `rawData` list resources. To perform a `rawData` bulk creation simply POST an
  array of `rawData` objects to the relevant `rawData` list resource.

# API Root
"""
root_routes.register(
    r'customers', gridplatform.customers.viewsets.CustomerViewSet)

energyperformance_routes = root_routes.register(
    r'energy_performances', EnergyPerformances, base_name='energyperformances')
energyperformance_routes.register(
    r'production_energy_performances',
    gridplatform.energyperformances.viewsets.ProductionEnergyPerformance)
energyperformance_routes.register(
    r'time_energy_performances',
    gridplatform.energyperformances.viewsets.TimeEnergyPerformance)

datasequence_routes = root_routes.register(
    r'datasequences', DataSequences, base_name='datasequences')
datasequence_routes.register(
    r'main_consumptions',
    gridplatform.consumptions.viewsets.MainConsumption)
datasequence_routes.register(
    r'consumption_groups',
    gridplatform.consumptions.viewsets.ConsumptionGroup)
datasequence_routes.register(
    r'production_groups',
    gridplatform.productions.viewsets.ProductionGroup)

consumption_routes = datasequence_routes.register(
    r'consumption_datasequences',
    gridplatform.consumptions.viewsets.Consumption)
consumption_routes.register(
    r'offline_tolerances',
    gridplatform.consumptions.viewsets.OfflineTolerance,
    filter_by='datasequence_id')
consumption_routes.register(
    r'nonpulse_periods',
    gridplatform.consumptions.viewsets.NonpulsePeriod,
    filter_by='datasequence_id')
consumption_routes.register(
    r'pulse_periods',
    gridplatform.consumptions.viewsets.PulsePeriod,
    filter_by='datasequence_id')
consumption_routes.register(
    r'single_value_periods',
    gridplatform.consumptions.viewsets.SingleValuePeriod,
    filter_by='datasequence_id')

production_routes = datasequence_routes.register(
    r'production_datasequences',
    gridplatform.productions.viewsets.Production)
production_routes.register(
    r'offline_tolerances',
    gridplatform.productions.viewsets.OfflineTolerance,
    filter_by='datasequence_id')
production_routes.register(
    r'nonpulse_periods',
    gridplatform.productions.viewsets.NonpulsePeriod,
    filter_by='datasequence_id')
production_routes.register(
    r'pulse_periods',
    gridplatform.productions.viewsets.PulsePeriod,
    filter_by='datasequence_id')
production_routes.register(
    r'single_value_periods',
    gridplatform.productions.viewsets.SingleValuePeriod,
    filter_by='datasequence_id')

energypervolume_routes = datasequence_routes.register(
    r'energy_per_volume_datasequences',
    gridplatform.datasequences.viewsets.EnergyPerVolumeDataSequence)
energypervolume_routes.register(
    r'energy_per_volume_periods',
    gridplatform.datasequences.viewsets.EnergyPerVolumePeriod,
    filter_by='datasequence_id')

nonaccumulation_routes = datasequence_routes.register(
    r'nonaccumulation_datasequences',
    gridplatform.datasequences.viewsets.NonaccumulationDataSequence)
nonaccumulation_routes.register(
    r'nonaccumulation_periods',
    gridplatform.datasequences.viewsets.NonaccumulationPeriod,
    filter_by='datasequence_id')
nonaccumulation_routes.register(
    r'offline_tolerances',
    gridplatform.datasequences.viewsets.NonaccumulationOfflineTolerance,
    filter_by='datasequence_id')

energytariff_routes = datasequence_routes.register(
    r'energytariffs',
    gridplatform.tariffs.viewsets.EnergyTariff)
energytariff_routes.register(
    'fixed_price_periods',
    gridplatform.tariffs.viewsets.FixedPricePeriod,
    filter_by='datasequence_id')
energytariff_routes.register(
    'spot_price_periods',
    gridplatform.tariffs.viewsets.SpotPricePeriod,
    filter_by='datasequence_id')

volumetariff_routes = datasequence_routes.register(
    r'volumetariffs',
    gridplatform.tariffs.viewsets.VolumeTariff)
volumetariff_routes.register(
    'fixed_price_periods',
    gridplatform.tariffs.viewsets.FixedPricePeriod,
    filter_by='datasequence_id')
volumetariff_routes.register(
    'spot_price_periods',
    gridplatform.tariffs.viewsets.SpotPricePeriod,
    filter_by='datasequence_id')


cost_compensation_routes = datasequence_routes.register(
    r'cost_compensation',
    gridplatform.cost_compensations.viewsets.CostCompensation)
cost_compensation_routes.register(
    'fixed_compensation_period',
    gridplatform.cost_compensations.viewsets.FixedCompensationPeriod,
    filter_by='datasequence_id')


datasource_routes = root_routes.register(
    r'datasources', DataSources, base_name='datasources')
datasource_routes.register(
    r'raw_data',
    gridplatform.datasources.viewsets.RawDataViewSet,
    filter_by='datasource_id')
datasource_routes.register(
    r'datasource',
    gridplatform.datasources.viewsets.DataSourceViewSet)

global_datasource_routes = datasource_routes.register(
    r'global_datasources',
    gridplatform.global_datasources.viewsets.GlobalDataSourceViewSet)

provider_datasource_routes = datasource_routes.register(
    r'provider_datasources',
    gridplatform.provider_datasources.viewsets.ProviderDataSourceViewSet)

customer_datasource_routes = datasource_routes.register(
    r'customer_datasources',
    gridplatform.customer_datasources.viewsets.CustomerDataSourceViewSet)

root_routes.register(
    r'pricerelays',
    energymanager.price_relay_site.viewsets.RelaySettingsViewSet,
    base_name='pricerelays'
)

urlpatterns = root_routes.urls
