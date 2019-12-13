#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from cStringIO import StringIO

from fabric.api import cd
from fabric.api import env
from fabric.api import execute
from fabric.api import get
from fabric.api import local
from fabric.api import parallel
from fabric.api import put
from fabric.api import roles
from fabric.api import run
from fabric.api import runs_once
from fabric.api import serial
from fabric.api import task


env.user = 'portal'

env.roledefs['web'] = [
    '{}.grid-manager.com'.format(name)
    for name in ('web1', 'web2', 'web3', 'web4', 'web5')
]
env.roledefs['gas'] = ['gas.grid-manager.com']
env.roledefs['engine'] = ['engine.grid-manager.com']

env.roledefs['staging'] = ['192.168.0.150']
env.roledefs['experimental'] = ['experimental.grid-manager.com']
#env.roledefs['production'] = ['portal@185.121.173.146']
env.roledefs['production'] = ['portal@smarterconsumers.dk']

SCRIPT_DIR = 'gridplatform/scripts/production_nordic'


@runs_once
def get_version():
    return local('git describe --always', capture=True)


@runs_once
def get_distfilename():
    return 'gridplatform-{}.tar.gz'.format(get_version())


@runs_once
def build_distfile(distfilename):
    local('make {}'.format(distfilename))


@parallel
@roles('web', 'gas', 'engine')
def upload(distfilename):
    put(distfilename, distfilename)


def unpack(distfilename):
    run('rm -rf gridplatform.old')
    run('mv gridplatform gridplatform.old')
    run('tar xzf {}'.format(distfilename))


def pip_setup():
    run('source $HOME/ve/bin/activate && ' +
        'pip install -r gridplatform/requirements/production.txt')


@parallel
@roles('web')
def stop_web():
    with cd(SCRIPT_DIR):
        run('./stop_celery.sh')
        run('./stop_uwsgi.sh')


@parallel
@roles('web')
def unpack_web(distfilename):
    execute(unpack, distfilename)


@parallel
@roles('web')
def setup_web():
    execute(pip_setup)
    with cd(SCRIPT_DIR):
        run('./manage.sh collectstatic --noinput')
        run('./manage.sh compress')


@parallel
@roles('web')
def start_web():
    with cd(SCRIPT_DIR):
        run('./start_celery.sh')
        run('./start_uwsgi.sh')


@roles('engine')
def stop_engine():
    with cd(SCRIPT_DIR):
        run('./stop_reports.sh')
        run('killall python')


@roles('engine')
def unpack_engine(distfilename):
    execute(unpack, distfilename)


@roles('engine')
def setup_engine():
    execute(pip_setup)


@roles('engine')
def start_engine():
    with cd(SCRIPT_DIR):
        run('./start_reports.sh')
        run('./manage.sh ruleengine')


@roles('gas')
def stop_gas():
    run('gridplatform/gridagentserver/stop.sh')


@roles('gas')
def unpack_gas(distfilename):
    execute(unpack, distfilename)


@roles('gas')
def setup_gas():
    execute(pip_setup)
    run('source $HOME/ve/bin/activate && ' +
        'pip install -r gridplatform/gridagentserver/requirements.txt')
    with cd(SCRIPT_DIR):
        run('./manage.sh syncdb --migrate')
        run('./manage.sh fix_contenttypes_and_permissions')


@roles('gas')
def start_gas():
    run('export DJANGO_CONFIGURATION=Prod && ' +
        'source $HOME/ve/bin/activate && ' +
        '$HOME/gridplatform/gridagentserver/start.sh')


@task
@serial
def deploy_nordic():
    """
    Deploy to the GridManager Nordic cloud.
    """
    distfilename = get_distfilename()
    execute(build_distfile, distfilename)
    execute(upload, distfilename)

    execute(stop_engine)
    execute(unpack_engine, distfilename)

    execute(stop_gas)
    execute(unpack_gas, distfilename)
    execute(setup_gas)
    execute(start_gas)

    execute(setup_engine)
    execute(start_engine)

    execute(stop_web)
    execute(unpack_web, distfilename)
    execute(setup_web)
    execute(start_web)


def deploy_singleserver():
    distfilename = get_distfilename()
    execute(build_distfile, distfilename)
    put(distfilename, distfilename)
    # stop
    with cd('gridplatform/scripts/production'):
        run('./stop_celery.sh', warn_only=True)
        run('./stop_uwsgi.sh', warn_only=True)
        run('./stop_reports.sh', warn_only=True)
    run('gridplatform/gridagentserver/stop.sh', warn_only=True)
    run('killall python', warn_only=True)
    # unpack
    execute(unpack, distfilename)
    # setup
    execute(pip_setup)
    run('source $HOME/ve/bin/activate && ' +
        'pip install -r gridplatform/gridagentserver/requirements.txt')
    with cd('gridplatform/scripts/production'):
        run('./manage.sh syncdb --migrate')
        run('./manage.sh fix_contenttypes_and_permissions')
        run('./manage.sh collectstatic --noinput')
        run('./manage.sh compress')
    # start
    with cd('gridplatform/scripts/production'):
        run('./start_celery.sh')
        run('./start_uwsgi.sh')
        run('./start_reports.sh')
        run('./manage.sh ruleengine')
    run('export DJANGO_CONFIGURATION=Local && ' +
        'source $HOME/ve/bin/activate && ' +
        '$HOME/gridplatform/gridagentserver/start.sh')


@task
@roles('staging')
def deploy_staging():
    execute(deploy_singleserver)


@task
@roles('experimental')
def deploy_experimental():
    execute(deploy_singleserver)


@task
@roles('production')
def deploy_production():
    execute(deploy_singleserver)


@parallel
@roles('web', 'gas', 'engine', 'staging', 'experimental', 'iberia')
def deployed_versions():
    data = StringIO()
    get('gridplatform/gridplatform/__init__.py', data)
    for line in data.getvalue().split('\n'):
        if line.startswith('__version__'):
            version = line.split()[-1]
            return version
    return None


@task
def check_versions():
    """
    Check software versions currently deployed.
    """
    versions = execute(deployed_versions)
    for host, version in sorted(versions.items()):
        print '{}: {}'.format(host, version)
