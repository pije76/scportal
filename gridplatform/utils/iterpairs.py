# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from .decorators import deprecated
from .iter_ext import pairwise, pairwise_extended


# With include_final=False, this gives the same behaviour as "pairwise" on
# http://docs.python.org/2/library/itertools.html#recipes
# Having two functions is clearer than include_final here; and the behaviour of
# pairwise --- i.e. like include_final=False is a better "default", but
# changing it without renaming the function would be problematic...
@deprecated('use pairwise/pairwise_extended from gridplatform.utils.iter_ext')
def iterpairs(iterable, include_final=True):
    """
    Translate an iterable to an iterable over a sequence of pairs of (current,
    next).

    This is intended as a helper when implementing tranformations from
    (timestamp, value)-sequences to (timestamp_from, timestamp_to,
    value)-sequences, for the cases where the from/to timestamps can be taken
    from the timestamps of the "current" and "next" elements in the sequence.

    Example use::
        for current_sample, next_sample in iterpairs(samples):
            yield range_sample(
                current_sample.timestamp,
                getattr(next_sample, 'timestamp', max_time),
                current_sample.value)

    @see: L{Sample} which defines samples and
    L{range_sample<legacy.measurementpoints.samples.range_sample>} which
    construct ranged samples, such as in the example above.

    @param include_final: If C{True}, the final output pair will consist of the
    final input pair and C{None} for "next"; if C{False}, this pair will not be
    included.
    """
    if include_final:
        return pairwise_extended(iterable)
    else:
        return pairwise(iterable)
