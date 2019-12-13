# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from legacy.measurementpoints.models import Collection


# Legacy user profile. Placed here instead of making another app just for
# this one model.

class UserProfile(models.Model):
    """
    "Extra" user information specific to customer users.  For the GridPortal,
    this is the active User Profile; other applications on the GridPlatform may
    use something else.
    """
    user = models.OneToOneField('users.User', on_delete=models.CASCADE)
    collections = models.ManyToManyField(
        Collection,
        through='customers.CollectionConstraint')

    class Meta:
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')
        ordering = ['id']
        db_table = 'customers_userprofile'
        app_label = 'customers'
