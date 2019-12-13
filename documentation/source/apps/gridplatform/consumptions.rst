Consumptions
============

This app defines models directly related to consumption, including
main consumptions, energy uses and consumption data sequences.

Main Consumption and Energy Use
-------------------------------

The consumptions app defines the models
:py:class:`~gridplatform.consumptions.models.MainConsumption` and
:py:class:`~gridplatform.consumptions.models.ConsumptionGroup`, where
the later should have been named ``EnergyUse``.  The commonality
between these two models are sufficiently big that they share a base
class
:py:class:`~gridplatform.consumptions.models.ConsumptionUnionBase`.


.. autoclass:: gridplatform.consumptions.models.ConsumptionUnionBase
   :members: energy_sum, energy_sequence, utility_sum, utility_sequence,
             net_cost_sum, net_cost_sequence,
             variable_cost_sum, variable_cost_sequence,
             costcompensation_amount_sum,
             co2_emissions_sum, co2_emissions_sequence

.. autoclass:: gridplatform.consumptions.models.MainConsumption
   :members: costcompensation_amount_sequence, total_cost_sum, fixed_cost_sum

.. autoclass:: gridplatform.consumptions.models.ConsumptionGroup
   :members: costcompensation_amount_sequence

Consumption Data Sequence
-------------------------

Secondarily the
:py:class:`~gridplatform.consumptions.models.Consumption` (a
``DataSequence`` specialization) is defined, along with small pallete
of input configuration periods.

In particular one period
:py:class:`~gridplatform.consumptions.models.NonepulsePeriod` is used
to define the ``utility_sequence()`` of ``Consumption`` directly from
``DataSource`` with the relevant utility unit, and another period
:py:class:`~gridplatform.consumptions.models.PulsePeriod` is used to
define the ``utility_sequence()`` of ``Consumption`` via pulse
conversion from ``DataSource`` with the ``"impulse"`` unit.  Finally a
period that skips the ``DataSource`` framework entirely is available,
the :py:class:`~gridplatform.consumptions.models.SingleValuePeriod`.

.. autoclass:: gridplatform.consumptions.models.Consumption
   :members: clean, energy_sequence, energy_sum,
             utility_sequence, utility_sum

.. autoclass:: gridplatform.consumptions.models.NonpulsePeriod

.. autoclass:: gridplatform.consumptions.models.PulsePeriod

.. autoclass:: gridplatform.consumptions.models.SingleValuePeriod
