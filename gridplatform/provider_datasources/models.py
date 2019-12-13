# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.datasources.models import DataSource
from gridplatform.providers.models import Provider
from gridplatform.trackuser import get_provider

from .managers import ProviderDataSourceManager


# NOTE: The ProviderDataSourceManager applies to all ProviderDataSource
# specializations.  For the manager to be inherited it must be set on an
# abstract Model.
class ProviderDataSourceBase(DataSource):
    class Meta:
        abstract = True

    objects = ProviderDataSourceManager()


class ProviderDataSource(ProviderDataSourceBase):
    """
    Specialization of :class:`~gridplatform.datasources.models.DataSource` that
    is owned by :class:`~gridplatform.providers.models.Provider` and shared
    among the :class:`~gridplatform.customers.models.Customer` of that
    :class:`~gridplatform.providers.models.Provider`.

    :ivar provider: The owning
        :class:`~gridplatform.providers.models.Provider`.

    :cvar objects: The manager of :class:`.ProviderDataSource` is a
        :class:`.ProviderDataSourceManager`.
    """
    provider = models.ForeignKey(
        Provider, verbose_name=_('provider'), default=get_provider)

    class Meta:
        verbose_name = _('provider data source')
        verbose_name_plural = _('provider data sources')

    def __unicode__(self):
        return self.hardware_id
