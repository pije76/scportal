# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import urlparse

from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.utils.encoding import python_2_unicode_compatible
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login
from django.contrib.auth.views import logout_then_login
from django.contrib.sites.models import get_current_site

from celery.result import AsyncResult
import celery.task.control

from gridplatform.users.decorators import auth_or_error
from gridplatform.utils.views import render_to, json_response
from gridplatform.trackuser import get_user
from gridplatform.trackuser import get_customer


@sensitive_post_parameters()
@csrf_protect
@never_cache
@render_to('website/login.html')
def login(request):
    """
    Displays the login form and handles the login action.
    """
    # based on django.contrib.auth.views.login --- "simplified" by removing
    # parameters, call to load encryption keys added.
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')

    # HACK: ONLY FOR USE ON GREENTECH SERVERS
    # if request.method == "POST" or "username" in request.GET:
    #     if 'username' in request.GET:
    #         form = AuthenticationForm(data=request.GET)
    #     else:
    #         form = AuthenticationForm(data=request.POST)

    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            netloc = urlparse.urlparse(redirect_to)[1]

            # Use default setting if redirect_to is empty
            if not redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL

            # Heavier security check -- don't allow redirection to a different
            # host.
            elif netloc and netloc != request.get_host():
                redirect_to = settings.LOGIN_REDIRECT_URL

            # Okay, security checks complete. Log the user in.
            auth_login(request, form.get_user())

            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()

            return HttpResponseRedirect(redirect_to)
    else:
        form = AuthenticationForm(request)

    request.session.set_test_cookie()

    current_site = get_current_site(request)

    return {
        'form': form,
        'REDIRECT_FIELD_NAME': redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }


@never_cache
def logout(request):
    return logout_then_login(request)


def find_home(request):
    if get_user().is_staff:
        return redirect('manage_customers-list')
    else:
        return redirect('display_widgets-dashboard')


@python_2_unicode_compatible
class CeleryError(Exception):
    """
    Wrapper for exceptions from Celery --- Celery provides an Exception object
    and a string representation of a traceback.
    """
    def __init__(self, wrapped, traceback):
        self.wrapped = wrapped
        self.traceback = traceback

    def __str__(self):
        return '{}\n{}'.format(self.wrapped, self.traceback)


@auth_or_error
@json_response
@require_POST
def task_status(request):
    """
    Given a celery task ID the status of that task is returned.

    If the task has failed, this raises an exception to trigger the normal
    Django error reporting.
    """
    task_id = request.POST['task_id']
    async = AsyncResult(task_id)

    # We have experienced async.failed() being false while async.result
    # contained an AssertionError instance.  Hence the isinstance check.
    if async.failed() or isinstance(async.result, Exception):
        # NOTE: The available "traceback" is a string, not a traceback-object,
        # hence "re-raising" with that as traceback context will not work

        if async.status == 'REVOKED':
            return {
                'task_id': async.id,
                'status': async.status
            }
        else:
            raise CeleryError(async.result, async.traceback)

    if async.status == "PROGRESS":
        return {
            'task_id': async.id,
            'status': async.status,
            'result': async.result,
        }
    else:
        return {
            'task_id': async.id,
            'status': async.status,
        }


@auth_or_error
@json_response
@require_POST
def cancel_task(request):
    """
    Kills a task with the given ID, if the logged in user
    is the same user that started the task
    """
    task_id = request.POST['task_id']
    async = AsyncResult(task_id)
    success = False
    if async and isinstance(async.result, dict) and \
            get_user().id == async.result.get('task_user_id', None):
        # NOTE: The Celery documentation recommends against using termitate
        # programmatically --- the worker in question is terminated, though it
        # may have started processing a different task when the termination
        # signal is delivered.  As we have enabled CELERY_ACKS_LATE, the harm
        # in that particular case is limited --- any next/different task being
        # processed by the terminated worker will be retried by another worker,
        # rather than being lost (as it would have been without
        # CELERY_ACKS_LATE)...
        celery.task.control.revoke(task_id, terminate=True)
        success = True
    return {
        'success': success
    }


@auth_or_error
@json_response
@require_POST
def json_task_result(request):
    """
    Given a celery task ID of a completed task, the result is returned. The
    result from the task must be serializable to JSON.
    """
    task_id = request.POST['task_id']
    async = AsyncResult(task_id)
    assert async.successful(), async.traceback

    # HACK: Production units cannot be displayed in tasks because they are
    # encrypted.  So we replace them here with their decrypted counter parts.
    def replace_production_unit(s, l):
        return s.replace(
            'production_%s' % l, getattr(
                get_customer(),
                'production_%s_unit_plain' % l))

    for letter in ['a', 'b', 'c', 'd', 'e']:
        try:
            async.result['options']['yaxis']['title'] = \
                replace_production_unit(async.result[
                    'options']['yaxis']['title'], letter)
        except KeyError:
            pass
        try:
            async.result['options']['xaxis']['title'] = \
                replace_production_unit(async.result[
                    'options']['xaxis']['title'], letter)
        except KeyError:
            pass
    return async.result
