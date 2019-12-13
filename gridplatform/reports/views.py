# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from collections import namedtuple
import base64
import datetime

from celery import Task
from celery.result import AsyncResult
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.encoding import python_2_unicode_compatible
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from django.views.generic import FormView
from celery.task.control import inspect
import pytz

from gridplatform.trackuser import get_customer
from gridplatform.users.decorators import auth_or_error
from gridplatform.utils.views import json_response
from gridplatform.utils.views import JsonResponse
from gridplatform.utils.views import JsonResponseBadRequest

from .models import Report


def is_queue_too_long(max_tasks, task_name):
    """
    Are too many tasks with a given name enqueued?

    Some tasks risk taking long to process.  For good measure users
    tend to reenqueue tasks that take too long.  Having the respective
    views introduce a maximum ensures that all successfully enqueued
    tasks are eventually processed, and there will eventually be room
    for enqueuing more tasks.

    :param max_tasks:  The threshold of too many tasks.
    :param task_name: The name of the tasks to query.

    :return: ``True`` if the scheduled task queue holds more than
        ``max_tasks`` tasks with the name ``task_name``. Otherwise
        returns ``False``
    """
    i = inspect()
    scheduled = i.scheduled()
    queue_length = 0
    for tasks in scheduled.values():
        for task in tasks:
            if task['name'] == task_name:
                queue_length += 1

    return queue_length > max_tasks


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


ReportInfo = namedtuple('ReportInfo', ['title', 'content_type', 'data'])


class StartReportView(FormView):
    """
    Generic view to, when configured with a form class and a Celery task, start
    the Celery task with data from the form.

    :cvar task: A Celery task set by concrete start view.
    """
    task = None

    def get_task(self):
        """
        Return the Celery task to run.
        """
        if self.task:
            return self.task
        else:
            raise ImproperlyConfigured('No task to run.  Provide a task.')

    def get_task_data(self, form):
        """
        Must be overwritten by subclass. This methods returns the data for
        the task itself, it must not contain any sensitive data!  The
        data must be serializable.

        NOTE: Django querysets are not serializable.
        """
        raise NotImplementedError('Subclass must implement this method')

    def start_task(self, data):
        """
        Start the Celery task.

        :param data: Single argument delegated to ``delay()`` method
            of task.
        """
        task = self.get_task()

        if not isinstance(task, Task):
            raise ImproperlyConfigured('Provided task is not a Celery Task.')

        return task.delay(data)

    def form_valid(self, form):
        """
        Start Celery task with data from given form; called when the form
        is found valid.

        :param form: The given form
        """
        data = self.get_task_data(form)
        async = self.start_task(data)
        return JsonResponse({
            'task_id': async.id,
            'status': async.status,
        })

    def form_invalid(self, form):
        """
        Format form errors as JSON error response.
        """
        return JsonResponseBadRequest(form.errors)


class TaskForm(forms.Form):
    """
    Form for identifying a task.

    :ivar task_id:  The id of the task identified.
    """
    task_id = forms.CharField()


class FinalizeReportView(FormView):
    """
    A :class:`~django.views.generic.FormView` for generating a report
    from the result of a :class:`celery.Task`.

    The report is likely to contain encrypted information wich is not
    available outside the request context, so the task could not have
    done the compilation itself.
    """
    form_class = TaskForm

    def generate_report(self, data, timestamp):
        """
        Generate a report and return as ReportInfo.  Subclasses must implement
        this.
        """
        raise NotImplementedError('Subclass must implement this method')

    def form_valid(self, form):
        """
        Generate the report for the task output.
        """
        task_id = form.cleaned_data['task_id']
        async = AsyncResult(task_id)
        if not async.successful():
            return JsonResponseBadRequest({'task_status': async.status})
        now = datetime.datetime.now(pytz.utc)
        generated = self.generate_report(async.result, now)
        if not isinstance(generated, ReportInfo):
            raise ImproperlyConfigured(
                'Generated not an instance of ReportInfo.')
        data_formats = {content_type: n
                        for n, content_type in Report.DATA_FORMAT_CHOICES}
        report = Report.objects.create(
            customer=get_customer(),
            title_plain=generated.title,
            generation_time=now,
            data_format=data_formats[generated.content_type],
            data_plain=base64.encodestring(generated.data),
            size=len(generated.data)
        )
        return JsonResponse({
            'id': report.id,
            'title': report.title_plain,
            'size': report.size,
            'url': reverse(
                'reports-serve',
                kwargs={'id': report.id, 'title': report.title_plain})
        })

    def form_invalid(self, form):
        """
        Format form errors as JSON error response.
        """
        return JsonResponseBadRequest(form.errors)


@auth_or_error
@require_GET
def serve(request, id, title=None):
    """
    View for serving an existing :class:`.Report` as a file for
    download.
    """
    report = get_object_or_404(Report, id=id)
    content_type = dict(Report.DATA_FORMAT_CHOICES)[report.data_format]
    return HttpResponse(base64.decodestring(report.data_plain),
                        content_type=content_type)


@auth_or_error
@json_response
@require_POST
def status(request):
    """
    View for querying the status of a scheduled task.

    :param request: :class:`TaskForm` is used to extract the task id from
        ``request.POST``.

    :raise CeleryError: If any exception was raised by the task.
        Effectively this means that an error inside the task will be
        reported as an error during the given request.

    :return: A JSON response containing a dictionary with status
        information about the given task.  If status is
        ``"PROGRESS"``, the JSON object will have the members
        ``task_id``, ``status``, ``result``.  For other non failed
        statuses the ``result`` member is absent.  The contents of
        ``result`` is task specific, but may be used to report
        progress.  If the submitted :class:`TaskForm` did not
        validate, its ``errors`` member is returned as a JSON object.

    See also the :func:`gridplatform.utils.views.json_response` decorator.
    """
    form = TaskForm(request.POST)
    if form.is_valid():
        task_id = form.cleaned_data['task_id']
        async = AsyncResult(task_id)
        if async.failed():
            # NOTE: The available "traceback" is a string, not a
            # traceback-object, hence "re-raising" with that as traceback
            # context will not work
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
    else:
        return form.errors
