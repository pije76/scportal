Token Auth
==========

The built-in token authentication of Django REST framework knows little about
our encryption scheme.  This app provides the necessary customizations to
include the additionally needed information in the token string.

.. autofunction:: gridplatform.token_auth.models.create_token

.. autoclass:: gridplatform.token_auth.models.TokenData
   :members: provide_token, decrypt_password, lookup_token

.. autoclass:: gridplatform.token_auth.authentication.EncryptionTokenAuthentication
   :members: authenticate, authenticate_credentials

Configuration
-------------

.. automodule:: gridplatform.token_auth.conf
