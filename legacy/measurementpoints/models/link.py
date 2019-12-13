# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from .dataseries import DataSeries


class Link(DataSeries):
    """
    A L{Link} is used to make a C{target} L{DataSeries} appear as a
    L{DataSeries} in another graph.

    @invariant: The C{unit} must be the same as for the C{target}
    L{DataSeries}.  This is a precondition of all sample related methods,
    because they are forwarded to their C{target} counterpart.
    """
    target = models.ForeignKey(DataSeries, on_delete=models.PROTECT,
                               related_name='link_derivative_set')

    class Meta(DataSeries.Meta):
        verbose_name = _('link')
        verbose_name_plural = _('link')
        app_label = 'measurementpoints'

    def clean(self):
        """
        L{Link} specialization of C{Model.clean()}.

        @postcondition: If C{target} is set, the class invariant holds.
        """
        self.unit = self.target.subclass_instance.unit
        self._assert_invariants()
        return super(Link, self).clean()

    def save(self, *args, **kwargs):
        self._assert_invariants()
        return super(Link, self).save(*args, **kwargs)

    def _assert_invariants(self):
        assert self.unit == self.target.subclass_instance.unit, \
            '%s != %s' % (self.unit, self.target.subclass_instance.unit)

    def _get_samples(self, from_timestamp, to_timestamp):
        self._assert_invariants()
        return self.target.subclass_instance.get_samples(
            from_timestamp, to_timestamp)

    def _get_condensed_samples(self, from_timestamp,
                               sample_resolution, to_timestamp):
        self._assert_invariants()
        return self.target.subclass_instance.get_condensed_samples(
            from_timestamp, sample_resolution, to_timestamp)

    def _interpolate_extrapolate_sample(self, timestamp,
                                        data_before=None, data_after=None):
        self._assert_invariants()
        return self.target.subclass_instance._interpolate_extrapolate_sample(
            timestamp, data_before=data_before, data_after=data_after)

    def calculate_development(self, from_timestamp, to_timestamp):
        self._assert_invariants()
        return self.target.subclass_instance.calculate_development(
            from_timestamp, to_timestamp)

    def calculate_cost(self, from_timestamp, to_timestamp, consumption=None):
        self._assert_invariants()
        return self.target.subclass_instance.calculate_cost(
            from_timestamp, to_timestamp, consumption=consumption)

    def depends_on(self):
        return self.target.subclass_instance.depends_on() + [
            self.target.subclass_instance]

    def latest_sample(self, from_timestamp, to_timestamp):
        self._assert_invariants()
        return self.target.subclass_instance.latest_sample(
            from_timestamp, to_timestamp)

    def aggregated_samples(self, from_timestamp, to_timestamp):
        self._assert_invariants()
        return self.target.subclass_instance.aggregated_samples(
            from_timestamp, to_timestamp)

    def get_recursive_condense_resolution(self, resolution):
        # Whatever is efficient for the target, ought to be efficient for
        # the link.
        return self.target.subclass_instance.\
            get_recursive_condense_resolution(resolution)
