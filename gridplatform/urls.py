# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib import admin
import django.contrib.auth.models
from django.conf import settings
from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
import djcelery.models

from gridplatform.utils.urls import restricted_url


js_info_dict = {
    'packages': (
        'legacy.website',
        'legacy.manage_devices',
        'legacy.manage_customers',
    ),
}


urlpatterns = patterns(
    '',
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
    (r'^jserror/', include('gridplatform.jserror.urls')),
    url(r'^task_status/$',
        'gridplatform.utils.views.task_status',
        name='task_status'),
    url(r'^manage/customers/', include('legacy.manage_customers.urls')),
    url(r'^manage/agents/', include('legacy.setup_agents.urls')),
    url(r'^locations/', include('legacy.manage_locations.urls')),
    url(r'^groups/', include('legacy.manage_collections.urls')),
    url(r'^devices/', include('legacy.manage_devices.urls')),
    url(r'^measurementpoints/',
        include(
            'legacy.manage_measurementpoints.urls',
            namespace='manage_measurementpoints')),
    url(r'^overview/details/',
        include('legacy.display_measurementpoints.urls')),
    url(r'^overview/indexes/',
        include('legacy.display_indexes.urls')),
    url(r'^projects/', include('legacy.display_projects.urls')),
    url(r'^users/', include('legacy.manage_users.urls')),
    url(r'^widgets/', include('legacy.display_widgets.urls')),
    url(r'^userprofile/', include('legacy.edit_userprofile.urls')),
    url(r'^rules/', include('legacy.manage_rules.urls')),
    url(r'^indexes/', include('legacy.manage_indexes.urls')),
    url(r'^reports/', include('legacy.manage_reports.urls')),
    url(r'', include('legacy.website.urls')),
    url('^energy_use_reports/',
        include('legacy.energy_use_reports.urls')),
    url('^enpi_reports/',
        include('legacy.enpi_reports.urls')),
    url(r'^report_generators/', include('gridplatform.reports.urls')),
    url(r'^project_generators/', include('legacy.projects.urls')),
    url(r'^start/',
        include('energymanager.start_site.urls', namespace='start_site')),
    url(r'^user/', include('gridplatform.users.urls', namespace='users')),
    url(r'^Wibeee/', include('gridplatform.smilics.urls')),
    # Provider site
    restricted_url(
        r'^admin/',
        include('energymanager.provider_site.urls',
                namespace='provider_site'),
        permission='users.access_provider_site',
        requires_provider=True),
    restricted_url(
        r'^configuration/',
        include('energymanager.configuration_site.urls',
                namespace='configuration_site'),
        permission='users.access_provider_site',
        requires_provider=True),
    # LED Light site
    restricted_url(
        r'^led_light/',
        include('energymanager.led_light_site.urls',
                namespace='led_light_site'),
        permission='users.access_led_light_site'),

    # HACK to restrict project urls
    # TODO: Figure out why restricted_url doesn't work in app url files
    restricted_url(
        r'^led_light/',
        include('energymanager.led_light_site.restricted_urls',
                namespace='led_light_site_projects'),
        permission='users.access_led_light_site_projects'),

    # Access price_relay site
    restricted_url(
        r'^price_relay/',
        include('energymanager.price_relay_site.urls',
                namespace='price_relay_site'),
        permission='users.access_price_relay_site'),

    # Project site
    restricted_url(
        r'^escolite/',
        include('energymanager.project_site.urls',
                namespace='project_site'),
        permission='users.access_project_site'),

    # Datahub site
    restricted_url(
        r'^datahub/',
        include('energymanager.datahub_site.urls',
                namespace='datahub_site'),
        permission='users.access_datahub_site'),


    # REST API
    url(r'^api/current/',
        RedirectView.as_view(url=reverse_lazy('api:api-root')),
        name='api-current-version'),
    url(r'^api/v3/', include('gridplatform.api', namespace='api')),

)


admin.autodiscover()

admin.site.unregister(django.contrib.auth.models.User)

admin.site.unregister(djcelery.models.TaskState)
admin.site.unregister(djcelery.models.WorkerState)
admin.site.unregister(djcelery.models.IntervalSchedule)
admin.site.unregister(djcelery.models.CrontabSchedule)
admin.site.unregister(djcelery.models.PeriodicTask)


urlpatterns += patterns(
    '',
    restricted_url(
        r'^sysadmin/',
        include(admin.site.urls),
        requires_is_staff=True),
)


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns(
        '',
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^qunit/', include('django_qunit.urls')),
    )
