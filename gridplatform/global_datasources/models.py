# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_countries.fields import CountryField

from gridplatform.datasources.models import DataSource


class GlobalDataSource(DataSource):
    """
    Specialization of :class:`~gridplatform.datasources.models.DataSource` that
    is globally accessible.

    :ivar name:  The name.
    :ivar app_label: String used identify the app that feeds data into this
        global data source.
    :ivar codename: Application specific string used to help identify this
        global data source.
    :ivar country: A country code for the country in which this global data
        source applies.
    """
    name = models.CharField(_('name'), max_length=120)
    app_label = models.CharField(max_length=100, editable=False)
    codename = models.CharField(max_length=100, editable=False)
    country = CountryField(editable=False)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('app_label', 'codename', 'country')
