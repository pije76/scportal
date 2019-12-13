# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django.db import models
from django.db.models import Q
from django.forms import ValidationError
from django.template import defaultfilters
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.trackuser.managers import StoredSubclassCustomerBoundManager
from gridplatform.utils import condense
from gridplatform.utils import deprecated
from gridplatform.utils.decorators import virtual

from gridplatform.utils.models import StoreSubclass
from gridplatform.utils.models import TimestampRangeModelMixin
from gridplatform.utils.managers import TimestampRangeManagerMixin
from gridplatform.utils.validators import clean_overlapping


def is_clock_hour(timestamp):
    """
    :return: True if given timestamp is on the hour.

    :param timestamp: The given timestamp.
    """
    return timestamp.minute == timestamp.second == timestamp.microsecond == 0


def is_five_minute_multiplum(timestamp):
    """
    :return: True if given timestamp is on a five minute multiplum after the
        hour.

    :param timestamp: The given timestamp.
    """
    return timestamp.minute % 5 == timestamp.second == \
        timestamp.microsecond == 0


class DataSequenceBase(
        EncryptionCustomerFieldMixin, EncryptedModel, StoreSubclass):
    """
    Base class for all data sequences.  This is an abstract model, so it cannot
    be queried directly.

    :ivar customer: The owning :class:`.Customer`.
    :ivar name: The name of this data sequence.
    :objects: The manager of data sequences are by default a
        :class:`.StoredSubclassCustomerBoundManager`.
    """
    name = EncryptedCharField(_('name'), max_length=200, blank=False)

    objects = StoredSubclassCustomerBoundManager()

    class Meta:
        abstract = True
        app_label = 'datasequences'

    @virtual
    def __unicode__(self):
        return self.name_plain

    def next_valid_date(self, date, timezone):
        """
        Get the first date after the specified that has overlap with a period
        for this datasequence --- ``None`` if no such date exists.
        """
        end_of_day = timezone.localize(
            datetime.datetime.combine(
                date + datetime.timedelta(days=1), datetime.time()))
        future_period = self.period_set.filter(
            Q(to_timestamp__gt=end_of_day) | Q(to_timestamp__isnull=True)
        ).order_by('from_timestamp').first()
        if future_period is None:
            # No periods ending after the specified date --- no future data.
            return None
        elif future_period.from_timestamp <= end_of_day:
            # Found period contains > epsilon of day after specified date.
            return date + datetime.timedelta(days=1)
        else:
            # Found period contains > epsilon of day of its from_timestamp.
            return timezone.normalize(
                future_period.from_timestamp.astimezone(timezone)).date()

    def previous_valid_date(self, date, timezone):
        """
        Get the last date before the specified that has overlap with a period
        for this datasequence --- `None` if no such date exists.
        """
        beginning_of_day = timezone.localize(
            datetime.datetime.combine(date, datetime.time()))
        past_period = self.period_set.filter(
            from_timestamp__lt=beginning_of_day).order_by(
                'from_timestamp').last()
        if past_period is None:
            return None
        elif past_period.to_timestamp is None or \
                past_period.to_timestamp >= beginning_of_day:
            return date - datetime.timedelta(days=1)
        else:
            # midnight is 00:00 --- so this might give the day after the last
            # one we have data for...
            past_to_time = timezone.normalize(
                past_period.to_timestamp.astimezone(timezone))
            if past_to_time.replace(tzinfo=None).time() == datetime.time():
                return past_to_time.date() - datetime.timedelta(days=1)
            else:
                return past_to_time.date()

    @deprecated
    def get_recursive_condense_resolution(self, resolution):
        if condense.RESOLUTIONS.index(resolution) >= \
                condense.RESOLUTIONS.index(condense.DAYS):
            return None
        else:
            return condense.next_resolution(resolution)

    def validate_requirements(self, from_date, to_date):
        """
        Validates offline tolerance requirements in given date range.

        :param from_date:  First date in the given date range.
        :param to_date:  Last date in the given date range.
        :rtype: dict

        :see: :meth:`.OfflineToleranceMixin.validate_requirement`.
        """
        invalidations = {}
        if hasattr(self, 'offlinetolerance'):
            offlinetolerance_validations = \
                self.offlinetolerance.validate_requirement(
                    from_date, to_date)
            if offlinetolerance_validations:
                invalidations[
                    'offlinetolerance'] = offlinetolerance_validations
        return invalidations


