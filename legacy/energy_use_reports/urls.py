# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from .views import FinalizeEnergyUseReportView
from .views import StartEnergyUseReportView

urlpatterns = patterns(
    'legacy.energy_use_reports.views',
    url(r'^start_report/$',
        StartEnergyUseReportView.as_view(),
        name='energy_use_reports-start_report'),
    url(r'^finalize_report/$',
        FinalizeEnergyUseReportView.as_view(),
        name='energy_use_reports-finalize_report'),
)
