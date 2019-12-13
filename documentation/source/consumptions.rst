Consumptions
============

This chapter covers utility consumptions that represent energy consumption in
some form.  The utility consumptions that companies are billed for directly are
the main consumptions.  Each main consumption can be partitioned into energy
uses.

.. _main-consumptions:

Main Consumptions
-----------------

Main consumptions are individually billed sources of utilities going into a
company.  Examples of main consumptions are:

  * The power consumption measured by a main electrical meter with billing
    number.
  * The heat consumption measured by a main district heating meter with
    billing number.
  * The amount of gas measured by a main gas meter with billing number.
  * The amount of oil delivered to a oil storage tank with a billing number..

The important properties of main consumptions are that they are individually
billed, and they deal with utilties that deliver energy in some form.

The utility type of each main consumption is unambiguous.  As such knowing the
energy consumption represented by each main consumption gives the distribution
of energy on different utility types.

For a given quantity of a given utility type at a given time, the CO₂ emissions
may be determined.

Energy Uses
-----------

Energy uses are main consumptions partitioned into smaller energy consumptions
each with a particular use.  Examples of energy uses are:

  * The lighting in an office building.
  * The power used by a conveyor belt.
  * The energy used for the casting of metals.
  * The power used by a compressor.
  * The energy consumption of a freezer.

Interresting properties that can be derived from energy uses include variable
costs and CO₂ emissions.

.. _adjustments-etc:

Adjustment Factors, Energy Performances and Normalized Consumptions
-------------------------------------------------------------------

The consumptions of different periods of the same energy use are comparable if
these consumptions are adjusted by the right adjustment factors.  Adjustment
factors are determined by what we find acceptable to increase the energy
consumption, say for instance:

  * The duration of the period may be normalized to a standard period duration.
    Say one period is one week and another is 9 days we can multiply them both
    with an adjustment factor to make them both correspond to a full month.
  * The heating degree days in the period may be normalizided to standard
    heating degree days.  Say the energy used to maintain a comfortable indoor
    temperature in a cold period is larger than the energy used to maintain the
    same temperature in a warmer period.
  * The production of one period may be larger than that of another, so to
    compare the energy consumption accross such two periods for the same energy
    use, they must be adjusted wich each their production counts.

Many more adjustment factors exist.  The above examples are adjusted energy
consumptions with following normalization, and their unit ends up being energy
(kWh) also when combined.  We call these normalized energy consumptions.
Because the unit before and after normalization are the same, multiple
adjustment factors can be used in calculating a normalized energy consumption.

When adjustment factors are applied without being followed by normalization, we
have an energy performance.  Comparing energy performances is equally fair, but
differenses in energy performances can be less trivial to value.  To reiterate
the above adjustment factors:

  * Adjusting for time gives a mean power W.
  * Adjusting for heating degree days gives a mean heat loss coefficient W/°K.
  * Adjusting for production gives mean production consumption kWh/pcs.

In isolation these units make sense.  When combined we risk getting meaningless
units.  For instances both heating degree days and production are not
compatible with duration adjustment; i.e. W/s°K and W/pcs are meaningless
units.  In these cases a normalized energy consumption is preferred.  For an
already normalized consumption an energy performance may be defined by applying
an additional adjustmentfactor (or leaving out the normalization of an existing
adjustment factor).

Similar to adjustment factors, other (additional) factors may be used to define
energy performances, including utility costs and CO₂ emissions.  For example
the marginal utility cost for production (EUR/pcs) is an energy performance,
and so is the marginal CO₂ emissions for production (tonne/pcs), even burn-rate
(EUR/year) and CO₂ emission rate (tonne/year).  These factors may also be used
on normalized energy consumptions to get normalized yearly costs (EUR), or
normalized yearly CO₂ emissions (tonne).

Some adjustment factors (or other factors) represent great value to companies,
for example the production.  Energy performances based on these may be promoted
to energy performance indicators.

The adjustment factors applied need not necessarily be part of the physics
observed.  As mentioned before it is enough if one finds the adjustment factor
relevant.  For instance, it may be relevant how much energy is used for
lighting a factory per unit produced, though the production does not influence
the energy consumption of lighting proportionally (or at all), it may be
desireable to improve this performance indicator after all.  The same goes for
man hours of work and energy used for comfort heating.

In particular, if only adjustment factors being part of the physics observed,
and all the adjustment factors being part of the physics observed are applied,
the resulting energy performance becomes an informationless physical constant
defined by nature.  For instance energy (kWh) adjusted for power (W) and
time (s) will always give 1 with no unit.
