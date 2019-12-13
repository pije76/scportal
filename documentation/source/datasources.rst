.. _data-sources:

Data Sources
============

Data sources are streams of samples in the domain.  A sample consist of a
physical quantity and a timestamp (or timestamp range).  Examples of data
sources are:

  * Accumulated energy consumption measured by a particular meter (kWh),
  * Tariff for a particular utility (EUR/kWh or EUR/m³),
  * CO₂ emission quotient (kg/kWh),
  * Temperature measured by a thermometer (°K),
  * Accumulated production counted automatically on a conveyorbelt (say bottles),
  * Power measured by a particular meter (W),
  * Volume flow measured by a particular meter (m²/h), and so on.

Some data sources sample continuous functions (each physical quantity belongs
to a point in time), and some sample piecewise constant functions (each
physical quantity belongs to a range of time).
