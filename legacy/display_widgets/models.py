# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.users.models import User
from legacy.measurementpoints.models import Collection
from legacy.indexes.models import Index
from gridplatform.trackuser.managers import CustomerBoundManager


class UserCustomerBoundManager(CustomerBoundManager):
    _field = 'user__customer'


class DashboardWidget(models.Model):
    LEFT_COLUMN = 0
    RIGHT_COLUMN = 1
    COLUMN_CHOICES = (
        (LEFT_COLUMN, _('Left')),
        (RIGHT_COLUMN, _('Right')),
    )
    CONSUMPTION_GRAPH = 0
    GAUGE = 1
    INDEX_GRAPH = 2
    RATE_GRAPH = 3
    COOLDOWN_GRAPH = 4
    PRODUCTION_GRAPH = 5

    WIDGET_TYPE_CHOICES = (
        (CONSUMPTION_GRAPH, _('Consumption Graph')),
        (GAUGE, _('Gauge')),
        (INDEX_GRAPH, _('Index Graph')),
        (RATE_GRAPH, _('Rate Graph')),
        (COOLDOWN_GRAPH, _('Mean Cool-down Temperature Graph')),
        (PRODUCTION_GRAPH, _('Production Graph')),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    column = models.IntegerField(_('Column'), choices=COLUMN_CHOICES)
    row = models.IntegerField()
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE,
                                   null=True)
    index = models.ForeignKey(Index, on_delete=models.CASCADE, null=True)
    widget_type = models.IntegerField(_('Type'), choices=WIDGET_TYPE_CHOICES)

    objects = UserCustomerBoundManager()

    def get_icon(self):
        """
        Returns icon string for this C{DashboardWidget}.
        """
        if self.collection_id:
            return self.collection.get_icon()
        else:
            assert self.index_id
            return self.index.get_icon()
