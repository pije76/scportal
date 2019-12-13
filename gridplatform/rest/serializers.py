# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals


from collections import OrderedDict

import urlparse
import functools

from django.core import urlresolvers
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.utils import six
from rest_framework import serializers
from rest_framework import pagination
import rest_framework.reverse

from .conf import settings


Field = serializers.Field
CharField = serializers.CharField
ChoiceField = serializers.ChoiceField
DateTimeField = serializers.DateTimeField
SerializerMethodField = serializers.SerializerMethodField
Serializer = serializers.Serializer
ModelSerializer = serializers.ModelSerializer


class HyperlinkedAutoResolveMixin(object):
    """
    Mixin for :class:`.HyperlinkedRelatedField` and
    :class:`.HyperlinkedIdentityField` to allow them to generate correct
    relation URLs in the case of nested routing.
    """
    @property
    def is_identity_field(self):
        return isinstance(self, serializers.HyperlinkedIdentityField)

    def build_kwargs(self, possibility, obj, parent_kwargs):
        for result, params in possibility:
            if params and 'format' not in params:
                # We found a usable match
                kwargs = {}
                for param in params:
                    if param in parent_kwargs:
                        # We only have request_kwargs in the case of
                        # HyperlinkedIdentityFields, in which case we trust
                        # parent_kwargs.
                        kwargs[param] = parent_kwargs[param]
                    elif self.is_identity_field and param != 'pk':
                        # In the case of HyperlinkedIndentityFields and top
                        # level list views.
                        kwargs[param] = obj.id
                    else:
                        # As a last try we see if the model has a field with
                        # same name as param. This is often the case for
                        # HyperlinkedRelatedFields.
                        kwargs[param] = getattr(obj, param)
                return kwargs
        raise AttributeError

    def get_url(self, obj, namespace_view_name, request, format):
        if self.is_identity_field:
            kwargs = request.parser_context['kwargs']
        else:
            kwargs = {}
        urlconf = urlresolvers.get_urlconf()
        resolver = urlresolvers.get_resolver(urlconf)
        parts = namespace_view_name.split(':')
        parts.reverse()
        view_name = parts[0]
        namespace_path = parts[1:]
        resolved_path = []
        ns_pattern = ''
        while namespace_path:
            namespace = namespace_path.pop()
            resolved_path.append(namespace)
            if namespace in resolver.app_dict and \
                    namespace not in resolver.app_dict[namespace]:
                # default instance namespace
                namespace = resolver.app_dict[namespace][0]
            try:
                pattern, resolver = resolver.namespace_dict[namespace]
            except KeyError:
                raise urlresolvers.NoReverseMatch(
                    "%s is not a registered namespace inside '%s'" %
                    (namespace, ':'.join(resolved_path)))
            ns_pattern += pattern
        if ns_pattern:
            resolver = urlresolvers.get_ns_resolver(
                ns_pattern, resolver)
        possibilities = resolver.reverse_dict.getlist(view_name)
        for possibility, pattern, defaults in possibilities:
            try:
                kwargs = self.build_kwargs(possibility, obj, kwargs)
                return rest_framework.reverse.reverse(
                    namespace_view_name, kwargs=kwargs, request=request,
                    format=format)
            except AttributeError:
                continue
        return super(HyperlinkedAutoResolveMixin, self).get_url(
            obj, namespace_view_name, request=request, format=format)


class HyperlinkedLookupMixin(object):
    """
    Mixin for :class:`.HyperlinkedRelatedField` and
    :class:`.HyperlinkedIdentityField` to make easy to specify a
    :attr:`lookup_map` used for nesting routing.
    """
    def __init__(self, *args, **kwargs):
        self.lookup_map = kwargs.pop('lookup_map', None)
        super(HyperlinkedLookupMixin, self).__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        if self.lookup_map:
            kwargs = {
                key: functools.reduce(getattr, value.split('.'), obj)
                for key, value in self.lookup_map.items()
            }
            return rest_framework.reverse.reverse(
                view_name, kwargs=kwargs, request=request, format=format)
        return super(HyperlinkedLookupMixin, self).get_url(
            obj, view_name, request=request, format=format)


