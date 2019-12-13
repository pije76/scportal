Tariffs
=======

Tariffs were mentioned in the domain model under the section
:ref:`data-sources`, and also in :ref:`main-consumptions`.  To facilitate
changes in the domain, as mentioned in :ref:`changes-in-domain`, the
:py:class:`~gridplatform.tariffs.models.Tariff` (and its subclasses
:py:class:`~gridplatform.tariffs.models.EnergyTariff` and
:py:class:`~gridplatform.tariffs.models.VolumeTariff`) is defined in terms of
periods; namely :py:class:`~gridplatform.tariffs.models.FixedPricePeriod` and
:py:class:`~gridplatform.tariffs.models.SpotPricePeriod`.  The periods are
associated to tariffs via the
:py:class:`~gridplatform.tariffs.models.TariffPeriodManager`


A simpler design for solving a simular task is described in
:ref:`co2-conversions`.

.. autoclass:: gridplatform.tariffs.models.Tariff

.. autoclass:: gridplatform.tariffs.models.EnergyTariff

.. autoclass:: gridplatform.tariffs.models.VolumeTariff

.. autoclass:: gridplatform.tariffs.models.TariffPeriodManager
   :members: subscription_cost_sum, value_sequence

.. autoclass:: gridplatform.tariffs.models.FixedPricePeriod
   :members: subscription_cost_sum, clean, get_unit_choices, _value_sequence

.. autoclass:: gridplatform.tariffs.models.SpotPricePeriod
   :members: clean, _value_sequence
