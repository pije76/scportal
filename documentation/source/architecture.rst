*********************
Software Architecture
*********************

The GridPlatform is an energy management platform, meaning it supposed to be
the foundation on which to build Energy Management System (EMS) software
products. Therefore there is a natural overall layered archicture with the
GridPlatform at the bottom.

The now legacy GridPortal 2.0 has been integrated with GridPlatform using a few
wrappers and can therefore be seen as one instance of an EMS. However, as it is
legacy it does have some of its own concepts that are not part of the
GridPlatform as well as different interpretation of such concepts. One example
is that the GridPortal 2.0 has a generic concept of ``indexes`` and the
GridPlatform has a concept of ``tariffs``. Price indexes in GridPortal 2.0 are
used similarly to how tariffs are used in the GridPlatform but are in no way
connected, nor should they be. The data models in the GridPlatform are superior
to those in GridPortal 2.0, and no further development, apart from bug fixes, are
planned for GridPortal 2.0.

A small EMS product, simply called Energy Manager, has been built on top of the
GridPlatform. The original vision was for this to eventually replace GridPortal
2.0, however, as development was cancelled in early stages this product turned
into a GridPlatfrom proof-of-concept implementation, and was used to drive the
further development of the GridPlatform.

The GridPlatform is intended to be heavily used via REST web services, so
future EMS software products may be implemented on top of the GridPlatform
using purely this interface, or they can built on top of it using Django like
the Energy Manager example does. Or indeed a mix of both if that makes the most
sense.

Energy Manager and GridPortal only use the Django Interface. Asynchronous HTTP
requests made by them are made using their own Django views.

The overall architecture can be visualised as follows:

.. code-block:: none

                     +---------------------------------+
                     | Energy Manager | GridPortal 2.0 |
    +--------------------------------------------------+
    |    REST API    |           Django API            |
    |           GridPlatform                           |
    +--------------------------------------------------+


Logging
=======

- Web traffic logging is done by ``nginx`` and the logs can normally be found
  in `/var/log/nginx`.

- PostgreSQL logs can normally be found in `/var/log/postgreqsql`

- Django and Celery error messages are not logged on the servers but are
  e-mailed directly to the list of administrators listed in the Django settings
  file.

- GridAgent Server logs are located in the GridAgent Server directory.

.. _architecture-cloud-architecture:

******************
Cloud Architecture
******************
The GridPlatform is designed to run in a cloud infrastructure for easy
expansion of resources as it becomes necessary. It is highly scalable and is
meant to be run in a distributed fashion across many servers. However, it is
also flexible in its deployment allowing for easy single server setups as well,
and can run on any Linux system with enough resources running PostgreSQL. All
third part software used are free and open source.

The deployment architecture consists of the following component types
responsible for running the listed software services:


Web server load balancer
========================
Only used in a multiple server deployment.


Web server
==========

- Nginx: Web server.

- uWSGI: WSGI compliant application server for running the GridManager
  GridPlatform Django application.

- Memcached: Distributed object caching system.


Message queue server
====================

- RabbitMQ: AMQP compliant message queue server.


Database server
===============

- PostgreSQL


Heavy computation server
========================

- Celery: Distributed task queue. The GridManager GridPlatform celery worker
  threads run on these types of servers.

- Cache Generator: GridManager script for condensing energy measurements in
  to 1 hour and 5 minute periods.


GridAgent Server
================

- Running the GridManager GridAgent Server Python application


GridAgent Rules Server
======================

Rule monitoring, execution and transmission.

- GridAgent Rule Engine: GridManager Django application that continuously
  checks the specified rule constraints that customers have specified and runs
  specified actions when needed.
  *Note: This is not a distributed service. Only one rule engine should be
  running at any given time or actions might get triggered twice.*

- GridAgent Rules Updater: GridManager script for transmitting specified
  rules to the GridAgents. Meant to run at the beginning of each clock hour.
  *Note: Only rules that can be handled solely by a single GridAgent are
  transmitted.*


Periodic Task Server
====================

The services listed below are all meant to be run as only one instance each in
the cloud. They can of course be run on serveral different servers, though none
of them are very computation nor memory hungry.

- Nord Pool Spot prices import: GridManager script for importing spot prices
  from the Nord Pool FTP server.

- Energinet.dk |CO2| index import: GridManager script for importing |CO2|/kWh
  data from Energinet.dk.

  .. |CO2| replace:: CO\ :sub:`2`

- Erroneous Peak Remover: A bug in old version of the GridManager GridPoint 3
  phase meter caused erroneous measurements being transmitted. A GridManager
  detects these abnormal measurements and deletes them.
  *Note: Must be run before cache generation to prevent the erroneous
  measurements affecting the cached values.*

- Clear Django sessions: A Django script for cleaning the database of any
  dead sessions.


Sharding
========

To support really large amounts of data, *sharding* should be
considered. Partitioning of the data is trivial: It is naturally divided on
customers. Customer data can then be distributed across many databases,
constrained by keeping data related to the same customer in the same database.

The web servers will then use a routing algorithm to use the correct database
for each logged in user. Many such schemas exists and libraries exists for
implementing such functionality trivial.

As we were nowhere near an amount of data that would necessitate sharding, it
has not been implemented; though the architecture is built with it in mind,
allowing future developers to add sharding later.
