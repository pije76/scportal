# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from .views import StartAnnualSavingsPotentialReportView
from .views import FinalizeAnnualSavingsPotentialReportView


urlpatterns = patterns(
    'legacy.projects.views',

    url('^start_annual_savings_potential_report/$',
        StartAnnualSavingsPotentialReportView.as_view(),
        name='projects-startannualsavingspotentialreport'),

    url('^finalize_annual_savings_potential_report/$',
        FinalizeAnnualSavingsPotentialReportView.as_view(),
        name='projects-finalizeannualsavingspotentialreport'),
)
