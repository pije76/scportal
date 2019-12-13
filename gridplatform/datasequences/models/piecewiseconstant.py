# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.utils.decorators import virtual
from gridplatform.utils.models import StoreSubclass
from gridplatform.utils.models import StoredSubclassManager
from gridplatform.utils.samples import RangedSample

from .base import DataSequenceBase
from .base import PeriodBase
from .base import PeriodBaseManager


class PiecewiseConstantBase(DataSequenceBase):
    """
    :class:`.DataSequenceBase` specialization for sequences of conversion
    :class:`RangedSample`.

    :see: :ref:`sequences-of-conversion-ranged-samples`
    """
    class Meta:
        abstract = True
        app_label = 'datasequences'


class PiecewiseConstantPeriodManagerBase(PeriodBaseManager):
    """
    Specialization of :class:`PeriodBaseManager` for
    :class:`.PiecewiseConstantPeriod`, adding
    :meth:`PiecewiseConstantPeriodManagerBase.value_sequence` to reverse
    relations (and unfortunately therefore also to the default manager).  See
    :class:`.TariffPeriodManager` for clarification and examples.
    """
    use_for_related_fields = True

    def value_sequence(self, from_timestamp, to_timestamp):
        """
        Returns a sequence of :class:`RangedSamples<RangedSample>` in within the
        given timespan.

        :param from_timestamp: The start of the given timespan.
        :param to_timestamp:  The end of the given timespan.

        :note: specializations may guarantee a particular duration of each
            :class:`RangedSample` yielded.
        """
        periods = self.in_range(
            from_timestamp, to_timestamp).order_by('from_timestamp')

        for period in periods:
            period_from, period_to = period.overlapping(
                from_timestamp, to_timestamp)
            for sample in period._value_sequence(
                    period_from, period_to):
                yield sample


class PiecewiseConstantPeriodManager(
        PiecewiseConstantPeriodManagerBase, StoredSubclassManager):
    """
    Default manager for :class:`.PiecewiseConstantPeriodBase`.  Inherits from
    both :class:`PiecewiseConstantPeriodManagerBase` and
    :class:`.StoredSubclassManager` (because the former must be used for
    reverse relations, and the later can't be used for reverse relations).
    """
    pass


class PiecewiseConstantPeriodBase(StoreSubclass, PeriodBase):
    """
    :class:`.PeriodBase` specialization for
    :class:`.PiecewiseConstantDataSequenceBase` specializations.
    :class:`.StoreSubclass` has been mixed into this model.
    """
    objects = PiecewiseConstantPeriodManager()

    class Meta:
        abstract = True
        app_label = 'datasequences'

    @virtual
    def _value_sequence(self, from_timestamp, to_timestamp):
        """
        Abstract delegate of
        :meth:`.PiecewiseConstantPeriodManagerBase.value_sequence` within
        timespan of this period.
        """
        raise NotImplementedError(self.__class__)


class FixedPiecewiseConstantPeriodValueSequenceMixin(object):
    """
    Mixes
    :meth:`FixedPiecewiseConstantPeriodValueSequenceMixin._value_sequence` into
    a :class:`.PiecewiseConstantPeriodBase` specialization that should give
    only fixed-value samples.

    The fixed piecewise constant period models must implement
    ``self._quantity`` which returns a :class:`.PhysicalQuantity`.  Also it must
    define ``self.resolution``.

    :note: This must be a mixin as opposed to an abstract specialization of
        PiecewiseConstantPeriodBase, to allow for polymorphic periods.
    """
    def _value_sequence(self, from_timestamp, to_timestamp):
        """
        Implementation of :meth:`.PiecewiseConstantPeriodBase._value_sequence`
        yielding sequences of conversion ranged samples all having the same
        value, namely that given by ``self._quantity``.
        """
        sample_from_timestamp = from_timestamp
        sample_to_timestamp = sample_from_timestamp + self.resolution
        while sample_to_timestamp <= to_timestamp:
            yield RangedSample(
                sample_from_timestamp,
                sample_to_timestamp,
                self._quantity)
            sample_from_timestamp, sample_to_timestamp = \
                sample_to_timestamp, sample_to_timestamp + self.resolution
