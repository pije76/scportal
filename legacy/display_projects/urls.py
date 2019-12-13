# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns
from django.conf.urls import url

from . import views


urlpatterns = patterns(
    '',
    url('^$',
        views.BenchmarkProjectIndexView.as_view(),
        name='display_projects-index'),
    url('^(?P<pk>\d+)/$',
        views.BenchmarkProjectDetailView.as_view(),
        name='display_projects-details'),
    url('^update/(?P<pk>\d+)/$',
        views.benchmarkproject_update,
        name='display_projects-update'),
    url('^update/(?P<pk>\d+)/normal/$',
        views.BenchmarkProjectUpdateView.as_view(),
        name='display_projects-update_normal'),
    url('^update/(?P<pk>\d+)/water/$',
        views.WaterBenchmarkProjectUpdateView.as_view(),
        name='display_projects-update_water'),
    url('^create/(?P<utility_type>(electricity|gas|district_heating|oil))$',
        views.BenchmarkProjectCreateView.as_view(),
        name='display_projects-create'),
    url('^create/(?P<utility_type>(water))$',
        views.WaterBenchmarkProjectCreateView.as_view(),
        name='display_projects-create_water'),
    url('^delete/(?P<pk>\d+)/$',
        views.BenchmarkProjectDeleteView.as_view(),
        name='display_projects-delete'),
    url('^request_project_report/$',
        views.StartProjectReportView.as_view(),
        name='display_projects-startprojectreport'),
    url('^finalize_project_report/$',
        views.FinalizeProjectReportView.as_view(),
        name='display_projects-finalizeprojectreport'),
    url('^annual_savings_potential_form/$',
        views.AnnualSavingsPotentialReportGenerationFormView.as_view(),
        name='display_projects-annualsavingspotentialreportform'),
)
