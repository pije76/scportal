Providers
=========

The ``providers`` app defines the
:py:class:`~gridplatform.providers.models.Provider` model, which represent the
entity that facilitates the software towards
:py:class:`~gridplatform.customers.models.Customer`.


.. autoclass:: gridplatform.providers.models.Provider
   :members: get_encryption_id, save

.. autofunction:: gridplatform.providers.models.auto_grant_provider_user_key

.. autofunction:: gridplatform.providers.models.auto_grant_provider_customer_key
