Provider Data Sources
=====================

This app defines :class:`~gridplatform.datasources.models.DataSource` owned by
:class:`~gridplatform.providers.models.Provider`
(:class:`~gridplatform.provider_datasources.models.ProviderDataSource`) and
shared among the :class:`~gridplatform.customers.models.Customer` of that
:class:`~gridplatform.providers.models.Provider`.

.. autoclass:: gridplatform.provider_datasources.models.ProviderDataSource

.. autoclass:: gridplatform.provider_datasources.managers.ProviderDataSourceManager

.. autoclass:: gridplatform.provider_datasources.managers.ProviderDataSourceManagerBase

.. autoclass:: gridplatform.provider_datasources.managers.ProviderDataSourceQuerySetMixin
   :members: _apply_customer_filtering, _apply_provider_filtering
