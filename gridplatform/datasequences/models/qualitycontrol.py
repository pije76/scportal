# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from collections import namedtuple
import datetime

from django.db import connection
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator

from gridplatform.utils.iter_ext import pairwise

from .nonaccumulation import NonaccumulationDataSequence


class OfflineToleranceMixin(models.Model):
    """
    Base class for offline tolerance models.  Despite its name, this model is
    barely ever used as a mixin.

    :ivar hours:  Report error if offline for this many clock hours.

    .. class:: _Invalidation

        A named tuple with the first element named ``from_datetime`` and the
        second element named ``to_datetime``.  Used in return for
        :meth:`.OfflineToleranceMixin.validate_requirement`.
    """
    hours = models.PositiveIntegerField(
        _('clock hours'),
        help_text=_('report error if offline for this many clock hours'),
        validators=[MinValueValidator(1)])

    class Meta:
        abstract = True

    _Invalidation = namedtuple(
        'Invalidation', ('from_datetime', 'to_datetime'))

    def __unicode__(self):
        return 'report error if offline for more than {} clock hours'.format(
            self.hours)

    def validate_requirement(self, from_date, to_date):
        """
        Validate offline tolerance requirements in given date range.

        :param from_date:  The first date in the given date range.
        :param to_date:  The final date in the given date range.

        :return: A list of :class:`_Invalidations<._Invalidation>` named tuples
            where ``self.datasequence`` did not have any date for
            ``self.hours`` or more.
        """
        assert from_date <= to_date
        timezone = self.datasequence.customer.timezone
        from_timestamp = timezone.localize(datetime.datetime.combine(
            from_date,
            datetime.time()))
        to_timestamp = timezone.localize(datetime.datetime.combine(
            to_date + datetime.timedelta(days=1),
            datetime.time()))
        online_hours = []
        invalidations = []
        for period in self.datasequence.period_set.in_range(
                from_timestamp, to_timestamp).order_by('from_timestamp'):
            if not hasattr(period.subclass_instance, 'datasource'):
                continue

            overlap_from_timestamp, overlap_to_timestamp = period.overlapping(
                from_timestamp, to_timestamp)

            cursor = connection.cursor()
            cursor.execute(
                '''
                SELECT DATE_TRUNC('hour', timestamp) AS hour,
                       COUNT(*)
                FROM datasources_rawdata
                WHERE datasource_id = %s
                AND timestamp BETWEEN %s AND %s
                GROUP BY hour
                ''', [
                    period.subclass_instance.datasource_id,
                    overlap_from_timestamp,
                    overlap_to_timestamp,
                ]
            )
            online_hours.extend([
                hour for hour, count in cursor.fetchall() if count > 0])
            for a, b in pairwise(
                    sorted([from_timestamp] + online_hours + [to_timestamp])):
                if int((b - a).total_seconds() / 3600) > self.hours:
                    invalidations.append(
                        self._Invalidation(
                            from_datetime=timezone.normalize(
                                a.astimezone(timezone)),
                            to_datetime=timezone.normalize(
                                b.astimezone(timezone))))
        return invalidations


class NonaccumulationOfflineTolerance(
        OfflineToleranceMixin, models.Model):
    """
    :class:`.OfflineToleranceMixin` specialization for
    :class:`.NonaccumulationDataSequence`.

    :ivar datasequence: The :class:`.NonaccumulationDataSequence` this is the
        offline tolerance for.
    """
    datasequence = models.OneToOneField(
        NonaccumulationDataSequence,
        related_name='offlinetolerance',
        editable=False)

    class Meta:
        app_label = 'datasequences'
