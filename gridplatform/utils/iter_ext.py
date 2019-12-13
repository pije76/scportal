# -*- coding: utf-8 -*-
"""
More iterator building blocks, based on
http://docs.python.org/2/library/itertools.html#recipes
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import itertools


def nwise(iterable, n, tee=itertools.tee, izip=itertools.izip):
    """
    >>> nwise([s0, s1, ...], n)   # doctest: +SKIP
    (s_0,...,s_n-1), (s1,..,s_n), (s2,...,s_n+1), ...
    """
    iterators = tee(iterable, n)
    for count, iterator in enumerate(iterators):
        for i in range(count):
            next(iterator, None)
    return izip(*iterators)


def triplewise(iterable, tee=itertools.tee, izip=itertools.izip):
    """
    >>> triplewise([s0, s1, s2, s3, s4, ...])   # doctest: +SKIP
    (s0,s1,s2), (s1,s2,s3), (s2,s3,s4), ...
    """
    a, b, c = tee(iterable, 3)
    next(b, None)
    next(c, None)
    next(c, None)
    return izip(a, b, c)


def pairwise(iterable, tee=itertools.tee, izip=itertools.izip):
    """
    >>> pairwise([s0, s1, s2, s3, ...])   # doctest: +SKIP
    (s0,s1), (s1,s2), (s2,s3), ...
    """
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


def pairwise_extended(iterable,
                      tee=itertools.tee, izip_longest=itertools.izip_longest):
    """
    >>> pairwise_extended([s0, s1, s2, s3, ... sn])   # doctest: +SKIP
    (s0,s1), (s1,s2), (s2,s3), ..., (s_n,None)
    """
    a, b = tee(iterable)
    next(b, None)
    return izip_longest(a, b)


def flatten(listOfLists, chain=itertools.chain):
    """
    Flatten one level of nesting
    """
    return chain.from_iterable(listOfLists)


def tee_lookahead(t, i, islice=itertools.islice):
    """
    Inspect the i-th upcomping value from a tee object while leaving the tee
    object at its current position.

    :raise IndexError: If the underlying iterator doesn't have enough
        values.
    """
    for value in islice(t.__copy__(), i, None):
        return value
    raise IndexError(i)


def count_extended(start, step):
    """
    Similar to itertools.count, but itertools.count only works for numbers.
    (Based on the "equivalent Python code" for itertools.count.)

    >>> count_extended(datetime.date(2000, 1, 1), datetime.timedelta(days=1))  # noqa doctest: +SKIP
    datetime.date(2000, 1, 1), datetime.date(2000, 1, 2), ...
    """
    n = start
    while True:
        yield n
        n += step
