# -*- coding: utf-8 -*-
"""
Django generic views and extra_views generic views wrapped with access control
and localized form fields by default.

Checks for logged in for read-only views; checks for add, change and delete
permissions for the models involved as appropriate otherwise.  (Access control
is implemented using mixin classes from braces.)

This is intended to be imported as ``from gridplatform.utils import
generic_views`` --- i.e. so that the generic views are referred to with the
module as prefix on use, to make it explicit whether we use these or the base
Django generic views.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import operator
from django.db.models import Q
import django.views.generic

import extra_views
import extra_views.formsets
import extra_views.advanced

from .access_control import CustomerBoundMixin
from .access_control import LoginRequiredMixin
from .access_control import ModelPermissionRequiredMixin
from .access_control import MultipleModelPermissionsRequiredMixin
from .localized import LocalizedModelFormMixin
from .localized import LocalizedModelFormSetMixin
from .localized import LocalizedInlineFormSetMixin


__all__ = [
    # read only; no explicit permission checks
    'ListView',
    'DetailView',
    # normal generic views with permission checks added
    'CreateView',
    'DeleteView',
    'UpdateView',
    # extra_views
    'InlineFormSet',
    'ModelFormSetView',
    'InlineFormSetView',
    'CreateWithInlinesView',
    'UpdateWithInlinesView',
]


class InlineFormSet(
        LocalizedInlineFormSetMixin,
        CustomerBoundMixin,
        extra_views.InlineFormSet):
    """
    Specialisation of :class:`extra_views.InlineFormSet` which adds
    ``localized_fields`` to parameters to ``modelformset_factory()``.
    """
    pass


class View(
        LoginRequiredMixin,
        CustomerBoundMixin,
        django.views.generic.View):
    """
    :class:`django.views.generic.View` specialization that requires
    login and is bound to the customer in context.
    """
    pass


class TemplateView(
        LoginRequiredMixin,
        CustomerBoundMixin,
        django.views.generic.TemplateView):
    """
    :class:`django.views.generic.TemplateView` specialization that
    requires login and is bound to the customer in context.
    """
    pass


class SearchableListMixin(extra_views.SearchableListMixin):
    """
    Mix :meth:`~.SearchableListMixin.get_queryset` into a view to
    allow for querying encrypted fields as well.

    :class:`extra_views.SearchableListMixin` specialization that
    replaces :meth:`~.SearchableListMixin.get_queryset` with a version
    that delegates search to
    ``self.model.objects.decrypting_search()`` if possible.
    """
    def get_queryset(self):
        # Note that the super call skips a level. This is our replacement for
        # extra_views.SearchableListMixin.get_queryset.
        qs = super(extra_views.SearchableListMixin, self).get_queryset()
        query = self.get_search_query()
        if query and not hasattr(self.model.objects, 'decrypting_search'):
            w_qs = []
            search_pairs = self.get_search_fields_with_filters()
            for word in self.get_words(query):
                filters = [
                    Q(**{'%s__%s' % (pair[0], pair[1]): word})
                    for pair in search_pairs
                ]
                if self.search_date_fields:
                    dt = self.try_convert_to_date(word)
                    if dt:
                        filters.extend([
                            Q(**{field_name: dt})
                            for field_name in self.search_date_fields
                        ])
                w_qs.append(reduce(operator.or_, filters))
            qs = qs.filter(reduce(operator.and_, w_qs)).distinct()
        elif query:
            for word in self.get_words(query):
                qs = qs.decrypting_search(word, self.search_fields)
        return qs


class ListView(
        LoginRequiredMixin,
        CustomerBoundMixin,
        extra_views.SortableListMixin,
        SearchableListMixin,
        django.views.generic.ListView):
    """
    Render list of objects from specified model.

    Set attribute ``model`` or override
    :meth:`~.ListView.get_queryset` to specify objects.

    By default, this will be rendered to template
    ``{app_label}/{model_name}_list.html`` -- to override, specify
    ``template_name`` attribute.

    The template will have access to the object list in variables
    ``object_list`` and ``{model_name}_list``, and to the generic view
    object in variable ``view``.

    If more data should be provided to template, override
    :meth:`~.ListView.get_context_data`.  The conventional pattern
    for such extension is::

        def get_context_data(self, **kwargs):
            context = {
                ...
            }
            context.update(kwargs)
            return super(..., self).get_context_data(**context)

    There are numerous other hooks/extension points, though those should not
    normally be needed.

    This view supports is sortable on encrypted and non-encrypted fields.

    You can provide either sort_fields as a plain list like
    ['id', 'some', 'foo__bar', ...] or, if you want to hide original field
    names you can provide list of tuples with aliases that will be used by
    setting sort_field_aliases, e.g.:
    [('id', 'by_id'), ('some', 'show_this'), ('foo__bar', 'bar')]

    Supports GET parameters:
        'o': For field to sort by
        'ot': For sorting type: 'asc' or 'desc', default is 'asc'
    """

    def _sort_queryset(self, queryset):
        self.sort_helper = self.get_sort_helper()
        sort = self.sort_helper.get_sort()
        if sort:
            if hasattr(queryset, 'decrypting_order_by'):
                queryset = queryset.decrypting_order_by(sort)
            else:
                queryset = queryset.order_by(sort)
        return queryset


class DetailView(
        LoginRequiredMixin,
        CustomerBoundMixin,
        django.views.generic.DetailView):
    """
    Render single object of specified model.

    Should be exposed in an URL with a ``pk`` keyword argument; this
    will specify the primary key/ID of the object to render.

    Set attribute ``model`` to specify model class.

    By default, this will be rendered to template
    ``{app_label}/{model_name}_detail.html`` -- to override, specify
    ``template_name`` attribute.

    The template will have access to the object in variables ``object`` and
    ``{model_name}``, and to the generic view object in variable ``view``.

    If more data should be provided to template, override
    :meth:`~.DetailView.get_context_data` -- the conventional
    pattern for such extension is::

        def get_context_data(self, **kwargs):
            context = {
                ...
            }
            context.update(kwargs)
            return super(..., self).get_context_data(context)

    There are numerous other hooks/extension points, though those should not
    normally be needed...
    """
    pass


class CreateView(
        ModelPermissionRequiredMixin,
        LocalizedModelFormMixin,
        CustomerBoundMixin,
        django.views.generic.CreateView):
    """
    Render model form for specified model on GET; saves and redirects if model
    validates on POST, otherwise renders model form with the errors.

    If the model specifies a :meth:`~.CreateView.get_absolute_url`,
    then the default URL to redirect to will be the result of calling
    :meth:`~django.db.models.Model.get_absolute_url` on the saved
    object.  Override :meth:`~.CreateView.get_success_url` to
    specify a different URL --- note that, at that point, the saved
    object will be available in ``self.object``.

    Set attribute ``model`` to specify model class.

    By default, a modelform for the model class is constructed, with its
    ``fields`` specification taken from the ``fields`` attribute on the view.
    An alternative modelform may be specified by setting ``form_class``.

    By default, this will be rendered to template
    ``{app_label}/{model_name}_form.html`` --- to override, specify
    ``template_name`` attribute.

    The template will have access to the modelform in variable ``form``, and to
    the generic view object in variable ``view``.

    If more data should be provided to template, override
    :meth:`~.CreateView.get_context_data` --- the conventional pattern
    for such extension is::

        def get_context_data(self, **kwargs):
            context = {
                ...
            }
            context.update(kwargs)
            return super(..., self).get_context_data(context)

    There are numerous other hooks/extension points, though those should not
    normally be needed...
    """
    model_permission = 'add'


class DeleteView(
        ModelPermissionRequiredMixin,
        CustomerBoundMixin,
        django.views.generic.DeleteView):
    """
    Delete a model object, then redirect.

    Should be exposed in an URL with a ``pk`` keyword argument; this
    will specify the primary key/ID of the object to delete.

    Set attribute ``model`` to specify model class.

    Override :meth:`~.DeleteView.get_success_url` to specify the URL
    to redirect to --- note that this is called *before* the object is
    deleted, with the object available in ``self.object``.
    """
    model_permission = 'delete'


class UpdateView(
        ModelPermissionRequiredMixin,
        LocalizedModelFormMixin,
        CustomerBoundMixin,
        django.views.generic.UpdateView):
    """
    Render model form for specified object on GET; saves and redirects if model
    validates on POST, otherwise renders model form with the errors.

    Should be exposed in an URL with a ``pk`` keyword argument; this
    will specify the primary key/ID of the object to update.

    If the model specifies a
    :meth:`~django.db.models.Model.get_absolute_url`, then the
    default URL to redirect to will be the result of calling
    :meth:`~django.db.models.Model.get_absolute_url` on the saved
    object.  Override :meth:`~.UpdateView.get_success_url` to
    specify a different URL --- note that, at that point, the saved
    object will be available in ``self.object``.

    Set attribute ``model`` to specify model class.

    By default, a modelform for the model class is constructed, with its
    ``fields`` specification taken from the ``fields`` attribute on the view.
    An alternative modelform may be specified by setting ``form_class``.

    By default, this will be rendered to template
    ``{app_label}/{model_name}_form.html`` --- to override, specify
    ``template_name`` attribute.

    The template will have access to the object in variables ``object`` and
    ``{model_name}``, to the modelform in variable ``form``, and to the generic
    view object in variable ``view``.

    If more data should be provided to template, override
    :meth:`~.UpdateView.get_context_data` --- the conventional pattern
    for such extension is::

        def get_context_data(self, **kwargs):
            context = {
                ...
            }
            context.update(kwargs)
            return super(..., self).get_context_data(context)

    There are numerous other hooks/extension points, though those should not
    normally be needed...
    """
    model_permission = 'change'


class ModelFormSetView(
        MultipleModelPermissionsRequiredMixin,
        LocalizedModelFormSetMixin,
        CustomerBoundMixin,
        extra_views.ModelFormSetView):
    """
    :class:`extra_views.ModelFormSetView` specialization that require
    permissions, localizes model formset and binds to a customer.
    """
    model_permissions = ('add', 'delete', 'change')

    def get_permissions_models(self):
        """
        :return: The models for which to check permissions.
        """
        model = self.model or self.get_queryset().model
        return [model]


class InlineFormSetView(
        MultipleModelPermissionsRequiredMixin,
        LocalizedModelFormSetMixin,
        CustomerBoundMixin,
        extra_views.InlineFormSetView):
    """
    :class:`extra_views.InlineFormSetView` specialization that require
    permissions, localizes model formset and binds to a customer.
    """
    model_permissions = ('add', 'delete', 'change')

    def get_permissions_models(self):
        """
        :return: The models for which to check permissions.
        """
        model = self.get_inline_model()
        return [model]


class CreateWithInlinesView(
        MultipleModelPermissionsRequiredMixin,
        LocalizedModelFormMixin,
        CustomerBoundMixin,
        extra_views.CreateWithInlinesView):
    """
    :class:`extra_views.CreateWithInlinesView` specialization that
    require permissions, localizes model formset and binds to a
    customer.
    """
    model_permissions = ('add',)
    # NOTE: Localized by using our specialisation of InlineFormSet;
    # not by mixin...

    def get_permissions_models(self):
        """
        :return: The models for which to check permissions.
        """
        base_model = self.model or self.get_queryset().model
        inline_models = [
            inline.model
            for inline in self.get_inlines()
        ]
        return [base_model] + inline_models


class UpdateWithInlinesView(
        MultipleModelPermissionsRequiredMixin,
        LocalizedModelFormMixin,
        CustomerBoundMixin,
        extra_views.UpdateWithInlinesView):
    """
    :class:`extra_views.UpdateWithInlinesView` specialization that
    require permissions, localizes model formset and binds to a
    customer.
    """
    model_permissions = ('add', 'delete', 'change')
    # NOTE: Localized by using our specialisation of InlineFormSet;
    # not by mixin...

    def get_permissions_models(self):
        """
        :return: The models for which to check permissions.
        """
        base_model = self.model or self.get_queryset().model
        inline_models = [
            inline.model
            for inline in self.get_inlines()
        ]
        return [base_model] + inline_models


class FormView(
        LoginRequiredMixin,
        CustomerBoundMixin,
        django.views.generic.FormView):
    """
    :class:`django.views.generic.FormView` specialization that require
    login and binds to a customer.
    """
    pass
