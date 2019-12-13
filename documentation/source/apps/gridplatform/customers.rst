Customers
=========

The ``customers`` app defines the
:py:class:`~gridplatform.customers.models.Customer` model, which in turn
represent the entity that owns any particular instance of the domain.

.. autoclass:: gridplatform.customers.models.Customer
   :members: clean_fields, save, now, get_encryption_id, satisfies_search,
             get_production_unit_choices

.. autoclass:: gridplatform.customers.managers.CustomerManager

.. autoclass:: gridplatform.customers.managers.CustomerQuerySetMixin
   :members: _apply_filtering
