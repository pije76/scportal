# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import sys
import pytz

from django.db import models
from django.db.models import signals

# ensure that appconf settings are loaded
from .conf import settings

from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.indexes.models import Index


class ModelBinding(models.Model):
    """
    Reference to the index instances used for Energinet CO₂.  Which index ID is
    used may differ between deployments; thus this is kept in the database ---
    as a model where only a single instance will be saved...
    """
    index = models.ForeignKey(
        Index, on_delete=models.CASCADE, related_name='+')
    # forecast_index = models.ForeignKey(
    #     Index, on_delete=models.CASCADE, related_name='+')


def setup_modelbinding(**kwargs):
    if ModelBinding.objects.exists():
        # already set up
        return
    unit = settings.ENERGINET_CO2_UNIT
    name = settings.ENERGINET_CO2_NAME
    timezone = pytz.timezone(settings.ENERGINET_CO2_TIMEZONE)
    binding = ModelBinding()
    binding.index = Index.objects.create(
        unit=unit,
        name_plain=name,
        data_format=Index.SPOT,
        role=DataRoleField.CO2_QUOTIENT,
        timezone=timezone,
        utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity,
        customer=None)
    # binding.forecast_index = Index.objects.create(
    #     unit=unit,
    #     name=name,
    #     data_format=Index.SPOT,
    #     role=DataRoleField.CO2_QUOTIENT,
    #     timezone=timezone,
    #     utility_type=utilitytypes.OPTIONAL_METER_CHOICES.electricity)
    binding.save()


if settings.ENERGINET_CO2_AUTO_SETUP:
    this_module = sys.modules[__name__]
    signals.post_syncdb.connect(setup_modelbinding, sender=this_module)
