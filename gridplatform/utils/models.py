# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from collections import namedtuple

import pytz
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.core.exceptions import ValidationError
from django.template.defaultfilters import date as date_format
from history.models import HistoricalRecords as ProDjangoHistoricalRecords

from gridplatform.trackuser import get_current_date

from .decorators import virtual


def raise_if_none(subject, exception):
    """
    Raise C{exception} if C{subject is None}.
    """
    if subject is None:
        raise exception


# TODO: Delete.  This is not used anywhere.
class HistoricalRecords(ProDjangoHistoricalRecords):
    """
    Specialization of C{ProDjangoHistoricalRecords} that avoids naive
    timestamp warnings.
    """

    def __init__(self, *args, **kwargs):
        """
        @keyword app_label: Optional argument for setting Meta.app_label on the
        generated historical records model.  This is necessary to support
        historical records for Models defined outside models.py.
        """
        self.app_label = kwargs.pop('app_label', None)
        super(HistoricalRecords, self).__init__(*args, **kwargs)

    def get_meta_options(self, model):
        """
        L{LogicalInput} specialization of
        L{HistoricalRecords.get_meta_options()}.  Controls meta options for
        generated historical record model.
        """
        result = super(HistoricalRecords, self).get_meta_options(model)
        if self.app_label is not None:
            result['app_label'] = self.app_label
        return result

    def get_extra_fields(self, model):
        """
        Overload of C{ProDjangoHistoricalRecords.get_extra_fields()},
        to avoid naive timestamps.
        """
        res = super(HistoricalRecords, self).get_extra_fields(model)
        res["history_date"].default = lambda: datetime.datetime.now(pytz.utc)
        return res

    def copy_fields(self, model):
        """
        Overload of C{ProDjangoHistoricalRecords.copy_fields()},
        to avoid specific errors wrt. unique foreign keys:
        C{OneToOneField} is implicitly unique, and clearing the "unique"
        attribute (as the inherited C{copy_fields()} does) has no effect.

        For now, we support use of C{OneToOneField} only as used for
        multi-table inheritance in Django --- the historical model includes all
        fields from the parent models in its single table, and the relation to
        a "parent" instance may thus be removed without loss of information.

        On other uses of C{OneToOneField}, we report error.
        """
        base_fields = super(HistoricalRecords, self).copy_fields(model)
        fields = {}
        for (name, field) in base_fields.iteritems():
            if isinstance(field, models.OneToOneField):
                assert field.rel.parent_link
                fields[name] = models.IntegerField(null=True)
            if isinstance(field, models.ForeignKey):
                fields["%s_id" % name] = models.IntegerField(null=True)
            else:
                fields[name] = field

        return fields


class StoredSubclassManager(models.Manager):
    """
    Manager which injects the appropriate ``prefetch_related()`` call
    for :class:`.StoreSubclass` instances.  This manager also provides
    the :meth:`.subclass_only` method.
    """
    use_for_related_fields = False

    def get_query_set(self):
        qs = super(StoredSubclassManager, self).get_query_set()
        return qs.prefetch_related('subclass_instance')

    def subclass_only(self):
        """
        Returns a queryset that will only contain objects whose subclass field
        indicate that they are subclasses of the model on which the query is
        performed.

        The objects yielded by the resulting query will still be
        instanses of the model on which the query is performed, so you
        still need to follow the ``subclass_instance``
        :class:`~django.contrib.contenttypes.generic.GenericForeignKey`
        on each object in the result, if you need the concrete
        subclass instance.

        :note: Only useful for proxy models --- queries on concrete
            models are already limited to those objects that are
            present in the relevant table, i.e. instances of the model
            we run the query on (possibly through subclasses).

        :deprecated: This is only useful as a workaround for the mess
            we've made with proxy models to save a few db tables (the
            :class:`legacy.measurementpoints.proxies.MeasurementPoint`
            class hierachy in particular).  We strongly recommend
            normal subclassing, also when there are no new fields, but
            in particular when there are new fields, as is the case
            with
            :class:`legacy.measurementpoints.proxies.MeasurementPoint`
            and its subclasses.
        """
        # The for_concrete_models=False ensures that proxy models are included
        # in the result.
        content_types_dict = ContentType.objects.get_for_models(
            *self._model_subclasses(), for_concrete_models=False)
        return self.get_query_set().filter(
            subclass__in=content_types_dict.values())

    def _model_subclasses(self, model=None):
        """
        List of all ``model`` subclasses.
        """
        if model is None:
            model = self.model
            result = [model]
        else:
            result = []

        for subclass in model.__subclasses__():
            result.append(subclass)
            result.extend(self._model_subclasses(subclass))

        return result


