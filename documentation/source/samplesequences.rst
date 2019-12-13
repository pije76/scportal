Sequences of Samples and their Operations
=========================================

Data sources continuously bring sequences of samples into the system:

  * Utility consumption (m³, kWh),
  * Pulse (impulse),
  * CO₂ conversions (tonne/kWh, tonne/m³),
  * Tariffs (EUR/kWh, EUR/m³)

Main consumptions and energy uses define other sequences of samples in
terms of:

  * Variable costs (EUR),
  * Utility consumption (m³, kWh),
  * Energy consumption (kWh),
  * CO₂ emissions,
  * Energy performances,
  * Normalized consumptions,
  * Normalized variable costs, and so on.

The sequences of samples can be classified according to what
operations can be applied to them and how they can be combined.

Sequences of Accumulating Ranged Samples
----------------------------------------

These are the most forgiving kind of sample sequences.  Each sample
covers a time range and holds a physical quantity.  Sequences of
accumulating ranged samples fit well into bar charts.

The samples of multiple such sequences having the same time range can
be added or subtracted to form a new sequence of accumulating ranged
samples.

Samples of smaller time ranges may be accumulated over larger time
ranges, forming new samples with the larger time ranges.  Doing so on
a sequence of accumulating ranged samples result in a new such
sequence.

For sequences of accumulating ranged samples accumulation across all
the samples within a given time range is generally well-defined.
Given compatible units, this enables multiple sequences of
accumulating ranged samples to be displayed in the same pie chart.

Typical units for these sequences include m³, kWh, impulse, EUR, h,
and tonne.

.. _sequences-of-conversion-ranged-samples:

Sequences of Conversion Ranged Samples
--------------------------------------

In their data structure these will resemble sequences of accumulating
ranged samples quite a lot.  And while adding (or subtracting) samples
with the same time range of sequences of conversion ranged samples
indeed result in new such sequences, and is well defined, accumulating
samples (or any other form of aggregation) across time ranges is not
well-defined.

Sequences of conversion ranged samples are typically illustrated as a
piece-wise constant function in a graph.

Typical units for these sequences include EUR/m³, EUR/kWh, kWh/m³,
m³/impulse, kWh/impulse, tonne/kWh and tonne/m³.

Note that while the units of conversion ranged samples in general seem
to be fractions, the implication does not go both ways.  There are
ranged samples whose units are fractions that can't be said to be
conversion ranged samples.  See sequences of fractional ranged
samples.

Sequences of conversion ranged samples may be sample-wise multiplied
with a sequence of accumulation ranged samples, resulting in a new
sequence of accumulation ranged samples, having the units that would
result from the multiplication (e.g. a sequence of conversion ranged
sample with unit EUR/m³ multiplied with a sequence of accumulation
ranged samples with unit m³ gives a sequence of accumulation ranged
samples with the unit EUR).  The time range of multiplied samples must
match exactly.  If the sequence of accumulated ranged samples is in a
too fine time range resolution, it should be accumulated to the matching
time resolution as described earlier before multiplication.

Sequences of Fractional Ranged Samples
--------------------------------------

Given two sequences of accumulating ranged samples, we can sample-wise
divide one with the other (if the sample of other is not zero).  A
great deal of information is lost in this process, yet the result is
often easy for humans to interpret.

Because of the information loss, no aggregation of samples across
periods is well-defined.  Sample-wise addition of two sequences of
fractional ranged samples is also not well-defined.  Data sources on
this form in general should be avoided as they provide the system with
very little information to work with.

Typical semantics of these sequences of fractional ranged samples include:

 * Marginal energy consumption (kWh/pcs),
 * Heat-loss coefficient (W/°K),
 * Cool-down temperature of distribution medium for district heating (°K),
 * Mean power (W),
 * Mean flow (m³/h),
 * Marginal CO₂ emissions (tonne/pcs),
 * Mean power factor (kWh/kVAh), and so on.

While aggregation of samples is out of the question, it is possible to
calculate sequences of fractional ranged samples in any time range
resolution in which the input sequences of accumulated ranged samples
are available.  For example mean power can both be calculated hour by
hour, and day by day.

Sequences of fractional ranged samples may be used as sequences of
conversion ranged samples in normalization of consumptions and costs.
For instance marginal energy consumption (kWh/pcs) can be used to
convert normal productions (pcs) to normalized energy consumption
(kWh).

.. _sequences-of-continuous-point-samples:

Sequences of Continuous Point Samples
-------------------------------------

These sequences sample underlying continuous functions, and may stem
from data sources, or be calculated from other sequences of continuous
point samples.

Sequences of continuous point samples are graphed by continuous
function by linear interpolation.

Typical semantics of sequences of continuous point samples include:

 * Power (W),
 * Electrical current (A),
 * Voltage (V),
 * Temperature (°K),
 * Power factor (kW/kVA),
 * Reactive power (VAr),
 * Volume flow (m³/h), and so on.

.. _sequences-of-ranged-samples-aggregating-sequences-of-continuous-point-samples:

Sequences of Ranged Samples Aggregating Sequences of Continuous Point Samples
-----------------------------------------------------------------------------

Sequences of continuous point samples can be converted to sequences of
aggregate ranged samples, by aggregation across time ranges
corresponding to the time ranges of the ranged samples in the
resulting sequence of aggregate ranged samples.  Well-defined
aggregate functions for this include average, minimum and maximum.

If the desired sequence of aggregate ranged samples alternatively can
be defined as a sequence of fractional ranged samples this is to be
preferred for its higher precision.  For instance mean power should
be defined by a sequence of fractional ranged samples, so the result
is the actual mean, and not just a sampled mean, where as mean outdoor
temperature often cannot be defined by such a sequence of fractional
ranged samples (though it would be possible to create such a meter).

Typical semantics of sequences of ranged samples aggregating sequences
of continuous point samples include:

  * Minimum outdoor temperature (°K),
  * Maximum outdoor temperature (°K),
  * Average outdoor temperature (°K).

Another interesting class of aggregate functions to consider is
conditional-time-weighed sums.  The resulting sequence of ranged
samples aggregating sequences of continuous point samples is in fact a
sequence of accumulating ranged samples.  Examples include:

 * Heating degree days (°K*days)
 * Cooling degree days (°K*days)
