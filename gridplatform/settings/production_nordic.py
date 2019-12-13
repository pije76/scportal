from __future__ import absolute_import

from .production import *  # noqa


# ######### CELERY CONFIGURATION
CELERY_ROUTES = {
    'legacy.energy_use_reports.tasks.EnergyUseReportTask': {
        'queue': 'reports',
    },
    'legacy.manage_reports.tasks.collect_consumption_data': {
        'queue': 'reports',
    },
    'legacy.display_projects.tasks.ProjectReportTask': {
        'queue': 'reports',
    },
    'legacy.enpi_reports.tasks.ENPIReportTask': {
        'queue': 'reports',
    },
}
# ######### END CELERY CONFIGURATION
