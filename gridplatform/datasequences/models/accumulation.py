# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import itertools

from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from gridplatform.customer_datasources.models import DataSource
from gridplatform.utils.decorators import virtual
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.iter_ext import count_extended
from gridplatform.utils.iter_ext import pairwise
from gridplatform.utils.models import StoreSubclass
from gridplatform.utils.models import StoredSubclassManager
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.units import ACCUMULATION_BASE_UNITS
from gridplatform.utils.units import IMPULSE_BASE_UNITS
from gridplatform.utils.samples import Sample

from .base import PeriodBaseManager
from .base import DataSequenceBase
from .base import PeriodBase
from .base import is_clock_hour
from ..utils import aggregate_sum_ranged_sample_sequence


class AccumulationBase(DataSequenceBase):
    """
    Abstract implementation of accumulation interface in terms of
    ``self.period_set``.  Note that the actual relation with periods must be
    defined on concrete subclasses.
    """
    class Meta:
        abstract = True
        app_label = 'datasequences'

    def _hourly_accumulated(self, from_timestamp, to_timestamp):
        """
        :return: a sequence of accumulating ranged samples for given timespan in
            hourly resolution.
        :param from_timestamp:  The start of the given timespan.
        :param to_timestamp:  The end of the given timespan.

        :see: Used to implement :meth:`.AccumulationBase.development_sequence`.
        """
        for period in self.period_set.in_range(
                from_timestamp, to_timestamp).order_by('from_timestamp'):
            period_from, period_to = period.overlapping(
                from_timestamp, to_timestamp)
            for sample in period._hourly_accumulated(
                    period_from, period_to):
                yield sample

    def _five_minute_accumulated(self, from_timestamp, to_timestamp):
        """
        :return: a sequence of accumulating ranged samples for given timespan in
            five-minute resolution.
        :param from_timestamp:  The start of the given timespan.
        :param to_timestamp:  The end of the given timespan.

        :see: Used to implement :meth:`.AccumulationBase.development_sequence`.
        """
        for period in self.period_set.in_range(
                from_timestamp, to_timestamp).order_by('from_timestamp'):
            period_from, period_to = period.overlapping(
                from_timestamp, to_timestamp)
            for sample in period._five_minute_accumulated(
                    period_from, period_to):
                yield sample

    def development_sequence(self, from_timestamp, to_timestamp, resolution):
        """
        :return: a sequence of accumulating ranged samples for given period in
            given resolution.

        :param from_timestamp: the start of the given period.
        :param to_timestamp: the end of the given period.
        :param resolution: the given resolution.
        """
        if resolution == RelativeTimeDelta(minutes=5):
            return self._five_minute_accumulated(from_timestamp, to_timestamp)
        elif resolution == RelativeTimeDelta(hours=1):
            return self._hourly_accumulated(from_timestamp, to_timestamp)
        else:
            data = self._hourly_accumulated(from_timestamp, to_timestamp)
            return aggregate_sum_ranged_sample_sequence(
                data, resolution, self.customer.timezone)

    def development_sum(self, from_timestamp, to_timestamp):
        """
        :return: The total accumulated in the given timespan.
        :rtype: :class:`.PhysicalQuantity`

        :param from_timestamp:  The start of the given timespan.
        :param to_timestamp:  The end of the given timespan.

        :note: Will return PhysicalQuantity(0, self.unit) if no samples in period.
            For occasions where zero due to no samples should somehow be considered
            different from zero from actual samples, if that ever occurs, use
            separate quality control

        :precondition: The given timespan must be on the hour.
        """
        assert is_clock_hour(from_timestamp), \
            '%r does not match clock hour' % from_timestamp
        assert is_clock_hour(to_timestamp), \
            '%r does not match clock hour' % to_timestamp
        samples = self._hourly_accumulated(from_timestamp, to_timestamp)
        value = sum(
            (s.physical_quantity for s in samples),
            PhysicalQuantity(0, self.unit))
        return value


class AccumulationPeriodManager(
        PeriodBaseManager, StoredSubclassManager):
    """
    Manager for :class:`.AccumulationPeriodBase` that inherits from both
    :class:`.PeriodBaseManager` and :class:`.StoredSubclassManager`.
    """
    pass


