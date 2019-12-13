.. _co2-conversions:

CO₂ Conversions
===============

The CO₂ Conversions app define a small class hierachy of CO₂
Conversions.  The base class is :py:class:`Co2Conversion`, which is
abstract in the OO sense.  :py:class:`Co2Conversion` is inherited by
:py:class:`DynamicCo2Conversion` and :py:class:`FixedCo2Conversion`
which are both concrete.

.. autoclass:: gridplatform.co2conversions.models.Co2Conversion
   :members: clean, _value_sequence

.. autoclass:: gridplatform.co2conversions.models.DynamicCo2Conversion
   :members: clean

.. autoclass:: gridplatform.co2conversions.models.FixedCo2Conversion
   :members: clean
