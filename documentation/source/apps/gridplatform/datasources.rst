Data Sources
============

.. autoclass:: gridplatform.datasources.models.DataSource
   :members: hourly_accumulated, five_minute_accumulated, _get_interpolate_fn,
             raw_sequence, next_valid_date, previous_valid_date

.. autoclass:: gridplatform.datasources.models.RawData
   :members: clean, interpolate

Managers
--------

.. autoclass:: gridplatform.datasources.managers.DataSourceQuerySetMixinBase
   :members: _apply_filtering, _apply_customer_filtering, _apply_provider_filtering


.. autoclass:: gridplatform.datasources.managers.DataSourceQuerySetMixin
   :members: _apply_customer_filtering, _apply_provider_filtering

.. autoclass:: gridplatform.datasources.managers.DataSourceManagerBase

.. autoclass:: gridplatform.datasources.managers.DataSourceManager
