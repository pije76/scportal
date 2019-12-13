# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import itertools

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from gridplatform.trackuser import get_customer
from gridplatform.utils.iter_ext import pairwise_extended
from gridplatform.utils.relativetimedelta import DATETIME_MAX
from gridplatform.utils import condense
from gridplatform.utils.unitconversion import PhysicalQuantity

from .dataseries import DataSeries


class Chain(DataSeries):
    """
    A C{Chain} is a L{DataSeries} defined in terms of chained segments of other
    L{DataSeries}.
    """
    chained_data_series = models.ManyToManyField(
        DataSeries, related_name='chain_derivative_set',
        through='measurementpoints.ChainLink',
        symmetrical=False)

    class Meta(DataSeries.Meta):
        verbose_name = _('chain')
        verbose_name_plural = _('chains')
        app_label = 'measurementpoints'

    def _get_samples(self, from_timestamp, to_timestamp):
        """
        C{Chain} implementation of L{DataSeries.get_raw_data_samples()}
        """
        for link in self.iterate_links(from_timestamp, to_timestamp):
            for sample in link.data_series.subclass_instance.\
                    get_samples(
                        max(from_timestamp, link.valid_from),
                        min(to_timestamp, link.get_valid_to())):
                assert sample.physical_quantity.compatible_unit(self.unit)
                yield sample

    def iterate_links(self, from_timestamp, to_timestamp):
        """
        Iterate links in this C{Chain} covering a given timespan.

        @param from_timestamp: The start of the timespan.

        @param to_timestamp: The end of the timespan.
        """
        result = self.links.filter(
            valid_from__gte=from_timestamp,
            valid_from__lt=to_timestamp).order_by('valid_from')

        if not result or result[0].valid_from >= from_timestamp:
            try:
                result = itertools.chain(
                    [self.links.filter(
                        valid_from__lt=from_timestamp).order_by(
                        '-valid_from')[0]], result)
            except IndexError:
                pass

        # annotate yielded links with precalculated C{valid_to}.
        for l1, l2 in pairwise_extended(result):
            if l2 is not None:
                l1._valid_to = l2.valid_from
            else:
                l1._valid_to = DATETIME_MAX
            yield l1

    def get_recursive_condense_resolution(self, resolution):
        return condense.next_resolution(resolution)


def _customer_now():
    customer = get_customer()
    if customer:
        return customer.now()
    else:
        return None


class ChainLink(models.Model):
    """
    Support model for L{Chain} model
    """
    chain = models.ForeignKey(Chain, on_delete=models.CASCADE,
                              related_name='links')
    data_series = models.ForeignKey(DataSeries, on_delete=models.PROTECT,
                                    related_name='chainlink_data_series')
    valid_from = models.DateTimeField(default=_customer_now)

    # NOTE: We may wish to specify a date rather than timestamp in the UI ---
    # but for computations, we need an absolute timestamp, and to ensure
    # consistent use/to only have the rules for translating date to timestamp
    # (taking time zone into account) once, we store the resulting datetime.

    class Meta:
        verbose_name = _('chain link')
        verbose_name_plural = _('chain links')
        app_label = 'measurementpoints'
        unique_together = (('chain', 'valid_from'))
        ordering = ['valid_from']

    def clean(self):
        try:
            chain = self.chain
            data_series = self.data_series
        except DataSeries.DoesNotExist:
            pass
        else:
            if self.chain.unit and \
                    not PhysicalQuantity.compatible_units(chain.unit,
                                                          data_series.unit):
                raise ValidationError(
                    {
                        'data_series': [
                            ValidationError(
                                _('The unit of the selected data series is '
                                  'incompatible with this chain'),
                                code='incompatible_units')]})

    def __unicode__(self):
        return '%s (%s %s)' % (self.data_series, self.chain, self.valid_from)

    def __repr__(self):
        return '<%s: id=%s, chain=%s, data_series=%s, valid_from=%s>' % (
            self.__class__.__name__, self.id, self.chain_id,
            self.data_series_id, self.valid_from)

    def get_valid_to(self):
        """
        The C{datetime} marking the end of this C{ChainLink}

        @note: Actually returning C{valid_from} data of next C{Period} object.
        In case of no other C{ChainLink} exists, L{DATETIME_MAX} is returned.

        @return: A C{datetime} marking the end of this C{ChainLink}
        """
        if hasattr(self, '_valid_to'):
            return self._valid_to

        ls = ChainLink.objects.filter(
            chain=self.chain,
            valid_from__gt=self.valid_from).\
            order_by(
                'valid_from').values_list('valid_from', flat=True)[:1]
        if ls:
            self._valid_to = ls[0]
            return self._valid_to
        else:
            return DATETIME_MAX
