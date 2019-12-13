Condensing
========================================================

This app defines models and utilities to optimize the data of
:py:class:`DataSources<.DataSource>` for further computations.  In particular
many computations benifit from working on samples with fixed durations, mostly
this duration is one hour, but some times it is five minutes.

The the timestamps of :py:class:`.RawData` are not always guaranteed to be on
the hour (or a five minute multiplum), in particular not those that stem from
meters.  Therefore interpolation is often required.  Interpolation is
computation wise relative expensive on :class:`datetime.datetime` objects.

So what this app does is compute relevant
:py:class:`RangedSamples<.RangedSample>` for relevant
:py:class:`DataSources<.DataSource>` and store them in the database (as
:py:class:`.HourAccumulatedData` and :py:class:`.FiveMinuteAccumulatedData`).
This gives a performance boost by order of magnitude as they only need to be
computed once, and the extra space taken up by these values is not an issue.

Models
------

.. automodule:: gridplatform.condensing.models
   :members: validate_hour, validate_five_minutes, AccumulatedData,
             HourAccumulatedData, FiveMinuteAccumulatedData,
             cleanup_cache_for_rawdata_delete, get_hourly_accumulated,
             get_five_minute_accumulated, get_accumulated, generate_cache,
             missing_periods, generate_period_data, raw_data_for_cache,
             adjust_from_to, period_aligned

Commands
--------

.. automodule:: gridplatform.condensing.management.commands.generate_cache
