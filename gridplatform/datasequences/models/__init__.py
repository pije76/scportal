# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.functional import cached_property

from .accumulation import AccumulationBase
from .accumulation import AccumulationPeriodBase
from .accumulation import NonpulseAccumulationPeriodMixin
from .accumulation import PulseAccumulationPeriodMixin
from .accumulation import SingleValueAccumulationPeriodMixin
from .base import DataSequenceBase
from .base import PeriodBase
from .base import is_clock_hour
from .piecewiseconstant import PiecewiseConstantBase
from .piecewiseconstant import PiecewiseConstantPeriodBase
from .piecewiseconstant import PiecewiseConstantPeriodManager

from .energyconversion import EnergyPerVolumeDataSequence
from .energyconversion import EnergyPerVolumePeriod
from .nonaccumulation import NonaccumulationDataSequence
from .nonaccumulation import NonaccumulationPeriod
from .qualitycontrol import OfflineToleranceMixin
from .qualitycontrol import NonaccumulationOfflineTolerance

__all__ = [
    'PeriodBase',
    'AccumulationBase',
    'AccumulationPeriodBase',
    'DataSequence',
    'DataSequenceBase',
    'EnergyPerVolumeDataSequence',
    'EnergyPerVolumePeriod',
    'NonaccumulationDataSequence',
    'NonaccumulationOfflineTolerance',
    'NonaccumulationPeriod',
    'NonpulseAccumulationPeriodMixin',
    'PiecewiseConstantBase',
    'PiecewiseConstantPeriodBase',
    'PiecewiseConstantPeriodManager',
    'PeriodBase',
    'PulseAccumulationPeriodMixin',
    'SingleValueAccumulationPeriodMixin',
    'OfflineToleranceMixin',
    'CurrencyUnitMixin',
    'is_clock_hour'
]


class CurrencyUnitMixin(object):
    """
    Gives ``self.currency_unit`` property, given `self.unit` contains a
    currency.
    """
    @cached_property
    def currency_unit(self):
        currency_units = ['currency_dkk', 'currency_eur']
        for currency_unit in currency_units:
            if currency_unit in self.unit:
                return currency_unit
        assert False, 'currency unit in "%s" not recognized' % (
            self.unit)
