# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import functools
import types

from django.utils import translation

from celery import Task
from celery import shared_task

from gridplatform.customers.models import Customer
from gridplatform.users.models import User

from . import _get_override_customer
from . import _get_selected_customer
from . import get_customer
from . import get_user
from . import replace_override_customer
from . import replace_selected_customer
from . import replace_user


def trackuser_task(task_instance):
    """
    Decorate the given Celery task instance to be in the same trackuser context
    on the worker side as it was on the invokation side.

    Usage::

        @trackuser_task
        @task
        class MyTask(Task):
            def run(self, *args, **kwargs):
                ...

    or::

        @trackuser_task
        @task
        def my_task(*args, **kwargs):
            ...

    :precondition: This decorator can only be used on concrete
        :class:`celery.Task` instances.  So always write the
        ``@trackuser_task`` decorator above the ``@task`` decorator.

    :see: :func:`.task`, for a simpler decorator intended for function tasks.
    """
    assert isinstance(task_instance, Task), \
        'precondition violated: @trackuser_task decorator should be on top '\
        'of @task decorator'

    task_instance.__class__.orig_apply_async = \
        task_instance.__class__.apply_async
    orig_run = task_instance.run

    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, **options):
        # Extract customer and user from current trackuser context, and forward
        # these as keyword arguments to L{run()}.
        extra_kwargs = {
            '_customer_id': get_customer().id,
            '_user_id': get_user().id,
        }

        if kwargs is None:
            kwargs = extra_kwargs
        else:
            assert '_customer_id' not in kwargs
            assert '_user_id' not in kwargs
            kwargs.update(extra_kwargs)

        return self.orig_apply_async(
            args=args, kwargs=kwargs, task_id=task_id, producer=producer,
            link=link, link_error=link_error, **options)

    def run(*args, **kwargs):
        # Runs C{run()} in a trackuser context similar to the one of the
        # request in which the task invocation was enqueued.
        customer = Customer.objects.get(id=kwargs.pop('_customer_id'))
        user = User.objects.get(id=kwargs.pop('_user_id'))
        with replace_override_customer(customer), replace_user(user):
            return orig_run(*args, **kwargs)

    # In production environments Celery behaves different than in unit-test. In
    # particular:
    #
    #   - If apply_async is not a bound method on class level it won't be bound
    #     at all for function based tasks.
    #
    #   - If apply_async is not assigned on class level it won't be called at
    #     all for function based tasks.
    task_instance.__class__.apply_async = types.MethodType(
        apply_async, task_instance, task_instance.__class__)

    # ahh, our run must be bound/unbound the same way their run is...
    task_instance.run = run

    return task_instance


def _context_from_kwargs(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        user_id = kwargs.pop('_user_id')
        if user_id is not None:
            user = User.objects.get(id=user_id)
        else:
            user = None
        override_customer_id = kwargs.pop('_override_customer_id')
        if override_customer_id is not None:
            override_customer = Customer.objects.get(id=override_customer_id)
        else:
            override_customer = None
        selected_customer_id = kwargs.pop('_selected_customer_id')
        if selected_customer_id is not None:
            selected_customer = Customer.objects.get(id=selected_customer_id)
        else:
            selected_customer = None
        language = kwargs.pop('_language')
        with replace_user(user), \
                replace_override_customer(override_customer), \
                replace_selected_customer(selected_customer), \
                translation.override(language):
            return f(*args, **kwargs)
    return wrapped


def _context_to_kwargs():
    return {
        '_user_id': getattr(get_user(), 'id', None),
        '_override_customer_id': getattr(_get_override_customer(), 'id', None),
        '_selected_customer_id': getattr(_get_selected_customer(), 'id', None),
        '_language': translation.get_language(),
    }


class TaskBase(Task):
    abstract = True

    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, **options):
        extra_kwargs = _context_to_kwargs()
        if kwargs is None:
            kwargs = extra_kwargs
        else:
            assert all([key not in kwargs for key in extra_kwargs.keys()])
            kwargs.update(extra_kwargs)
        return super(TaskBase, self).apply_async(
            args=args, kwargs=kwargs, task_id=task_id, producer=producer,
            link=link, link_error=link_error, **options)

    def set_progress(self, current, total):
        self.update_state(
            state='PROGRESS',
            meta={
                'task_user_id': get_user().id,
                'current': current,
                'total': total,
            })


def task(*args, **kwargs):
    """
    Wrapper/replacement for the Celery ``@shared_task`` decorator that will run
    the task in the same ``user``/``customer``/``selected_customer`` context
    that was active on the invocation side.

    Takes the same parameters as ``@shared_task``.  Reserves the keyword
    arguments ``_user_id``, ``_customer_id`` and ``_selected_customer_id``.

    Usage::

        @task
        my_task(*args, **kwargs):
            ...
    """
    def create_task(**options):
        base = options.pop('base', TaskBase)
        assert issubclass(base, TaskBase)

        def wrap_callable(f):
            return shared_task(base=base, **options)(_context_from_kwargs(f))
        return wrap_callable

    if len(args) == 1 and callable(args[0]):
        assert len(kwargs) == 0
        return create_task()(args[0])
    else:
        assert len(args) == 0
        return create_task(**kwargs)
