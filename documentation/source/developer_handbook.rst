******************
Developer Handbook
******************


System requirements
===================

The servers on which the software is currently deployed run Ubuntu 14.04 LTS, and this is also the recommended development environment.

Using other Unix-like systems should be possible, though we cannot provide specific lists of package names to install for those.

Windows is not supported.  At least some of the third-party Python libraries used involve C extensions that are distributed in source code form, which are difficult to install under Windows.\ [#compiler]_  Various scripts are written as Bash shell-scripts.  It may be *possible* to run the software under Windows, but running it in a Linux VM is likely to be a simpler solution.

.. [#compiler] According to Python documentation, under Windows, extensions should preferably be compiled with the same version of Microsoft Visual C++ as used to compile the Python interpreter.


Repository root folder structure
================================

The code is split up into four major components:

- :file:`documentation/`: This documentation.
- :file:`energymanager/`: Energy Manager. An example Energy Management System
  based on the GridPlatform.
- :file:`gridagentserver/`: GridAgent Server code base.
- :file:`gridagentserver-protocol/`: GridAgent Server protocol code (used by GridAgent Server).
- :file:`gridplatform/`: The GridPlatform code base.
- :file:`legacy/`: GridPlatform 2.0 code base.
- :file:`qunit/`: QUnit (http://qunitjs.com/).
- :file:`requirements/`: PyPI requirement files.
- :file:`scripts/`: Scripts for easing the used of the system once deployed.
- :file:`static/`: Static website assets.
- :file:`templates/`: Top level Django templates that did not fit anywhere else.


Installing needed software
==========================


"Global" software installation
------------------------------

For local development, you will need:

* Python 2.7.
* virtualenv to enable "local" installation of Python libraries.
* An appropriate C-compiler/build tools and Python development headers, to support installation of Python libraries that include C-extensions.
* PostgreSQL and development headers for building a client library.  The PostgreSQL DBMS is used for deployment, and due to subtle differences between DBMS behavior, using the same locally simplifies development.\ [#dbms]_
* Memcached and development headers for building a client library.  Memcached is used for "cache" and for communicating computed results from background tasks to the web-part.
* libjpeg and development headers to support resizing uploaded images.
* The RabbitMQ message queue server, used to schedule background tasks.
* LaTeX and various TeX packages used for building PDF reports.

.. [#dbms] This is a tradeoff.  Using different database systems may help ensure that the application can later be deployed with a different DBMS for production --- but the "overhead" can be significant.  Use of the Django ORM for database access which *should* preserve this portability, though database schema migrations in particular can be difficult to express without "raw" SQL.

On a computer with Ubuntu 14.04 LTS, this can all be installed with::

   sudo apt-get install \
     python-virtualenv \
     virtualenvwrapper \
     python-dev \
     build-essential \
     libgmp-dev \
     postgresql \
     libpq-dev \
     memcached \
     libmemcached-dev \
     libjpeg-dev \
     rabbitmq-server \
     texlive-latex-recommended \
     texlive-xetex \
     fonts-linuxlibertine \
     ttf-mscorefonts-installer \
     texlive-latex-extra \
     texlive-science \
     texlive-fonts-recommended

On deployment, you will also need:

* nginx (or a different HTTP-server) to serve "static" files, handle SSL and communicate with the backend WSGI server.
* A local mail server, to enable the system to send error mails and any other emails.  We use Postfix.

On a computer with Ubuntu 14.04 LTS, this can all be installed with::

   sudo apt-get install \
     nginx \
     postfix


Python packages
---------------

Create virtual Python environment and set the current directory as "working directory" for it::

   mkvirtualenv gridportal
   setvirtualenvproject

Various Python packages are specified in ``requirements/base.txt``, ``requirements/local.txt`` and ``requirements/production.txt``; including short comments on what they do/what we use them for.  For development, the "base" and "local" packages should be installed::

   pip install --requirement=requirements/local.txt

This will take some time, as a number of packages are downloaded, and some C-extensions compiled.

To later use this virtual Python environment::

   workon gridportal


Setting up a database server locally
====================================

For development, the current user needs to be able to create and delete databases, as a "new" database is created and destroyed for unit test runs.
The easiest option is to make the current user a PostgreSQL superuser::

   sudo -u postgres createuser --superuser $USER

If/when the current user is PostgreSQL superuser, creating the database with the current user as owner is simple::

   createdb --encoding=utf-8 portal

With the Python virtual environment with Django and other packages installed active (``workon gridportal``), database the tables may be set up::

   ./manage.py syncdb --noinput
   ./manage.py migrate --all


.. _developer-handbook-scripts-and-commands:

Scripts and commands
====================

To get started/run the software locally, you will need to use:

* ``./manage.py runserver``: Run the Django development server.  By default, it will listen on port 8000.
* ``./manage.py celery worker``: Run a Celery worker process.  This is used for asynchroneous/background tasks like collecting data for graphs or compiling PDF reports.

For other commands that are built-in or provided by third-party Django apps, refer to their respective documentation.


Custom Django management commands
---------------------------------

* ``./manage.py generate_cache``: Generate the five-minute-/hour-"cache" for accumulated data sources.
* ``./manage.py get_agent_events``: Get event log for a specified GridAgent.
* ``./manage.py hickup_detection``: Check for specific outliers/measurement errors in raw data.
* ``./manage.py import_energinet_co2``: Import CO2 data from Energinet.dk to "legacy" indexes.  Requires an Energinet.dk FTP-account, with login-credentials specified in settings ``ENERGINET_CO2_USER`` and ``ENERGINET_CO2_PASS``.
* ``./manage.py setup_nordpool``: Set up "legacy" indexes for import of Nordpool spot prices.
* ``./manage.py import_nordpool``: Import Nordpool spot prices to "legacy" indexes.  Requires a Nordpool FTP-account, with login-credentials specified in settings ``NORDPOOL_USER`` and ``NORDPOOL_PASS``.
* ``./manage.py import_nordpool_spot_prices``: Import Nordpool spot prices to global datasources.  Requires a Nordpool FTP-account, with login-credentials specified in settings ``NORDPOOL_USER`` and ``NORDPOOL_PASS``.
* ``./manage.py ruleengine``: Run the GridPlatform rule engine.
* ``./manage.py send_rules``: Send rules that are evaluated on GridAgents to the GridAgents.
* ``./manage.py check_db_connection``: Check whether Django can connect to the database backend; exits with code 0 for success, 1 for failure.
* ``./manage.py fix_contenttypes_and_permissions``: Add/remove ``ContentType`` entries to match the current set of existing ``Model`` classes; create ``Permission`` instances that exist in code but are missing in the database.  Mismatch may be caused by schema migrations that fail to fire the appropriate events on ``Model`` changes or the addition of new permissions in code.
* ``./manage.py rebuild_group_tree``: Rebuilds the measurement point group trees used in the left menu in GridPortal 2.0. There is a known issue regarding the group tree being corrupted and this a short term fix. This command is run by cron on the servers at every midnight.


Scripts
-------

* ``fixture_hack.sh``: Script to wipe the local cache and database, recreate tables and populate the database with dynamic "fixture" data.
* ``compilemessages.sh``: Call the Django translation system to build ``gettext`` ``.mo`` files from ``.po`` files.
* ``rabbitmq-check.sh``: Check whether there are more than 100 pending messages in any RabbitMQ queues.  This may indicate that task arrive to be run in the background faster than they are currently processed.
* ``run_all_tests.py``: Run unit tests with coverage check.
* ``test_javascript.sh``: Run QUnit unit-tests for JavaScript with PhantomJS.
* ``translate.sh``: Call the Django translation system to create ``.po``-files for the Danish locale for each Django app, open the resulting files with "missing" translations in the default editor, and compile the ``.po``-files to ``.mo``-files.


Makefile rules
--------------

* ``make dist``:  Build ``gridplatform-<branch>-<commit>.tar.gz`` from last commit with ``<branch>-<commit>`` as version.  Use to build untagged "test" releases.
* ``make release``: Build ``gridplatform-<tag>[-<commit>].tar.gz`` from last commit with ``<tag>[-<commit>]`` as version.  Use after git tag to build relases --- the "commit"-part of the version is absent when last commit *is* the tag.
* ``make makemessages``: Run ``django-admin makemessages`` with appropriate parameters to create ``.po``-files for Danish and Spanish translation for each Django app in the project.
* ``make compilemessages``: Run ``django-admin compilemessages`` to generate ``.mo``-files from ``.po``-files for each Django app in the project.
* ``make flake8``: Run the ``flake8`` checker on Python code files changed since the last commit according to git.
* ``make test``: Run unit tests for all Django apps in the project.
* ``make test-rerun``: Run only those unit tests that failed on last test run.
* ``make test-coverage``: Run unit tests with code coverage check.
* ``make selenium-test``: Run normal unit tests *and* Selenium-based tests.  This requires ``chromedriver`` to be present in ``PATH`` or in the current directory.
* ``make tags``, ``make TAGS``: Build Emacs tag file for the Python code.
* ``make test-failures``: Run only those unit tests that failed on last test run.  This version includes workarounds for the test runners failure to correctly identify the failing tests in case of issues with Python module imports.
* ``make parallel-test``: Run unit tests with separate test databases and as separate "jobs" per Django app tested.  This allows tests to be run in parallel, e.g. as ``make parallel-test --jobs=20``.
* ``make scss``: Build ``legacy/website/static/style.css`` from ``legacy/website/static/style.scss`` and the SCSS files in ``legacy/website/static/scss/``.
* ``make html``: Compile documentation to HTML in ``documentation/build/``.
* ``make pdf``: Compile documentation to PDFs as ``GridPlatform.pdf`` and ``GridPlatformDomainModel.pdf``.
* ``make clean``: Delete Python bytecode files, unit test "rerun"-files, log files and the documentation PDF documents.
