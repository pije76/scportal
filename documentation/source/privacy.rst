*******
Privacy
*******

We encrypt sensitive information, and we take care to avoid having the
encryption keys stored or communicated over the network.

As the primary function of the GridPlatform is to perform calculations on
measurement it would be major performance problem if measurements were to be
encrypted. To avoid this, all textual company information is instead
considered to be confidential. That is, if you hacked the servers and dumped
the database, then you would get all the measurements but you would not know
who they belong to or in any way what they are for. Also, even if a develop
makes an access control logic error and by mistake gives a user from one customer
access to objects from another customer, the user will not be able to see the
encrypted data that do not belong to his company. In fact, it will cause an
exception to be raised and this will in turn cause the GridPlatform to send
the administrators an e-mail containing a stack trace describing exactly
where the violation occurred.

So the privacy strategy is:

- All textual and other information that may be used to identify a customer is
  encrypted; with one encryption key per customer. Not even user names are left
  unencrypted. So instead of storing user names directly in the database we are
  storing a hashed version of the user name, so when a user logs in, the user
  name is hashed and then matched against the user names in the database.
- The keys to decrypt data are stored encrypted; one copy per user with access;
  encrypted with a private/public key pair associated with each user.
- The private key per user is stored encrypted, with the users login password
  as passphrase.
- On login, users must provide their user name and passwords; which enables us
  to load the relevant keys.
- To keep keys accessible during an active session, they are stored as part of
  the session state --- but encrypted, with a randomly generated key provided
  to the client in a cookie, to keep beside the session identifier.


Implementation notes
====================

Encrypted fields on models are accessed using the attribute name
``<fieldname>_plain`` instead of just ``fieldname`` and then
encryption/decryption is handled automatically.

The ``EncryptionMiddleware`` is used to manage having encryption state in a
thread-local while processing requests, and otherwise split between encrypted
session-state and a cookie.

Objects with encrypted fields must override method ``get_encryption_id()`` to provide an encryption key identifier.
