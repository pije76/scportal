**********
Deployment
**********

Fabric is used to management server deployment. For Fabric usage please
refer to https://pypi.python.org/pypi/fabric. The fabric rules in
:file:`fabfile.py` explains how to deploy to single server targets (e.g. the
target `deploy_staging`) as well as cloud deployment (the target
`deploy_production`). In cloud deployment please note the order in which
the various services are started and stopped. For example, it is not
recommended to start the upgrade of the database while over services that
depend on it are still running.


Virgin deployment
==================

If you are deploying to a new server with clean database you want to create a
staff user for administrators to use.

As with most Django projects the first user is added using the following command:

.. code-block:: none

    ./manage.py createsuperuser

The command creates a user with both `is_staff = True` and `is_superuser =
True`.


Django admin
------------
Staff users (i.e. users with `is_staff = True`) can log into the Django admin
website at `/django_admin`.

The Django admin site allows the administrator to create providers and provider
users, as well as administering groups and permissions. That is all that is
supposed to be done from this site. Once provider administrators have been
created they can log in and administer the rest them using either GridPortal
2.0 or Energy Manager.


Web server locale setup
=======================

Ensure that the locale specified in
:file:`gridplatform/scripts/production/start_uwsgi.sh`
is unicode/utf-8-compatible and actually exists on server.
Otherwise, when interacting with the file system (e.g. when handling file
uploads) you will experience errors on the form (if the file name contains non-ASCII characters):

.. code-block:: none

    UnicodeEncodeError: 'ascii' codec can't encode character u'\xf3' in position 46: ordinal not in range(128)


Crontab
=======

Please refer to :ref:`developer-handbook-scripts-and-commands` for descriptions
of the scripts used in the crontabs listed in this section.

Single server
-------------
For single server deployment `crontab` contains the following:

.. code-block:: none

5 0 * * * $HOME/gridplatform/scripts/production/manage.sh clearsessions
15 * * * * $HOME/gridplatform/scripts/production/manage.sh hickup_detection --previous-hour --quiet && ./gridplatform/scripts/production/manage.sh generate_cache --hours_back=2 --verbosity=0
15 7 * * * $HOME/gridplatform/scripts/production/manage.sh import_nordpool
15 12 * * * $HOME/gridplatform/scripts/production/manage.sh import_nordpool
15 14 * * * $HOME/gridplatform/scripts/production/manage.sh import_nordpool
15 16 * * * $HOME/gridplatform/scripts/production/manage.sh import_nordpool
15 22 * * * $HOME/gridplatform/scripts/production/manage.sh import_nordpool
15 7 * * * $HOME/gridplatform/scripts/production/manage.sh import_nordpool_spot_prices
15 22 * * * $HOME/gridplatform/scripts/production/manage.sh import_nordpool_spot_prices
1 0 * * * $HOME/gridplatform/scripts/production/manage.sh import_energinet_co2
*/15 * * * * $HOME/gridplatform/scripts/production/manage.sh import_energinet_co2 $(date +\%Y-\%m-\%d)
*/15 * * * * $HOME/gridplatform/scripts/production/manage.sh send_rules
5 * * * * $HOME/gridplatform/gridagentserver/gas-check.sh
15 * * * * $HOME/gridplatform/rabbitmq-check.sh
1 0 * * * $HOME/gridplatform/scripts/production/manage.sh rebuild_group_tree
@reboot while ! $HOME/gridplatform/scripts/production/manage.sh check_db_connection ; do sleep 10; done; $HOME/start.sh

# Portal
@reboot while ! $HOME/gridplatform/scripts/production/manage.sh check_db_connection ; do sleep 10; done; $HOME/start.sh > /dev/null
5 0 * * * $HOME/gridplatform/scripts/production/manage.sh clearsessions
15 * * * * $HOME/gridplatform/scripts/production/manage.sh hickup_detection --previous-hour --quiet && ./gridplatform/scripts/production/manage.sh generate_cache --hours_back=2 --verbosity=0
*/15 * * * * $HOME/gridplatform/scripts/production/manage.sh send_rules
15 * * * * $HOME/gridplatform/rabbitmq-check.sh
1 0 * * * $HOME/gridplatform/scripts/production/manage.sh rebuild_group_tree

# GAS
@reboot while ! $HOME/gridplatform/scripts/production/manage.sh check_db_connection ; do sleep 10; done; sleep 10; $HOME/restart-gas.sh
5 * * * * export DJANGO_CONFIGURATION=Prod && $HOME/gridplatform/gridagentserver/gas-check.sh
10 * * * * if [ $(ps -ho rss $(cat $HOME/gridplatform/gridagentserver/twistd.pid)) -gt 500000 ]; then $HOME/restart-gas.sh; fi

For cloud deployment
--------------------

For cloud deployment, here follows the crontab for the web, engine and GridAgent servers. For a description of the cloud architecture please refer to :ref:`architecture-cloud-architecture`.

Web server:

.. code-block:: none

    @reboot while ! $HOME/gridplatform/scripts/production_nordic/manage.sh check_db_connection ; do sleep 10; done; cd $HOME/gridplatform/scripts/production_nordic; ./start_gunicorn.sh; ./start_celery.sh


Engine server:

.. code-block:: none

    @reboot while ! $HOME/gridplatform/scripts/production_nordic/manage.sh check_db_connection ; do sleep 10; done; $HOME/gridplatform/scripts/production_nordic/manage.sh ruleengine; $HOME/gridplatform/scripts/production_nordic/start_reports.sh; $HOME/gridplatform/scripts/production_nordic/start_store_data_sanitize.sh
    15 * * * * $HOME/gridplatform/rabbitmq-check.sh
    5 0 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh clearsessions
    15 * * * * $HOME/gridplatform/scripts/production_nordic/manage.sh hickup_detection --previous-hour --quiet && ./gridplatform/scripts/production_nordic/manage.sh generate_cache --hours_back=2 --verbosity=0
    15 7 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh import_nordpool
    15 12 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh import_nordpool
    15 14 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh import_nordpool
    15 16 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh import_nordpool
    15 22 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh import_nordpool
    15 7 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh import_nordpool_spot_prices
    15 22 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh import_nordpool_spot_prices
    1 0 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh import_energinet_co2
    */15 * * * * $HOME/gridplatform/scripts/production_nordic/manage.sh import_energinet_co2 $(date +\%Y-\%m-\%d)
    */15 * * * * $HOME/gridplatform/scripts/production_nordic/manage.sh send_rules
    1 0 * * * $HOME/gridplatform/scripts/production_nordic/manage.sh rebuild_group_tree


GridAgent Server:

.. code-block:: none

    @reboot while ! $HOME/gridplatform/scripts/production_nordic/manage.sh check_db_connection ; do sleep 10; done; cd $HOME/gridplatform/gridagentserver; ./start.sh
    5 * * * * export DJANGO_CONFIGURATION=Prod && $HOME/gridplatform/gridagentserver/gas-check.sh
