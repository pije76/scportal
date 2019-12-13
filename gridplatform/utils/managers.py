# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models


class DateRangeManagerMixin(object):
    """
    Mixes :meth:`~.DateRangeManagerMixin.in_range` into mixed manager.
    Intended for managers used for
    :class:`~gridplatform.utils.models.DateRangeModelMixin` mixed
    models.
    """

    def in_range(self, from_date, to_date):
        """
        A queryset of rows that have a non-empty overlap with the given range.

        :param from_date: Rows must be overlapping with this date or
            later.
        :param to_date: Rows must be overlapping with this date or
            earlier.
        """
        return self.filter(
            (
                models.Q(to_date__gte=from_date) |
                models.Q(to_date__isnull=True)),
            from_date__lt=to_date)


class TimestampRangeManagerMixin(object):
    """
    Mixes :meth:`~.TimestampRangeManagerMixin.in_range` into mixed
    manager.  Intended for managers used for
    :class:`~gridplatform.utils.models.TimestampRangeModelMixin` mixed
    models.
    """

    def in_range(self, from_timestamp, to_timestamp):
        """
        A queryset of rows that have a non-empty overlap with the given
        range.

        :param from_timestamp: The start point of the given range.
        :param to_timestamp: The end point of the given range.
        """
        return self.filter(
            (
                models.Q(to_timestamp__gte=from_timestamp) |
                models.Q(to_timestamp__isnull=True)),
            from_timestamp__lt=to_timestamp)