class HyperlinkedSubclassRelatedMixin(object):
    """
    Mixin for :class:`.HyperlinkedRelatedField` to add support for models that
    have polymorphic behaviour.
    """

    def __init__(self, *args, **kwargs):
        # view_name isn't required for subclass related models
        kwargs['view_name'] = kwargs.get('view_name', '')
        super(HyperlinkedSubclassRelatedMixin, self).__init__(*args, **kwargs)

    def initialize(self, parent, field_name):
        super(HyperlinkedSubclassRelatedMixin, self).initialize(
            parent, field_name)
        if getattr(self, 'queryset', None) is None:
            manager = getattr(
                self.parent.opts.model, self.source or field_name)
            if hasattr(manager, 'related'):  # Forward
                self.queryset = manager.related.model._default_manager.all()
            else:  # Reverse
                self.queryset = manager.field.rel.to._default_manager.all()
        model = self.queryset.model
        self._subclass_related = hasattr(model, 'subclass')

    def _subclass_related_view_name(self, obj):
        subclass_instance = obj.subclass_instance
        format_kwargs = {
            'app_label': subclass_instance._meta.app_label,
            'model_name': subclass_instance._meta.object_name.lower()
        }
        return ':'.join([
            settings.REST_API_NAMESPACE,
            '{}-detail'.format(settings.REST_SERIALIZER_VIEW_NAME_BASE) %
            format_kwargs
        ])

    def get_url(self, obj, view_name, request, format):
        if self._subclass_related:
            try:
                return super(HyperlinkedSubclassRelatedMixin, self).get_url(
                    obj,
                    view_name=self._subclass_related_view_name(obj),
                    request=request, format=format)
            except urlresolvers.NoReverseMatch:
                pass
        return super(HyperlinkedSubclassRelatedMixin, self).get_url(
            obj, view_name=view_name, request=request, format=format)

    def from_native(self, value):
        if self._subclass_related:
            try:
                http_prefix = value.startswith(('http:', 'https:'))
            except AttributeError:
                msg = self.error_messages['incorrect_type']
                raise ValidationError(msg % type(value).__name__)
            if http_prefix:
                value = urlparse.urlparse(value).path
                prefix = urlresolvers.get_script_prefix()
                if value.startswith(prefix):
                    value = '/' + value[len(prefix):]
            try:
                match = urlresolvers.resolve(value)
            except Exception:
                raise ValidationError(self.error_messages['no_match'])
            try:
                obj = self.get_object(
                    self.queryset, match.view_name, match.args, match.kwargs)
            except (ObjectDoesNotExist, TypeError, ValueError):
                # NOTE: This error might actually have been an
                # "incorrect_match".
                raise ValidationError(self.error_messages['does_not_exist'])
            if match.view_name != self._subclass_related_view_name(obj):
                raise ValidationError(self.error_messages['incorrect_match'])
            return obj
        else:
            return super(
                HyperlinkedSubclassRelatedMixin, self).from_native(value)


class HyperlinkedRelatedField(
        HyperlinkedSubclassRelatedMixin,
        HyperlinkedLookupMixin,
        HyperlinkedAutoResolveMixin,
        serializers.HyperlinkedRelatedField):
    """
    The GridPlatform default HyperlinkedRelatedField.
    """
    pass


class HyperlinkedIdentityField(
        HyperlinkedLookupMixin,
        HyperlinkedAutoResolveMixin,
        serializers.HyperlinkedIdentityField):
    """
    The GridPlatform default HyperlinkedIdentityField.
    """
    pass


class DefaultSerializerOptions(serializers.HyperlinkedModelSerializerOptions):
    """
    Options class for the :class:`.DefaultSerializer`
    """
    def __init__(self, meta):
        super(DefaultSerializerOptions, self).__init__(meta)
        if meta.model and \
                getattr(meta.model, 'subclass', None) and \
                'subclass' not in self.exclude:
            # Don't try to generate hyperlink to ContentType
            self.exclude += ('subclass',)


class DefaultSerializer(serializers.HyperlinkedModelSerializer):
    """
    The GridPlatform default serializer.
    """
    _options_class = DefaultSerializerOptions
    _hyperlink_field_class = HyperlinkedRelatedField
    _hyperlink_identify_field_class = HyperlinkedIdentityField
    _default_view_name = ':'.join([
        settings.REST_API_NAMESPACE,
        '{}-detail'.format(settings.REST_SERIALIZER_VIEW_NAME_BASE)
    ])

    def get_pk_field(self, model_field):
        # Always include pk field
        return self.get_field(model_field)

    def reverse(self, viewname, *args, **kwargs):
        request = kwargs.pop('request', None) or self.context.get('request')
        url = urlresolvers.reverse(viewname, *args, **kwargs)
        if request:
            return request.build_absolute_uri(url)
        return url

    @property
    def filter_fields(self):
        return getattr(self.context['view'], 'filter_fields', [])

    def metadata(self):
        def metadata_with_filter_fields(field_name, field):
            metadata = field.metadata()
            if field_name in self.filter_fields:
                metadata['filter_field'] = field_name
            else:
                metadata['filter_field'] = None
            return field_name, metadata

        return OrderedDict([
            metadata_with_filter_fields(field_name, field)
            for field_name, field in six.iteritems(self.fields)
        ])


class DefaultPaginationSerializer(pagination.PaginationSerializer):
    """
    The GridPlatform default serializer when pagination is needed
    """
    filter_fields = SerializerMethodField('get_filter_fields')

    def get_filter_fields(self, obj):
        return getattr(self.context['view'], 'filter_fields', [])
