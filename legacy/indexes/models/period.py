# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals


def normalize_periods(periods):
    """
    Normalize periods.

    @param periods: A list of 2-tuples [(t0, t1),...], where t0 and t1
    are datetime objects, defining nonoverlapping, but possibly
    adjacent periods (t0 marking the start of the period and t1
    marking the end of the period).

    @return: Returns a sorted list of periods [p1, p2,...], where
    no p_i and p_i+1 are adjacent.
    """
    if periods == []:
        return

    sorted_periods = sorted(periods)
    new_start = sorted_periods[0][0]
    new_stop = sorted_periods[0][1]
    for old_start, old_stop in sorted_periods[1:]:
        assert old_start <= old_stop
        assert new_start <= new_stop
        assert new_stop <= old_start

        if new_stop < old_start:
            # periods are not adjacent
            yield (new_start, new_stop)
            new_start = old_start

        new_stop = old_stop

    yield (new_start, new_stop)