class PeriodBaseManager(TimestampRangeManagerMixin, models.Manager):
    """
    Default manager for :class:`.PeriodBase`.
    """
    use_for_related_fields = True


class PeriodBase(TimestampRangeModelMixin, models.Model):
    """
    Base class for data sequence periods.  This is an abstract model, and has
    :class:`.TimestampRangeModelMixin` mixed into it.

    Assumes concrete specialization has a ``datasequence`` foreign key to some
    :class:`.DataSequenceBase` specialization.

    :ivar objects: The default manager for data sequence periods is
        :class:`.PeriodBaseManager`

    :ivar _clean_overlapping_periods: Can be used to disable overlap checking
        by :meth:`.PeriodBase.clean`.  This is needed when multiple periods for
        the same data sequence are updated simultaneously via a formset.  The
        formset should then make sure to validate the periods for overlap.  The
        default value is ``True`` (i.e. overlap checking is enabled by
        default).  See also :meth:`.PeriodBase.clean_overlapping_periods`.
    """
    objects = PeriodBaseManager()

    class Meta:
        abstract = True
        app_label = 'datasequences'

    def __init__(self, *args, **kwargs):
        super(PeriodBase, self).__init__(*args, **kwargs)

        # Set to false to prevent clean of overlapping periods against the db.
        # it is a bug if formsets don't do this.
        self._clean_overlapping_periods = True

    def __unicode__(self):
        timezone = self.datasequence.customer.timezone
        formatted_from_timestamp = defaultfilters.date(
            timezone.normalize(
                self.from_timestamp.astimezone(timezone)),
            'SHORT_DATETIME_FORMAT')
        if self.to_timestamp:
            formatted_to_timestamp = defaultfilters.date(
                timezone.normalize(
                    self.to_timestamp.astimezone(timezone)),
                'SHORT_DATETIME_FORMAT')
        else:
            formatted_to_timestamp = _('unspecified')
        return ugettext(
            '{from_timestamp} - {to_timestamp}: {datasequence}').format(
                from_timestamp=formatted_from_timestamp,
                to_timestamp=formatted_to_timestamp,
                datasequence=self.datasequence)

    def clean(self):
        """
        :raise ValidationError: If ``self.from_timestamp`` is not on the hour.
        :raise ValidationError: If ``self.to_timestamp`` is not on the hour.
        :raise ValidationError: If ``self._clean_overlapping_periods`` is True
            and there are overlapping periods.

        :see: :meth:`.PeriodBase.clean_overlapping_periods`.
        """
        super(PeriodBase, self).clean()
        if self.from_timestamp and not is_clock_hour(self.from_timestamp):
            raise ValidationError(_('Period must start on a clock hour'))
        if self.to_timestamp and not is_clock_hour(self.to_timestamp):
            raise ValidationError(_('Period must end on a clock hour'))

        if self._clean_overlapping_periods and hasattr(self, 'datasequence'):
            periods = [
                period
                for period in self.datasequence.period_set.all()
                if period.id != self.id]
            periods.append(self)
            self.clean_overlapping_periods(periods)

    @cached_property
    def unit(self):
        return self._get_unit()

    @staticmethod
    def clean_overlapping_periods(periods):
        """
        At all times no two periods belonging to the same data sequence must be
        overlapping.  This needs to be ensured towards the database from model
        forms (the default) and towards other surviving instances in inline
        formsets (set _clean_overlapping_periods to False and call this method
        explicitly in formset.clean()).
        """
        clean_overlapping(periods)
