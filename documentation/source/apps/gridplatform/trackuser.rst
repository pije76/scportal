Track User
=================

The ``trackuser`` app defines a number of global functions to access various
data that depend on the user currently logged in.

.. autofunction:: gridplatform.trackuser.get_user
.. autofunction:: gridplatform.trackuser._get_user_customer
.. autofunction:: gridplatform.trackuser._get_override_customer
.. autofunction:: gridplatform.trackuser._get_selected_customer
.. autofunction:: gridplatform.trackuser.get_customer
.. autofunction:: gridplatform.trackuser.get_provider
.. autofunction:: gridplatform.trackuser.get_provider_id
.. autofunction:: gridplatform.trackuser.get_timezone
.. autofunction:: gridplatform.trackuser.get_current_date

Context Managers
----------------

.. py:function:: gridplatform.trackuser.replace_user(user)

   A context manager within which the :class:`~gridplatform.users.models.User`
   returned by :py:func:`get_user` will appear to be the given user.

.. py:function:: gridplatform.trackuser.replace_override_customer(customer)

   A context manager within which the
   :class:`~gridplatform.customers.models.Customer` returned by
   :py:func:`_get_override_customer` will appear to be the given customer.

.. py:function:: gridplatform.trackuser.replace_selected_customer(customer)

   A context manager within which the
   :class:`~gridplatform.customers.models.Customer` returned by
   :py:func:`_get_selected_customer` will appear to be the given customer.


.. py:function:: gridplatform.trackuser.replace_customer(customer)

   A context manager within which the
   :class:`~gridplatform.customers.models.Customer` returned by
   :py:func:`get_customer` will appear to be the given customer.

   This is primariliy used for unit-testing.

Managers
--------

.. autoclass:: gridplatform.trackuser.managers.FilteringQuerySetMixinBase
   :members: iterator, aggregate, count, delete, update, _update, exists,
             _clone, values, values_list, dates,
             datetimes, _apply_filtering

.. autoclass:: gridplatform.trackuser.managers.CustomerBoundQuerySetMixin
   :members: _apply_filtering

.. autoclass:: gridplatform.trackuser.managers.ProviderBoundQuerySetMixin
   :members: _apply_filtering

.. autoclass:: gridplatform.trackuser.managers.CustomerBoundManagerBase

.. autoclass:: gridplatform.trackuser.managers.CustomerBoundManager

.. autoclass:: gridplatform.trackuser.managers.TreeCustomerBoundManager

.. autoclass:: gridplatform.trackuser.managers.StoredSubclassCustomerBoundManager

.. autoclass:: gridplatform.trackuser.managers.StoredSubclassTreeCustomerBoundManager

.. autoclass:: gridplatform.trackuser.managers.ProviderBoundManager

Middleware
----------

.. autoclass:: gridplatform.trackuser.middleware.TrackUserMiddleware

Tasks
-----

The ``trackuser`` provides some Celery task decorators for tracking users and
similar context into Celery tasks.

.. autofunction:: gridplatform.trackuser.tasks.trackuser_task
.. autofunction:: gridplatform.trackuser.tasks.task
