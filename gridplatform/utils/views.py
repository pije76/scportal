# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import json
import time
from functools import wraps
from mimetypes import guess_type

from celery.result import AsyncResult
from django import forms
from django.conf import settings
from django.core import urlresolvers
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from django.utils.decorators import available_attrs
from django.utils.functional import cached_property
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.views.generic import RedirectView

from gridplatform.customers.models import Customer
from gridplatform.trackuser import get_user
from gridplatform.trackuser import replace_selected_customer

from . import generic_views


def json_response(view_func):
    """
    Decorator to simplify returning JSON, and make a clear declaration of
    intent.  Use::

        @json_response
        def my_function(response, ...):
            ...

    To have the return value serialised with json and wrapped in a
    HttpResponse.  You may "escape" this by directly returning a HttpResponse,
    e.g. in order to respond with a redirect or an error message.

    :note: Will wrap output in HTML for non-AJAX requests in debug
        mode.  This allows us to use Django Debug Toolbar to check SQL
        queries and other information about the handling of the
        request.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrapper(request, *args, **kwargs):
        data = view_func(request, *args, **kwargs)
        if isinstance(data, HttpResponse):
            return data
        try:
            json_data = json.dumps(data, cls=DjangoJSONEncoder)
        except TypeError as e:
            raise TypeError(b'%s while serializing %r' % (e, data))
        if not settings.DEBUG or request.is_ajax():
            response = HttpResponse(json_data, content_type='application/json')
        else:
            response = render_to_response('utils/json_data.html',
                                          {'data': json_data})
        add_never_cache_headers(response)
        return response
    return wrapper


def json_list_response(view_func):
    """
    Decorator to give filter and pagify in JSON list responses.

    Decorate a function that return a tripple, like::

        @json_list_response
        def json_list_response(request, ...):
            ...
            return (order_map, object_list, template_name)

    where ``order_map`` is a mapping from the name of what to order to
    a function that returns the value of what to order given an
    object.  For example::

        order_map = {
            "name": lambda obj: unicode(obj.name),
            "location": lambda obj: unicode(obj.location.name)}

    and ``object_list`` is a list of objects, say a query set turned
    into a list, and ``template_name`` is a path to a HTML file
    relative to the ``templates/`` directory of your application, where
    the object that this template is instantiated for will be bound to
    the name ``"object"``.
    """
    @json_response
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrapper(request, *args, **kwargs):
        order_map, object_list, template_name = \
            view_func(request, *args, **kwargs)
        options = json_list_options(request)

        if options["search"]:
            object_list = filter(
                lambda obj: obj.satisfies_search(options["search"]),
                object_list)

        if options["order_by"] in order_map:
            object_list.sort(key=order_map[options["order_by"]])
            if options["direction"].lower() == "desc":
                object_list.reverse()

        return {
            "total": len(object_list),
            "data": [render_to_string(template_name,
                                      {"object": obj},
                                      RequestContext(request))
                     for obj
                     in object_list[options["offset"]: options["offset"] +
                                    options["count"]]]}
    return wrapper


class JsonResponse(HttpResponse):
    """
    :class:`~django.http.HttpResponse` specialisation that serialises
    data to a JSON string.
    """
    def __init__(self, data={}, cachable=False):
        content = json.dumps(data, cls=DjangoJSONEncoder)
        super(JsonResponse, self).__init__(
            content, content_type='application/json')
        if not cachable:
            add_never_cache_headers(self)

    def _get_data(self):
        """
        DjangoJSONEncoder formats datetime objects as strings; reading
        them back gives strings.
        """
        return json.loads(self.content)

    def _set_data(self, data):
        self.content = json.dumps(data, cls=DjangoJSONEncoder)

    data = property(_get_data, _set_data)


class JsonResponseBadRequest(JsonResponse, HttpResponseBadRequest):
    """
    A :class:`.JsonResponse` that is also a
    :class:`django.http.HttpResponseBadRequest`.
    """
    pass


class DateLocalEpoch(json.JSONEncoder):
    """
    :class:`json.JSONEncoder` specialization that adds support for
    :class:`datetime.datetime` and :class:`datetime.date`.
    """
    def default(self, o):
        """
        Specialization of :meth:`json.JSONEncoder.default`.

        :param o: The object to be encoded.

        :return: If ``o`` is a :class:`~datetime.datetime` it is
            converted to a naive local timestamp counting milliseconds
            since the epoch.  If ``o`` is a :class:`~datetime.date` it
            is converted to a naive local timestamp at the start of
            that date counting milliseconds since the epoch.  Both
            these encodings are along the lines of what Javascript
            expects.  Otherwise the call is delegated to the super
            implementation.
        """
        if isinstance(o, datetime.datetime):
            naive = timezone.make_naive(o, timezone.get_current_timezone())
            return int(time.mktime(naive.timetuple()) * 1000)
        elif isinstance(o, datetime.date):
            return int(time.mktime(o.timetuple()) * 1000)
        else:
            return super(DateLocalEpoch, self).default(o)


def date_epoch_json_response(view_func):
    """
    Decorator similar to :func:`.json_response` except it uses
    :class:`.DateLocalEpoch` for JSON encoding, and is less smart
    about debugging.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def wrapper(*args, **kwargs):
        data = view_func(*args, **kwargs)
        if isinstance(data, HttpResponse):
            return data
        response = HttpResponse(json.dumps(data, cls=DateLocalEpoch),
                                content_type='application/json')
        add_never_cache_headers(response)
        return response
    return wrapper


