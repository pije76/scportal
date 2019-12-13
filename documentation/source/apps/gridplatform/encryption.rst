Encryption
==========

To make sure no customer's confidential data is ever leaked we encrypt all
texts written by our users with a key specific to the organization of that
user.


Models
------

.. autoclass:: gridplatform.encryption.models.EncryptedModel
   :members: __init__, save, _encrypt, _decrypt, reset_encryption, get_encryption_id,
             clean_fields

.. autoclass:: gridplatform.encryption.models.EncryptionUser
   :members: generate_private_key, update_private_key, grant_key,
             decrypt_private_key, decrypt_keys

.. autoclass:: gridplatform.encryption.models.BaseEncryptionKey
   :members: key_id, generate, share

.. autoclass:: gridplatform.encryption.models.EncryptionKey

.. autofunction:: gridplatform.encryption.models.auto_grant_to_current_user


Base
----

.. automodule:: gridplatform.encryption.base
   :members: _get_cipher_module, get_cipher_module, MissingEncryptionKeyError,
             _CachedKeys, EncryptionContext

Cipher
------

.. automodule:: gridplatform.encryption.cipher
   :members: generate_iv, generate_symmetric_key, hash_symmetric_key,
             symmetric_cipher, generate_private_public_keypair,
             load_private_key, load_public_key, private_key_cipher,
             public_key_cipher

Settings
--------

.. automodule:: gridplatform.encryption.conf

Fields
------

.. automodule:: gridplatform.encryption.fields
   :members:

Filters
-------

.. autoclass:: gridplatform.encryption.filters.DecryptingSearchFilter

Managers
--------

.. automodule:: gridplatform.encryption.managers
   :members:

Middleware
----------

.. automodule:: gridplatform.encryption.middleware
   :members:

Shell
-----

.. autoclass:: gridplatform.encryption.shell.Request

Signals
-------

.. automodule:: gridplatform.encryption.signals
