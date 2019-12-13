# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from .views import FinalizeENPIReportView
from .views import StartENPIReportView

urlpatterns = patterns(
    'legacy.enpi_reports.views',
    url(r'^start_report/$',
        StartENPIReportView.as_view(),
        name='enpi_reports-start_report'),
    url(r'^finalize_report/$',
        FinalizeENPIReportView.as_view(),
        name='enpi_reports-finalize_report'),
)
