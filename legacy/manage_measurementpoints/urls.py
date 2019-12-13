# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from gridplatform.utils import utilitytypes

from . import views

from legacy.manage_measurementpoints.forms.imported import \
    ImportedMeasurementPointForm

from gridplatform.users.decorators import auth_or_redirect

urlpatterns = patterns(
    'legacy.manage_measurementpoints.views',
    url(r'^$',
        auth_or_redirect(TemplateView.as_view(
            template_name='manage_measurementpoints/'
            'measurementpoint_list.html')),
        name='measurement_point-list'),
    url(r'^json/measurementpoints/$',
        'list_json',
        name='measurement_point-json-list'),
    url(r'^update/(?P<pk>\d+)$',
        'measurementpoint_form',
        name='measurement_point-update'),
    url(r'^delete/$',
        'measurementpoint_delete',
        name='measurement_point-delete'),

    # CONSUMPTION MEASUREMENT POINT CREATE VIEWS
    url(r'^consumption_measurement_point/electricity$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity),
        name='consumption_measurement_point-electricity-create'),
    url(r'^consumption_measurement_point/gas$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas),
        name='consumption_measurement_point-gas-create'),
    url(r'^consumption_measurement_point/water$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water),
        name='consumption_measurement_point-water-create'),
    url(r'^consumption_measurement_point/district_heating$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating),
        name='consumption_measurement_point-district_heating-create'),
    url(r'^consumption_measurement_point/oil$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.oil),
        name='consumption_measurement_point-oil-create'),

    # CONSUMPTION MEASUREMENT POINT UPDATE VIEW
    url(r'^consumption_measurement_point/(?P<pk>\d+)$',
        views.ConsumptionMeasurementPointUpdateView.as_view(),
        name='consumption_measurement_point-update'),

    # IMPORTED MEASUREMENT POINTS CREATE VIEWS
    url(r'^imported_measurement_point/electricity$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            form_class=ImportedMeasurementPointForm,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
            template_name='manage_measurementpoints/imported.html'),
        name='imported_measurement_point-electricity-create'),
    url(r'^imported_measurement_point/district_heating$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            form_class=ImportedMeasurementPointForm,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating,
            template_name='manage_measurementpoints/imported.html'),
        name='imported_measurement_point-district_heating-create'),
    url(r'^imported_measurement_point/water$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            form_class=ImportedMeasurementPointForm,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water,
            template_name='manage_measurementpoints/imported.html'),
        name='imported_measurement_point-water-create'),
    url(r'^imported_measurement_point/gas$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            form_class=ImportedMeasurementPointForm,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas,
            template_name='manage_measurementpoints/imported.html'),
        name='imported_measurement_point-gas-create'),
    url(r'^imported_measurement_point/oil$',
        views.ConsumptionMeasurementPointCreateView.as_view(
            form_class=ImportedMeasurementPointForm,
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.oil,
            template_name='manage_measurementpoints/imported.html'),
        name='imported_measurement_point-oil-create'),

    # MISC MEASUREMENT POINT CREATE VIEWS
    url(r'^production_measurement_point$',
        views.ProductionMeasurementPointCreate.as_view(),
        name='production_measurement_point-create'),
    url(r'^current_measurement_point$',
        views.CurrentMeasurementPointCreate.as_view(),
        name='current_measurement_point-create'),
    url(r'^voltage_measurement_point$',
        views.VoltageMeasurementPointCreate.as_view(),
        name='voltage_measurement_point-create'),
    url(r'^power_measurement_point$',
        views.PowerMeasurementPointCreate.as_view(),
        name='power_measurement_point-create'),
    url(r'^reactive_power_measurement_point$',
        views.ReactivePowerMeasurementPointCreate.as_view(),
        name='reactive_power_measurement_point-create'),
    url(r'^reactive_energy_measurement_point$',
        views.ReactiveEnergyMeasurementPointCreate.as_view(),
        name='reactive_energy_measurement_point-create'),
    url(r'^power_factor_measurement_point$',
        views.PowerFactorMeasurementPointCreate.as_view(),
        name='power_factor_measurement_point-create'),
    url(r'^temperature_measurement_point/$',
        'temperaturepoint_create_form',
        name='temperature_measurement_point-create'),
    url(r'^efficiency_measurement_point$',
        views.EfficiencyMeasurementPointCreate.as_view(),
        name='efficiency_measurement_point-create'),

    # CONSUMPTION MEASUREMENT POINT SUMMATION CREATE VIEWS
    url(r'^consumption_measurement_point_summation/electricity$',
        views.ConsumptionMeasurementPointSummationCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity),
        name='consumption_measurement_point_summation-electricity-create'),
    url(r'^consumption_measurement_point_summation/district_heating$',
        views.ConsumptionMeasurementPointSummationCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating),
        name=('consumption_measurement_point_summation-district_heating-create')),  # noqa
    url(r'^consumption_measurement_point_summation/water$',
        views.ConsumptionMeasurementPointSummationCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water),
        name='consumption_measurement_point_summation-water-create'),
    url(r'^consumption_measurement_point_summation/gas$',
        views.ConsumptionMeasurementPointSummationCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas),
        name='consumption_measurement_point_summation-gas-create'),
    url(r'^consumption_measurement_point_summation/oil$',
        views.ConsumptionMeasurementPointSummationCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.oil),
        name='consumption_measurement_point_summation-oil-create'),

    # CONSUMPTION MEASUREMENT POINT SUMMATION UPDATE VIEW
    url(r'^consumption_measurement_point_summation/(?P<pk>\d+)$',
        views.ConsumptionMeasurementPointSummationUpdateView.as_view(),
        name='consumption_measurement_point_summation-update'),

    # CONSUMPTION MULTIPLICATION POINT CREATE VIEWS
    url(r'^consumption_multiplication_point/electricity$',
        views.ConsumptionMultiplicationPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity),
        name='consumption_multiplication_point-electricity-create'),
    url(r'^consumption_multiplication_point/district_heating$',
        views.ConsumptionMultiplicationPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.district_heating),
        name='consumption_multiplication_point-district_heating-create'),
    url(r'^consumption_multiplication_point/water$',
        views.ConsumptionMultiplicationPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.water),
        name='consumption_multiplication_point-water-create'),
    url(r'^consumption_multiplication_point/gas$',
        views.ConsumptionMultiplicationPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.gas),
        name='consumption_multiplication_point-gas-create'),
    url(r'^consumption_multiplication_point/oil$',
        views.ConsumptionMultiplicationPointCreateView.as_view(
            utility_type=utilitytypes.OPTIONAL_METER_CHOICES.oil),
        name='consumption_multiplication_point-oil-create'),

    # CONSUMPTION MULTIPLICATION POINT UPDATE VIEW
    url(r'^consumption_multiplication_point/(?P<pk>\d+)$',
        views.ConsumptionMultiplicationPointUpdateView.as_view(),
        name='consumption_multiplication_point-update'),

    # DISTRICT HEATING MEASUREMENT POINT CREATE VIEW
    url(r'^district_heating_measurement_point$',
        views.DistrictHeatingMeasurementPointCreateView.as_view(),
        name='district_heating_measurement_point-create'),

    # DISTRICT HEATING MEASUREMENT POINT UPDATE VIEW
    url(r'^district_heating_measurement_point/(?P<pk>\d+)$',
        views.DistrictHeatingMeasurementPointUpdateView.as_view(),
        name='district_heating_measurement_point-update'),
)