class StoreSubclass(models.Model):
    """
    Model mixin class intended to simplify work with multi-table inheritance
    trees. Saves concrete class via the Django contenttypes framework, and
    injects a ``prefetch_related()`` for this on later model access.

    Accessing the concrete subclass instance from a base class instance must
    still be done explicitly by accessing ``self.subclass_instance``.

    :ivar subclass: A foreign key to the
        :class:`django.contrib.contenttypes.models.ContentType` that
        hold the class information of this instance.
    :ivar subclass_instance: A
        :class:`django.contrib.contenttypes.generic.GenericForeignKey`
        to ``self`` as an instance of ``self.subclass``.
    """
    subclass = models.ForeignKey(
        ContentType, on_delete=models.PROTECT,
        editable=False, related_name='+')
    subclass_instance = generic.GenericForeignKey('subclass', 'id')

    objects = StoredSubclassManager()

    class Meta:
        abstract = True

    @virtual
    def __unicode__(self):
        return unicode(super(StoreSubclass, self))

    def __repr__(self):
        return '<%s(id=%s)>' % (self.__class__.__name__, self.id)

    def __init__(self, *args, **kwargs):
        super(StoreSubclass, self).__init__(*args, **kwargs)
        if not self.subclass_id:
            # NOTE: For_concrete_model=False uses proxy class when applicable,
            # rather than the "default" behaviour of taking first concrete
            # parent.
            self.subclass = ContentType.objects.get_for_model(
                self, for_concrete_model=False)

            self._allow_subclass_change = True
        else:
            self._allow_subclass_change = False
        self._initial_subclass = self.subclass

        if not hasattr(self, '_subclass_cache'):
            # Explicitly use ContentType manager --- the lookups will be cached
            # in the manager; normal access to foreign key does not do that.
            self._subclass_cache = ContentType.objects.get_for_id(
                self.subclass_id)
        # Initialise "cache" for subclass_instance if the current object is
        # already of the appropriate class, to avoid implicitly reloading it on
        # accessing the subclass_instance property.
        if not hasattr(self, '_subclass_instance_cache'):
            if self.__class__ == self.subclass.model_class():
                self._subclass_instance_cache = self

    def clean(self):
        """
        :raise ValidationError: If ``self.subclass`` is changed.
        """
        super(StoreSubclass, self).clean()
        if not self._allow_subclass_change:
            if self._initial_subclass != self.subclass:
                raise ValidationError(
                    ugettext('Changing class is not allowed.'))


TimestampRange = namedtuple(
    'TimestampRange', ['from_timestamp', 'to_timestamp'])


class DateRangeModelMixin(models.Model):
    """
    Adds fields defining a date range to the model this mixin is mixed
    into.

    :ivar from_date:  The first date in the date range.
    :ivar to_date:  The final date in the date range.  This may be ``None``.

    :see: :class:`gridplatform.utils.managers.DateRangeManagerMixin`
    """
    from_date = models.DateField(_('from date'), default=get_current_date)
    to_date = models.DateField(_('to date'), null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        """
        :raise ValidationError: If date range is empty.
        """
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValidationError(_('Period of existense must be non-empty.'))

    def timestamp_range_intersection(
            self, from_timestamp, to_timestamp, timezone):
        """
        :return: The timestamp range intersection between a given
            timestamp range and this date range.  If the result is empty
            ``None`` is returned.

        :param from_timestamp: The start of the given timestamp range.
        :param to_timestamp: The end of the given timestamp range.
        :param timezone: The timestamp range that corresponds to this
            date range is only well-defined given a timezone.
        """
        range_from_timestamp = timezone.localize(
            datetime.datetime.combine(self.from_date, datetime.time()))
        result_from_timestamp = max([from_timestamp, range_from_timestamp])

        if self.to_date is not None:
            range_to_timestamp = timezone.localize(
                datetime.datetime.combine(
                    self.to_date + datetime.timedelta(days=1),
                    datetime.time()))
            result_to_timestamp = min([to_timestamp, range_to_timestamp])
        else:
            result_to_timestamp = to_timestamp

        if result_from_timestamp <= result_to_timestamp:
            return TimestampRange(result_from_timestamp, result_to_timestamp)
        else:
            return None


class TimestampRangeModelMixin(models.Model):
    """
    Adds fields defining a timestamp range to the model this mixin is
    mixed into.

    :ivar from_timestamp:  The first timestamp in the timestamp range.
    :ivar to_timestamp: The final timestamp in the timestamp range.
        This may be ``None``.

    :see: :class:`gridplatform.utils.managers.TimestampRangeManagerMixin`
    """
    from_timestamp = models.DateTimeField(_('from time'))
    to_timestamp = models.DateTimeField(_('to time'), blank=True, null=True)

    class Meta:
        abstract = True

    def clean(self):
        """
        :raise ValidationError: If timestamp range is empty.
        """
        super(TimestampRangeModelMixin, self).clean()
        if self.from_timestamp and self.to_timestamp and \
                self.from_timestamp >= self.to_timestamp:
            raise ValidationError(_('Period of existense must be non-empty.'))

    def format_timestamp_range_unicode(self, description, timezone):
        """
        Helper function for implementing ``unicode()`` in subclasses.

        :return: A given ``description`` prefixed with a human
            readable representation of the timestamp range in given
            ``timezone``.
        """
        if self.to_timestamp is not None:
            return '{from_timestamp} - {to_timestamp}: {description}'.format(
                from_timestamp=date_format(
                    timezone.normalize(
                        self.from_timestamp.astimezone(timezone)),
                    'SHORT_DATETIME_FORMAT'),
                to_timestamp=date_format(
                    timezone.normalize(
                        self.to_timestamp.astimezone(timezone)),
                    'SHORT_DATETIME_FORMAT'),
                description=description)
        else:
            return '{from_timestamp} - ...: {description}'.format(
                from_timestamp=date_format(
                    timezone.normalize(
                        self.from_timestamp.astimezone(timezone)),
                    'SHORT_DATETIME_FORMAT'),
                description=description)

    def overlapping(self, from_timestamp, to_timestamp):
        """
        :return: The intersection between a given timestamp range and this
            timestamp range.  If the intersection is empty an interval
            with negative duration is returned.

        :param from_timestamp: The start of the given timestamp range.
        :param to_timestamp: The end of the given timestamp range.
        """
        result_from = max(from_timestamp, self.from_timestamp)
        if self.to_timestamp:
            result_to = min(to_timestamp, self.to_timestamp)
        else:
            result_to = to_timestamp
        return (result_from, result_to)
