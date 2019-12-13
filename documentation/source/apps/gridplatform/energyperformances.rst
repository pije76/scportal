Energy Performances
===================

Energy performances are defined in the domain model in the section
:ref:`adjustments-etc`.  The ``energyperformances`` app defines a class hierachy of
energy performances.  Notably, there is the base class
:py:class:`~gridplatform.energyperformances.models.EnergyPerformance` which is
specialized by
:py:class:`~gridplatform.energyperformances.models.ProductionEnergyPerformance`
(based on production adjustments) and
:py:class:`~gridplatform.energyperformances.models.TimeEnergyPerformance`
(based on duration adjustments).


.. autoclass:: gridplatform.energyperformances.models.EnergyPerformance
   :members: compute_performance

.. autoclass:: gridplatform.energyperformances.models.ProductionEnergyPerformance
   :members: compute_performance, clean_fields

.. autoclass:: gridplatform.energyperformances.models.TimeEnergyPerformance
   :members: compute_performance
