# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from .views import StartGraphdataDownloadView
from .views import FinalizeGraphdataDownloadView
from legacy.enpi_reports.views import CreateENPIReportView
from legacy.enpi_reports.views import UpdateENPIReportView


urlpatterns = patterns(
    'legacy.manage_reports.views',
    url(r'^$', 'index',
        name='manage_reports-index'),
    url(r'^create/consumption/$', 'create_consumption_report',
        name='manage_reports-create_consumption_report'),
    url(r'^create/energy_use/(?P<utility_type>\w+)/$',
        'create_energy_use_report',
        name='manage_reports-create_energy_use_report'),
    url(r'^update/energy_use/(?P<pk>\d+)/$', 'update_energy_use_report',
        name='manage_reports-update_energy_use_report'),
    url(r'^delete/$',
        'delete',
        name='manage_reports-delete'),
    url(r'^request/$',
        'request_consumption_report',
        name='manage_reports-request_consumption_report'),
    url(r'^finalize/$',
        'finalize_consumption_report',
        name='manage_reports-finalize_consumption_report'),
    url(r'^(?P<pdf_id>\d+)/(?P<title>.+)\.pdf$',
        'serve_pdf',
        name='manage_reports-serve_pdf'),
    url(r'^(?P<csv_id>\d+)/(?P<title>.+)\.csv$',
        'serve_csv',
        name='manage_reports-serve_csv'),
    url(r'^request_export/$',
        StartGraphdataDownloadView.as_view(),
        name='manage_reports-startgraphdatadownload'),
    url(r'^finalize_export/$',
        FinalizeGraphdataDownloadView.as_view(),
        name='manage_reports-finalizegraphdatadownload'),

    url(r'^enpi/new/(?P<energy_driver_unit>[-a-z0-9_^*]+)$',
        CreateENPIReportView.as_view(),
        name='manage_reports-create_enpi_report_form'),
    url(r'^enpi/(?P<pk>\d+)/$',
        UpdateENPIReportView.as_view(),
        name='manage_reports-update_enpi_report_form'),
    url(r'^enpi/delete/$',
        'enpi_delete',
        name='manage_reports-enpi-delete'),
)
