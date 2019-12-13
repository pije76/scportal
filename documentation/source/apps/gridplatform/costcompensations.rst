Cost Compensations
==================

Cost compensations are described in the domain model in the section
:ref:`cost-compensations`.  To facilitate changes in the domain, as mentioned
in :ref:`changes-in-domain`, the
:py:class:`~gridplatform.cost_compensations.models.CostCompensation` is defined
in terms of periods, namely
:py:class:`~gridplatform.cost_compensations.models.FixedCompensationPeriod`.
The periods are associated to cost compensations via the
:py:class:`~gridplatform.cost_compensations.models.CostCompensationPeriodManager`.

A simpler design for solving a simular task is described in
:ref:`co2-conversions`.

.. autoclass:: gridplatform.cost_compensations.models.CostCompensation

.. autoclass:: gridplatform.cost_compensations.models.CostCompensationPeriodManager
   :members: value_sequence

.. autoclass:: gridplatform.cost_compensations.models.Period


.. autoclass:: gridplatform.cost_compensations.models.FixedCompensationPeriod
   :members: clean
