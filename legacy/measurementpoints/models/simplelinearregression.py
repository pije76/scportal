# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import operator
from fractions import Fraction

from django.db import models
from django.utils.translation import ugettext_lazy as _

from gridplatform.utils.unitconversion import PhysicalQuantity

from .dataseries import DataSeries
from .dataseries import UndefinedSamples
from ..fields import DataRoleField


class SimpleLinearRegression(DataSeries):
    data = models.ForeignKey(
        DataSeries, related_name='simple_linear_regression')

    class Meta(DataSeries.Meta):
        verbose_name = _('Simple linear regression')
        verbose_name_plural = _('Simple linear regressions')
        app_label = 'measurementpoints'

    def clean_fields(self, exclude=None):
        def should_clean_field(field_name):
            return not (exclude and field_name in exclude)

        if self.data:
            if should_clean_field('role'):
                self.role = DataRoleField.LINEAR_REGRESSION
            if should_clean_field('unit'):
                self.unit = self.data.unit
            if should_clean_field('utility_type'):
                self.utility_type = self.data.utility_type
            if should_clean_field('customer'):
                self.customer_id = self.data.customer_id

        super(SimpleLinearRegression, self).clean_fields(exclude=exclude)

    def depends_on(self):
        return [self.data.subclass_instance] + \
            self.data.subclass_instance.depends_on()

    def _get_samples(self, from_timestamp, to_timestamp):
        raise UndefinedSamples(
            'not supported by this linear regression implementation')

    def _get_condensed_samples(
            self, from_timestamp, sample_resolution, to_timestamp):
        data_samples = [
            sample for sample in
            self.data.get_condensed_samples(
                from_timestamp, sample_resolution, to_timestamp) if
            not (not sample and sample.extrapolated)]

        if data_samples:
            n = len(data_samples)
            y_list = [s.physical_quantity for s in data_samples]
            # x is offset as seconds after from_timestamp
            x_list = [
                PhysicalQuantity(
                    Fraction(
                        (s.from_timestamp - from_timestamp).total_seconds() +
                        (
                            s.to_timestamp -
                            s.from_timestamp).total_seconds() / 2),
                    'second')
                for s in data_samples]

            y_sum = reduce(operator.add, y_list)
            x_sum = reduce(operator.add, x_list)
            xy_sum = reduce(
                operator.add, (x * y for x, y in zip(x_list, y_list)))
            xx_sum = reduce(operator.add, (x * x for x in x_list))

            assert x_sum
            assert xx_sum
            if n / x_sum - x_sum / xx_sum:
                b = (y_sum / x_sum - xy_sum / xx_sum) / \
                    (n / x_sum - x_sum / xx_sum)

                # the following two definitions of a, must be equal, otherwise
                # b is wrong.  Also there is only one b that will satisfy the
                # following equation, so if the assertion pass, b is indeed
                # correct.
                a = (y_sum - n * b) / x_sum
                a_ = -1 * (b * x_sum - xy_sum) / xx_sum
                assert a == a_

                def y(x):
                    return a * x + b
            else:
                ZERO = PhysicalQuantity(0, self.unit)

                def y(x):
                    return ZERO

            yield self.create_point_sample(
                from_timestamp,
                y(PhysicalQuantity(0, 'second')),
                uncachable=True)

            yield self.create_point_sample(
                to_timestamp,
                y(
                    PhysicalQuantity(
                        (to_timestamp - from_timestamp).total_seconds(),
                        'second')),
                uncachable=True)

    def get_preferred_unit_converter(self):
        return self.data.subclass_instance.get_preferred_unit_converter()