class AccumulationPeriodBase(StoreSubclass, PeriodBase):
    """
    Abstract :class:`.PeriodBase` specialisation that delegates accumulation
    period interface to subclasses.  This is also an abstract Django model
    (e.g. this model cannot be queried, but subclasses inherit the manager).

    Assumes concrete specialization has a ``datasequence`` foreign key to some
    :class:`.AccumulationDataSequence` specialization.

    :ivar objects: The default manager for :class:`.AccumulationPeriodBase` is
        :class:`.AccumulationPeriodManager`.
    """
    objects = AccumulationPeriodManager()

    class Meta:
        abstract = True
        app_label = 'datasequences'

    @virtual
    def _hourly_accumulated(self, from_timestamp, to_timestamp):
        """
        Abstract delegate of :meth:`.AccumulationBase._hourly_accumulated` within
        the timespan of this period.
        """
        raise NotImplementedError(self.__class__)

    @virtual
    def _five_minute_accumulated(self, from_timestamp, to_timestamp):
        """
        Abstract delegate of :meth:`.AccumulationBase._hourly_accumulated` within
        the timespan of this period.
        """
        raise NotImplementedError(self.__class__)

    @virtual
    def _get_unit(self):
        """
        Abstract method returning the unit of this period.
        """
        raise NotImplementedError(self.__class__)


class NonpulseAccumulationPeriodMixin(models.Model):
    """
    Mixes nonpulse datasource implementations of abstract methods defined in
    :class:`.AccumulationPeriodBase` into a :class:`.AccumulationPeriodBase`
    specialization.

    :ivar datasource: The non-pulse, accumulating :class:`.DataSource` defining
        the data of owning accumulation within the mixed period.
    """
    datasource = models.ForeignKey(
        DataSource,
        verbose_name=_('data source'),
        limit_choices_to={'unit__in': ACCUMULATION_BASE_UNITS},
        on_delete=models.PROTECT,
        related_name='+')

    class Meta:
        abstract = True
        app_label = 'datasequences'

    def clean(self):
        """
        :raise ValidationError: If the units of data source and data sequence don't
            match.
        """
        super(NonpulseAccumulationPeriodMixin, self).clean()
        if self.datasource_id and self.datasequence_id and not \
                PhysicalQuantity.compatible_units(
                    self.datasource.unit, self.datasequence.unit):
            raise ValidationError(
                _('Input configuration and data source '
                  'units are not compatible'))

    def _hourly_accumulated(self, from_timestamp, to_timestamp):
        """
        Delegates to data source.
        """
        return self.datasource.hourly_accumulated(
            from_timestamp, to_timestamp)

    def _five_minute_accumulated(self, from_timestamp, to_timestamp):
        """
        Delegates to data source.
        """
        return self.datasource.five_minute_accumulated(
            from_timestamp, to_timestamp)

    def _get_unit(self):
        """
        Delegates to data source.
        """
        return self.datasource.unit


class PulseAccumulationPeriodMixin(models.Model):
    """
    Mixes pulse datasource implementations of abstract methods defined in
    :class:`.AccumulationPeriodBase` into a :class:`.AccumulationPeriodBase`
    specialization.

    :ivar datasource: The pulse accumulating :class:`.DataSource` defining the
        data of owning accumulation within the mixed period.

    Pulses are converted to nonpulse data using the pulse conversion equation
    stating that ``PhysicalQuantity(self.pulse_quantity, 'impulse')``
    corresponds to ``PhysicalQuantity(self.output_quantity,
    self.output_unit)``.

    :ivar pulse_quantity: quantity of pulse side of conversion equation.
    :ivar output_quantity:  quantity of output side of conversion equation.
    :ivar output_unit: unit of output side of conversion equation.

    :ivar _conversion_factor: Cached property holding a
        :class:`.PysicalQuantity` that when multiplied with a pulse
        :class:`.PysicalQuantity` result in an output
        :class:`.PysicalQuantity`.
    """

    datasource = models.ForeignKey(
        DataSource,
        verbose_name=_('data source'),
        limit_choices_to={'unit__in': IMPULSE_BASE_UNITS},
        on_delete=models.PROTECT,
        related_name='+')

    class Meta:
        abstract = True
        app_label = 'datasequences'

    pulse_quantity = models.IntegerField(_('pulse quantity'))
    output_quantity = models.IntegerField(_('output quantity'))
    output_unit = BuckinghamField(_('output unit'))

    def clean(self):
        super(PulseAccumulationPeriodMixin, self).clean()
        if self.output_unit and self.datasequence_id:
            datasequence = self._meta.get_field('datasequence').rel.to.objects.get(pk=self.datasequence_id)

            if not PhysicalQuantity.compatible_units(
                    self.output_unit, datasequence.unit):
                raise ValidationError(
                    _('Input configuration and output '
                      'units are not compatible'))

    @cached_property
    def _conversion_factor(self):
        pulse_quantity = PhysicalQuantity(self.pulse_quantity, 'impulse')
        output_quantity = PhysicalQuantity(
            self.output_quantity, self.output_unit)
        return output_quantity / pulse_quantity

    def _convert_sample(self, sample):
        """
        Converts a given pulse sample to an output sample using
        ``self._conversion_factor``.
        """
        return sample._replace(
            physical_quantity=self._conversion_factor *
            sample.physical_quantity)

    def _hourly_accumulated(self, from_timestamp, to_timestamp):
        """
        Implementation of :meth:`.AccumulationPeriodBase._hourly_accumulated`
        yielding pulse samples converted to output samples.
        """
        return itertools.imap(
            self._convert_sample,
            self.datasource.hourly_accumulated(
                from_timestamp, to_timestamp))

    def _five_minute_accumulated(self, from_timestamp, to_timestamp):
        """
        Implementation of :meth:`.AccumulationPeriodBase._five_minute_accumulated`
        yielding pulse samples converted to output samples.
        """
        return itertools.imap(
            self._convert_sample,
            self.datasource.five_minute_accumulated(
                from_timestamp, to_timestamp))

    def _get_unit(self):
        return self.datasource.unit