def render_to(template):
    """
    Decorator to simplify a common use of template rendering: Views where the
    template to use is always the same, though there may be several independent
    code paths for determining the data to render with.  The intent is twofold:
    To support the convention that each view function should normally be
    associated with only a single template, and to make it easier for a reader
    to immediately identify which template is associated with the view.  Use::

        @render_to('some_template.html')
        def my_view(request, ...):
           ...

    and return a dictionary from the function, to get the template rendered
    into a HttpResponse with the provided dictionary.  You may "escape" this by
    directly returning a HttpResponse, e.g. in order to respond with a redirect
    or an error message.
    """
    def renderer(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def wrapper(request, *args, **kwargs):
            data = view_func(request, *args, **kwargs)
            if isinstance(data, HttpResponse):
                return data
            return render(request, template, data)
        return wrapper
    return renderer


def json_list_options(request):
    """
    Extracts JSON list options from a request.

    :return: A dictionary with keys ``'search'``, ``'order_by'``,
        ``'offset'``, ``'count'``, ``'direction'`` mapping to the
        corresponding query arguments or their default values.
    """
    return {
        'search': request.GET.get('search', ''),
        'order_by': request.GET.get('order', None),
        'offset': int(request.GET.get('offset', 0)),
        'count': int(request.GET.get('count', 20)),
        'direction': request.GET.get('direction', 'asc'),
    }


# ... perhaps others missing

# Usage example:
# urls.py:
# url('^(?P<pk>\d+)/photo/$',
#     generic.FileView.as_view(model=Car, field='photo')
#     name='cars-photo'),


class FileView(DetailView):
    """
    Generic :class:`.DetailView` serving a file stored on the instane
    whose details are being inspected.

    :cvar model: The model class of which instance is an instance.
    :cvar str field: The name of the field on the instance whose
        details are bing inspected.
    """
    field = None

    def get(self, request, *args, **kwargs):
        """
        :return: The contents of the DB FieldFile specified by
            ``self.field`` as a :class:`~django.http.HttpResponse`.
        """
        self.object = self.get_object()
        fieldfile = getattr(self.object, self.field)
        mimetype, encoding = guess_type(str(fieldfile))
        if not mimetype:
            mimetype = 'application/octet-stream'
        response = HttpResponse(content_type=mimetype)
        fieldfile.open()
        response.write(fieldfile.read())
        fieldfile.close()
        return response


class NoCustomerMixin(object):
    """
    Mixes a ``_customer`` property that is None into a view.
    """
    @cached_property
    def _customer(self):
        return None


class CustomerContextMixin(object):
    """
    Mixes a specialization of
    :meth:`django.views.generic.TemplateView.get_context_data` into a
    view, that makes ``customer`` available in template context.
    """

    def get_context_data(self, **kwargs):
        """
        Makes ``customer`` available in temmplate context.

        Requires ``self._customer`` to be set.  For example via
        :class:`.CustomerInKwargsMixin` or :class:`.NoCustomerMixin`.
        """
        context = super(CustomerContextMixin, self).get_context_data(**kwargs)
        if 'customer' not in context:
            context['customer'] = self._customer
        return context


class CustomerInKwargsMixin(CustomerContextMixin):
    """
    Mixes a ``_customer`` cached property into a view.

    :ivar _customer: A property that extracts a
        :class:`~gridplatform.customers.models.Customer` from the
        ``self.kwargs['customer_id']``.
    """
    @cached_property
    def _customer(self):
        return get_object_or_404(Customer, pk=int(self.kwargs['customer_id']))


class CustomersContextMixin(CustomerContextMixin):
    """
    Bastard mixin that specializes :class:`.CustomerContextMixin`.

    :see: :class:`.CustomerListMixin` if ``self._customer`` should be
        defined by ``self.kwargs['customer_id']``.

    Mixes a `customers` property, and a
    :meth:`django.views.generic.TemplateView.get_context_data`
    specialization into a view.

    :ivar customers: A
        :class:`~gridplatform.customers.models.Customer` list ordered
        by decrypted name.
    """
    @cached_property
    def customers(self):
        with replace_selected_customer(None):
            return list(
                Customer.objects.filter(
                    is_active=True).decrypting_order_by('name_plain', 'id'))

    def get_context_data(self, **kwargs):
        """
        Makes ``self.customers`` available as ``customers`` in template
        context.
        """
        context = {
            'customers': self.customers,
        }
        context.update(kwargs)
        return super(CustomersContextMixin, self).get_context_data(**context)


class CustomerListMixin(CustomersContextMixin):
    """
    A :class:`.CustomerContextMixin` specialization that in addition
    mixes a ``self._customer`` into a view.

    :ivar _customer: :class:`~gridplatform.customers.models.Customer`
        defined from ``self.kwargs['customer_id']`` but avoiding extra
        DB query.  The selected customer must be in
        ``self.customers``.
    """
    @cached_property
    def _customer(self):
        customer_id = int(self.kwargs['customer_id'])
        for customer in self.customers:
            if customer.id == customer_id:
                return customer
        raise Http404


@json_response
@require_POST
def task_status(request):
    """
    View giving JSON response about status of a given task.

    :deprecated: Use :func:`gridplatform.reports.views.status` instead
        as it has better error handling (and has almost the same
        interface, except it also protects against csrf).
    """
    if 'task_id' not in request.POST:
        return HttpResponseBadRequest('task_id not specified')
    task_id = request.POST['task_id']
    async = AsyncResult(task_id)

    if async.status == 'PROGRESS' and isinstance(async.result, dict):
        if 'task_user_id' in async.result:
            if get_user().id != async.result['task_user_id']:
                return HttpResponseForbidden()
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


class StartTaskView(generic_views.FormView):
    """
    Generic view to, when configured with a form class and a Celery
    task, start the Celery task with data from the form.
    """
    task = None
    status_url_name = 'task_status'
    finalize_url_name = None
    http_method_names = ['options', 'post']

    def get_task_kwargs(self, form):
        """
        Must be overwritten by subclass. This methods returns the data
        for the task itself, it must not contain any sensitive data!
        """
        raise NotImplementedError()

    def get_task(self):
        """
        Return the Celery task to run.
        """
        if self.task is None:
            raise ImproperlyConfigured('No task to run.  Provide a task.')
        return self.task

    def get_status_url(self):
        """
        Reverse ``self.status_url_name`` for use in returned
        :class:`JsonResponse` of :meth:`StartTaskview.form_valid`.
        """
        if self.status_url_name is None:
            raise ImproperlyConfigured('Missing status_url_name')
        return urlresolvers.reverse(self.status_url_name)

    def get_finalize_url(self):
        if self.finalize_url_name is None:
            raise ImproperlyConfigured('Missing finalize_url_name')
        return urlresolvers.reverse(self.finalize_url_name)

    def start_task(self, kwargs):
        """
        Start the Celery task.
        """
        task = self.get_task()
        return task.delay(**kwargs)

    def form_valid(self, form):
        """
        Start Celery task with data from form; called when the form is found
        valid.
        """
        kwargs = self.get_task_kwargs(form)
        async = self.start_task(kwargs)
        return JsonResponse({
            'task_id': async.id,
            'status_url': self.get_status_url(),
            'finalize_url': self.get_finalize_url(),
            'status': async.status,
        })

    def form_invalid(self, form):
        """
        Format form errors as JSON error response.
        """
        return JsonResponseBadRequest(form.errors)


class TaskForm(forms.Form):
    """
    Same as :class:`gridplatform.reports.views.TaskForm`.
    """
    task_id = forms.CharField()


class FinalizeTaskView(generic_views.FormView):
    """
    Abstract view for finalizing a Celery task.  Specializations must
    implement :meth:`~.FinalizeTaskView.finalize_task`.
    """
    form_class = TaskForm
    http_method_names = ['options', 'post']

    def finalize_task(self, task_result):
        """
        Abstract method for finalizing task.

        :param task_result: The result returned by the Celery task to
            be finalized.

        :return: Should return some kind of http resonse.
        """
        raise NotImplementedError(self.__class__)

    def form_valid(self, form):
        """
        If task was successful delegate to
        :meth:`~.FinalizeTaskView.finalize_task`.
        """
        task_id = form.cleaned_data['task_id']
        async = AsyncResult(task_id)
        if not async.successful():
            return JsonResponseBadRequest({'task_status': async.status})

        return self.finalize_task(async.result)

    def form_invalid(self, form):
        """
        Format form errors as JSON error response.
        """
        return JsonResponseBadRequest(form.errors)


class HomeViewBase(CustomerListMixin, RedirectView):
    """
    An abstract :class:`.RedirectView` used when a site depends on a
    customer.

    .. method:: get_redirect_with_customer_url()

        Should return a url to redirect to if the customer is allready set

    .. method:: get_choose_customer_url()

        Should return a url to the site specialisation of ChooseCustomerBase
    """
    def get_redirect_url(self, *args, **kwargs):
        """
        Redirects to customer list if no customer has been defined yet.
        If only one customer is defined or a customer is currently
        selected, delegate to
        :meth:`~.HomeViewBase.get_redirect_with_customer_url`.  If
        more than one customer is defined and none are selected
        delegate to :meth:`~.HomeViewBase.get_choose_customer_url`.
        """
        if len(self.customers) == 0:
            return reverse('provider_site:customer-list')
        elif len(self.customers) == 1:
            return self.get_redirect_with_customer_url(self.customers[0].id)
        else:
            customer_id = self.request.session.get('chosen_customer_id', None)
            if customer_id and Customer.objects.filter(
                    is_active=True, pk=customer_id).exists():
                return self.get_redirect_with_customer_url(customer_id)
            else:
                return self.get_choose_customer_url()

    def get_redirect_with_customer_url(self, customer_id):
        raise NotImplementedError()

    def get_choose_customer_url(self):
        raise NotImplementedError()


class ChooseCustomerBase(generic_views.TemplateView):
    """
    Used when site depends on a customer

    The specialisation needs to define a template_name
    The template should be a blank page that contains
    javascript to open the customer select modal on load
    """
    @property
    def _customer(self):
        return None

    def get_context_data(self, **kwargs):
        context = {
            'customers': list(
                Customer.objects.filter(
                    is_active=True).decrypting_order_by('name_plain', 'id')),
        }
        context.update(kwargs)
        return super(ChooseCustomerBase, self).get_context_data(**context)


class CustomerViewBase(CustomerListMixin, RedirectView):
    """
    Used when site depends on a customer

    .. method:: get_redirect_with_customer_url()

        Should return a url to redirect to
    """
    def get_redirect_url(self, *args, **kwargs):
        self.request.session['chosen_customer_id'] = self._customer.id
        return self.get_redirect_with_customer_url(self._customer.id)

    def get_redirect_with_customer_url(self, customer_id):
            raise NotImplementedError()
