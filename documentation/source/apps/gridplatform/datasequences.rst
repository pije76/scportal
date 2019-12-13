Data Sequences
==============

Data sequences are the glue between sources of data and applications of data.
To support :ref:`changes-in-domain` data sequences are defined in terms of
periods.  This app defines base classes and utility functions and utility
classes related to this task.

Models
------

.. autoclass:: gridplatform.datasequences.models.CurrencyUnitMixin

Base
~~~~

.. autofunction:: gridplatform.datasequences.models.base.is_clock_hour
.. autofunction:: gridplatform.datasequences.models.base.is_five_minute_multiplum
.. autoclass:: gridplatform.datasequences.models.DataSequenceBase
   :members: next_valid_date, previous_valid_date, validate_requirements
.. autoclass:: gridplatform.datasequences.models.base.PeriodBaseManager
   :members: in_range
.. autoclass:: gridplatform.datasequences.models.PeriodBase
   :members: clean, clean_overlapping_periods

Accumulation
~~~~~~~~~~~~

.. autoclass:: gridplatform.datasequences.models.AccumulationBase
   :members: _hourly_accumulated, _five_minute_accumulated,
             development_sequence, development_sum
.. autoclass:: gridplatform.datasequences.models.accumulation.AccumulationPeriodManager
.. autoclass:: gridplatform.datasequences.models.AccumulationPeriodBase
   :members: _hourly_accumulated, _five_minute_accumulated, _get_unit
.. autoclass:: gridplatform.datasequences.models.NonpulseAccumulationPeriodMixin
   :members: clean, _hourly_accumulated, _five_minute_accumulated
.. autoclass:: gridplatform.datasequences.models.PulseAccumulationPeriodMixin
   :members: clean, _convert_sample, _hourly_accumulated,
             _five_minute_accumulated
.. autoclass:: gridplatform.datasequences.models.SingleValueAccumulationPeriodMixin
   :members: clean, _period_accumulated, _hourly_accumulated,
             _five_minute_accumulated

Energy Conversion
~~~~~~~~~~~~~~~~~

.. autofunction:: gridplatform.datasequences.models.energyconversion._break_into_hourly_samples
.. autoclass:: gridplatform.datasequences.models.EnergyPerVolumeDataSequence
.. autoclass:: gridplatform.datasequences.models.energyconversion.VolumeToEnergyConversionPeriodManager
   :members: value_sequence
.. autoclass:: gridplatform.datasequences.models.EnergyPerVolumePeriod
   :members: _raw_samples, _value_sequence

Nonaccumulation
~~~~~~~~~~~~~~~

.. autoclass:: gridplatform.datasequences.models.NonaccumulationDataSequence
   :members: clean, raw_sequence
.. autoclass:: gridplatform.datasequences.models.NonaccumulationPeriod
   :members: _raw_sequence

Piece-wise Constant
~~~~~~~~~~~~~~~~~~~

.. autoclass:: gridplatform.datasequences.models.PiecewiseConstantBase
.. autoclass:: gridplatform.datasequences.models.piecewiseconstant.PiecewiseConstantPeriodManagerBase
   :members: value_sequence
.. autoclass:: gridplatform.datasequences.models.PiecewiseConstantPeriodManager
.. autoclass:: gridplatform.datasequences.models.PiecewiseConstantPeriodBase
   :members: _value_sequence
.. autoclass:: gridplatform.datasequences.models.piecewiseconstant.FixedPiecewiseConstantPeriodValueSequenceMixin
   :members: _value_sequence

Quality Control
~~~~~~~~~~~~~~~

.. autoclass:: gridplatform.datasequences.models.OfflineToleranceMixin
   :members: validate_requirement
.. autoclass:: gridplatform.datasequences.models.NonaccumulationOfflineTolerance

Utilities
---------

.. automodule:: gridplatform.datasequences.utils
   :members: _pad_ranged_sample_sequence, multiply_ranged_sample_sequences,
             subtract_ranged_sample_sequences, add_ranged_sample_sequences,
             _fiveminutes_period_key, _hour_period_key, _day_period_key,
             _month_period_key, _quarter_period_key, _year_period_key,
             _PERIOD_KEYS, aggregate_sum_ranged_sample_sequence