class SingleValueAccumulationPeriodMixin(models.Model):
    """
    Mixes fixed value implementations of abstract methods defined in
    :class:`.AccumulationPeriodBase` into a :class:`.AccumulationPeriodBase`
    specialization.

    :ivar value:  The value accumulated uniformly over this period.
    :ivar unit:  The unit of ``self.value``.

    :ivar _accumulation_rate: The slope of the uniformly accumulated value of
        this period in the forms of a :class:`.PhysicalQuantity`.
    """
    value = models.BigIntegerField(_('value'))
    # Is actually used as a choice field, thus the get_unit_display method is
    # defined below.
    unit = BuckinghamField(_('unit'))

    class Meta:
        abstract = True
        app_label = 'datasequences'

    def clean(self):
        """
        :raise ValidationError: If ``self.to_timestamp`` is not set.
        :raise ValidationError: If ``self.unit`` and the unit of owning data
            sequence are not compatible.
        """
        super(SingleValueAccumulationPeriodMixin, self).clean()
        if not self.to_timestamp:
            raise ValidationError(
                _('The "to time" is required for single value periods.')
            )
        if self.datasequence and self.unit and not \
                PhysicalQuantity.compatible_units(
                    self.datasequence.unit, self.unit):
            raise ValidationError(
                _('The chosen unit is not compatible.')
            )

    @cached_property
    def _accumulation_rate(self):
        total_quantity = PhysicalQuantity(self.value, self.unit)
        total_duration = PhysicalQuantity(
            (self.to_timestamp - self.from_timestamp).total_seconds(),
            'second')
        return total_quantity / total_duration

    def _period_accumulated(self, from_timestamp, to_timestamp, resolution):
        """
        Returns a sequence of ranged accumulation samples across given timespan in
        given resolution.

        The slope of the accumulation in each sample will equal
        ``self._accumulation_rate``.

        :param from_timestamp: The start of the given timespan.
        :param to_timestamp: The end of the given timespan.
        :param datetime.timedelta resolution: The given resolution. Note this
            is not a :class:`.RelativeTimeDelta` instance.
        """
        assert self.from_timestamp <= from_timestamp <= self.to_timestamp
        assert self.from_timestamp <= to_timestamp <= self.to_timestamp
        sample_duration = PhysicalQuantity(
            resolution.total_seconds(), 'second')
        quantity = self._accumulation_rate * sample_duration

        for from_timestamp_, to_timestamp_ in pairwise(
                count_extended(from_timestamp, resolution)):
            yield Sample(from_timestamp_, to_timestamp_, quantity, True, False)
            if to_timestamp_ >= to_timestamp:
                break

    def _hourly_accumulated(self, from_timestamp, to_timestamp):
        """
        Implementation of :meth:`.AccumulationPeriodBase._hourly_accumulated`
        delegating to :meth:`._period_accumulated` with resolution of one hour.
        """
        return self._period_accumulated(
            from_timestamp, to_timestamp, datetime.timedelta(hours=1))

    def _five_minute_accumulated(self, from_timestamp, to_timestamp):
        """
        Implementation of :meth:`.AccumulationPeriodBase._five_minute_accumulated`
        delegating to :meth:`._period_accumulated` with resolution of five minutes.
        """
        return self._period_accumulated(
            from_timestamp, to_timestamp, datetime.timedelta(minutes=5))
