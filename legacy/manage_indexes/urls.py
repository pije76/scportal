# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module defines URLs of the manage_indexes Django app.
"""

from django.conf.urls import patterns, url

from . import views


def _url(regexp, view):
    """
    All URLs are identified as C{manage_indexes-<VIEW_NAME>}.
    """
    return url(regexp, view, name=("manage_indexes-" + view))


urlpatterns = patterns(
    "legacy.manage_indexes.views",
    _url(r"^$", "listing"),
    _url(r"^list-json/$", "list_json"),

    url(r'^form/derived/tariff/electricity$',
        views.DerivedElectricityTariffCreateView.as_view(),
        name='manage_indexes-derived-electricity-tariff-create-view'),

    url(r'^form/derived/tariff/gas$',
        views.DerivedGasTariffCreateView.as_view(),
        name='manage_indexes-derived-gas-tariff-create-view'),

    url(r'^form/derived/tariff/water$',
        views.DerivedWaterTariffCreateView.as_view(),
        name='manage_indexes-derived-water-tariff-create-view'),

    url(r'^form/derived/tariff/district_heating$',
        views.DerivedDistrictHeatingTariffCreateView.as_view(),
        name='manage_indexes-derived-district_heating-tariff-create-view'),

    url(r'^form/derived/tariff/oil$',
        views.DerivedOilTariffCreateView.as_view(),
        name='manage_indexes-derived-oil-tariff-create-view'),

    url(r'^form/seasons/tariff/electricity$',
        views.SeasonsElectricityTariffCreateView.as_view(),
        name='manage_indexes-seasons-electricity-tariff-create-view'),

    url(r'^form/seasons/tariff/gas$',
        views.SeasonsGasTariffCreateView.as_view(),
        name='manage_indexes-seasons-gas-tariff-create-view'),

    url(r'^form/seasons/tariff/water$',
        views.SeasonsWaterTariffCreateView.as_view(),
        name='manage_indexes-seasons-water-tariff-create-view'),

    url(r'^form/seasons/tariff/district_heating$',
        views.SeasonsDistrictHeatingTariffCreateView.as_view(),
        name='manage_indexes-seasons-district_heating-tariff-create-view'),

    url(r'^form/seasons/tariff/oil$',
        views.SeasonsOilTariffCreateView.as_view(),
        name='manage_indexes-seasons-oil-tariff-create-view'),

    url(r'^form/seasons/employees/unknown$',
        views.SeasonsEmployeesIndexCreateView.as_view(),
        name='manage_indexes-seasons-employees-index-create-view'),

    url(r'^form/seasons/area/unknown$',
        views.SeasonsAreaIndexCreateView.as_view(),
        name='manage_indexes-seasons-area-index-create-view'),

    url(r'^form/derived/(?P<pk>\d+)/$',
        views.DerivedIndexUpdateView.as_view(),
        name='manage_indexes-derived-index-update-view'),

    url(r'^form/seasons/(?P<pk>\d+)/$',
        views.SeasonsIndexUpdateView.as_view(),
        name='manage_indexes-seasons-index-update-view'),

    _url(r"^delete/$", "delete"),
)
