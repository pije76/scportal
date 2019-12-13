Users
=====

This app defines the :py:class:`~gridplatform.users.models.User` model which is
used for user authentication and authorization.

.. autoclass:: gridplatform.users.models.User
   :members: clean_fields, save, _decrypt, get_username, set_password,
             reset_password, is_admin, is_customer_superuser,
             get_encryption_id, satisfies_search


Encryption Key Signal Handlers
------------------------------

A number of signal handlers take care of encryption key generation and sharing.

.. autofunction:: gridplatform.users.models.create_user_key

.. autofunction:: gridplatform.users.models.auto_grant_to_admins

.. autofunction:: gridplatform.users.models.auto_grant_user_self_key

.. autofunction:: gridplatform.users.models.auto_grant_user_key_to_superusers

.. autofunction:: gridplatform.users.models.auto_grant_customer_superuser_user_keys

.. autofunction:: gridplatform.users.models.auto_grant_provideruser_provider_key

.. autofunction:: gridplatform.users.models.auto_grant_provideruser_customer_keys

.. autofunction:: gridplatform.users.models.auto_grant_provideruser_provideruser_keys


Views
-----

.. autoclass:: gridplatform.users.views.CustomerAdminOrAdminRequiredMixin
   :members: dispatch

.. autoclass:: gridplatform.users.views.UserProfileForm
   :members: clean

.. autoclass:: gridplatform.users.views.UserProfileView
   :members: get_form_kwargs, form_valid


Managers
--------

.. autofunction:: gridplatform.users.managers.hash_username

.. autoclass:: gridplatform.users.managers.UserManager
   :members: create_user

.. autoclass:: gridplatform.users.managers.UserQuerySetMixin
   :members: _apply_filtering

.. autoclass:: gridplatform.users.managers.BoundUserManager
