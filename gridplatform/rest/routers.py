# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import collections
from collections import OrderedDict

import django.conf.urls
import rest_framework.response
import rest_framework.reverse
import rest_framework.routers
import rest_framework.views

from .conf import settings


class NestingMixin(object):
    """
    Mixes :meth:`.NestingMixin.register` into a
    :class:`rest_framework.routers.BaseRouter` specialization.

    The signature of :meth:`rest_framework.routers.BaseRouter.register` is
    changed to return a :class:`.NestingMixin.Nested` instance rather than not
    having a return value at all.
    """
    class Nested(object):
        """
        Allows nesting of registered viewsets.

        :ivar root: The root :class:`rest_framework.routers.BaseRouter`
            specialization to register nested viewsets on.
        :ivar prefix:  The prefix used to register parent viewsets.
        """
        def __init__(self, root, prefix):
            self.root = root
            self.prefix = prefix

        def register(self, prefix, viewset, base_name=None, **kwargs):
            """
            Delegates to :meth:`.NestingMixin.register` but with prefix rewritten to
            simulate nesting under parent viewset.
            """
            filter_by = kwargs.pop('filter_by', ())
            if not isinstance(filter_by, (tuple, list)):
                filter_by = (filter_by,)
            parent_prefix = self.prefix
            filter_args = '/'.join(
                '(?P<{}>[^/.]+)'.format(field)
                for field in filter_by
            )
            if filter_args:
                nested_prefix = \
                    '{parent_prefix}/{filter_args}/{prefix}'.format(
                        parent_prefix=parent_prefix, filter_args=filter_args,
                        prefix=prefix)
            else:
                nested_prefix = '{parent_prefix}/{prefix}'.format(
                    parent_prefix=parent_prefix, prefix=prefix)
            return self.root.register(
                prefix=nested_prefix, viewset=viewset, base_name=base_name,
                filter_by=filter_by, **kwargs)

    def register(self, prefix, viewset, base_name=None, **kwargs):
        """
        Specialization of :meth:`rest_framework.routers.BaseRouter.register`
        changed to return a :class:`.NestingMixin.Nested` that may be used to
        further register more viewsets under the URLs given viewset argument.
        """
        filter_by = kwargs.pop('filter_by', ())
        viewset.filter_by = filter_by
        super(NestingMixin, self).register(
            prefix=prefix, viewset=viewset, base_name=base_name, **kwargs)
        return self.Nested(root=self, prefix=prefix)


class AppNamespaceMixin(object):
    """
    Mixes :attr:`.AppNamespaceMixin.urls` into a
    :class:`rest_framework.routers.BaseRouter` specialization, so that
    registered viewsets have their urls defined according to the scheme defined
    by :data:`settings.REST_API_NAMESPACE` and
    :data:`settings.REST_SERIALIZER_VIEW_NAME_BASE`.
    """
    def get_default_base_name(self, viewset):
        model_cls = getattr(viewset, 'model', None)
        queryset = getattr(viewset, 'queryset', None)
        if model_cls is None and queryset is not None:
            model_cls = queryset.model
        model_meta = model_cls._meta
        format_kwargs = {
            'app_label': model_meta.app_label,
            'model_name': model_meta.object_name.lower()
        }
        return settings.REST_SERIALIZER_VIEW_NAME_BASE % format_kwargs

    @property
    def urls(self):
        bad_urls = super(AppNamespaceMixin, self).get_urls()
        global_namespace_urls = []
        namespaces = collections.defaultdict(list)
        for urlpattern in bad_urls:
            regex = urlpattern.regex
            parts = urlpattern.name.rpartition(':')
            name = parts[2]
            namespace_path = parts[0] or None
            view = urlpattern.callback
            url = django.conf.urls.url(regex.pattern, view, name=name)
            if namespace_path:
                namespaces[namespace_path].append(url)
            else:
                global_namespace_urls.append(url)
        namespace_urls = []
        for namespace_path, urls in namespaces.items():
            namespace_list = namespace_path.split(':')
            nested = urls
            while namespace_list:
                namespace = namespace_list.pop()
                nested = [django.conf.urls.url(
                    r'',
                    django.conf.urls.include((nested, namespace, namespace)))]
            namespace_urls.append(nested.pop())
        return django.conf.urls.patterns(
            r'', *(global_namespace_urls + namespace_urls))


class ExtendedRouterMixin(AppNamespaceMixin, NestingMixin):
    """
    Mixed both :class:`.AppNamespaceMixin` and :class:`.NestingMixin` into a
    :class:`rest_framework.routers.BaseRouter` specialization.
    """
    pass


class DefaultRouter(ExtendedRouterMixin, rest_framework.routers.DefaultRouter):
    """
    :class:`rest_framework.routers.DefaultRouter` specialization mixed with
    :class:`.ExtendedRouterMixin`.
    """
    description = ''

    def __init__(self, *args, **kwargs):
        super(DefaultRouter, self).__init__(*args, **kwargs)
        self._api_root = {}

    def register(self, prefix, viewset, base_name=None, **kwargs):
        if not kwargs:
            if base_name is None:
                base_name = self.get_default_base_name(viewset)
            self._api_root[prefix] = base_name

        return super(DefaultRouter, self).register(
            prefix=prefix, viewset=viewset, base_name=base_name, **kwargs)

    def get_api_root_view(self):
        api_root = self._api_root

        class ApiRootView(rest_framework.views.APIView):
            __doc__ = self.description
            _ignore_model_permissions = True

            def get_view_name(view_cls, suffix=None):
                if self.__doc__ != '':
                    return ''
                else:
                    return super(DefaultRouter, self).get_view_name(
                        view_cls, suffix)

            def get(self, request, format=None):
                return rest_framework.response.Response(OrderedDict(sorted([
                    (url,
                     rest_framework.reverse.reverse(
                         ':'.join([
                             settings.REST_API_NAMESPACE,
                             '{}-list'.format(base_name),
                         ]),
                         request=request,
                         format=format))
                    for url, base_name in api_root.items()
                ])))

        return ApiRootView.as_view()


class SimpleRouter(ExtendedRouterMixin, rest_framework.routers.SimpleRouter):
    """
    :class:`rest_framework.routers.SimpleRouter` specialization mixed with
    :class:`.ExtendedRouterMixin`.
    """
    pass
