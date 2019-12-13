.. _changes-in-domain:

Changes in the Domain
=====================

Occationally, one of the following will happen:

  * A new main consumption is installed.
  * An existing main consumption is discontinued.
  * A new energy use is introduced.
  * An existing energy use is disconnected.
  * A new data source is introduced.
  * A data source is replaced in some application (say a new meter is
    installed, or a different tariff is applied).

It is not enough to model the state of the domain at just a single
point in time.  The state of the domain needs to be modelled with
support for historical changes.
