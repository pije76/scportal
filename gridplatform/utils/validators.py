# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import operator
from datetime import datetime

import pytz
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .iter_ext import pairwise


def nonzero_validator(value):
    """
    :raise ValidationError: If ``value`` is zero.
    """
    if value == 0:
        raise ValidationError(_(u'Must be non-zero.'))


def in_the_past_validator(value):
    """
    :raise ValidationError: If ``value`` is in the future.
    """
    if value > datetime.now(pytz.utc):
        raise ValidationError(_(u'Must be in the past.'))


def clean_overlapping(models):
    """
    :raise ValidationError: If ``models`` seem overlapping.

    :param models: An iterable of :class:`~.TimestampRangeModelMixin` mixed
        models.
    """
    sorted_models = sorted(
        models, key=operator.attrgetter('from_timestamp'))
    for model, next_model in pairwise(sorted_models):
        if model.to_timestamp is None or \
                model.to_timestamp > next_model.from_timestamp:
            raise ValidationError(_('There are overlaps.'))
