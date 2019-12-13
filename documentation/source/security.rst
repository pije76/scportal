********
Security
********

Various security mechanisms are used in order to maximise the security of the
GridPlatform. They are explained in this chapter.


Secure Socket Layer (SSL)
=========================
When deploying GridPlatform to a production environment, the web servers must
always be set up with valid SSL certificates and web server communication must
only allow SSL connections from clients.


Cross Site Request Forgery (CSRF) protection
============================================
CRSF protection is part of the Django framework. Refer to the Django documentation for details (https://docs.djangoproject.com/en/dev/ref/csrf/).


Model Permissions
=================
The permission and groups available in ``django.contrib.auth`` are use
implement access control. Refer to the Django documentation for details.


Other Access Control mechanisms
===============================

The user model has a ``user_type`` field, which in GridPortal 2.0 is used for access control purposes.


API tokens
==========

To allow secure access to the GridPlatform via the REST API an API key scheme
has been implemented. API users can be created using the Energy Manager
administration site and a key generated for them. The key is only shown on
creation, and if in any way forgotten a new must be generated for that user.

These keys are as confidential as user names as password as they enable the
owner to login and decrypt the data belonging to the customer associated with that user.

In the case of provider API users the user has the ability to decrypt all data
for all customers belonging to that provider.
