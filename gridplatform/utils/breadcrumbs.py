# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals


from collections import namedtuple


_Breadcrumb = namedtuple('Breadcrumb', ['title', 'url'])


class Breadcrumb(_Breadcrumb):
    """
    A breadcrumb, consisting of a title and an URL, though the URL is optional
    in some instances.

    Instances of this class are immutable.

    :ivar title:  The title.
    :ivar url: The URL.
    """
    __slots__ = ()

    def __new__(cls, title, url=None):
        return _Breadcrumb.__new__(cls, title, url)

    def __add__(self, other):
        raise NotImplementedError(
            'Adding to a breadcrumb object makes no sense.')


class Breadcrumbs(tuple):
    """
    A tuple/sequence of :class:`.Breadcrumb`.

    Instances of this class are immutable.

    Only the last :class:`.Breadcrumb` may have a URL that is ``None``.
    """
    __slots__ = ()

    def __new__(cls, elems=()):
        for elem in elems:
            assert isinstance(elem, Breadcrumb), \
                'Not a Breadcrumb: {}'.format(elem)
        for elem in elems[:-1]:
            assert elem.url is not None, \
                'Breadcrumb without URL: {}'.format(elem)
        return tuple.__new__(cls, elems)

    def __add__(self, other):
        """
        Add a :class:`.Breadcrumb` to this; returning the result as a new
        :class:`.Breadcrumbs` object.
        """
        assert isinstance(other, Breadcrumb)
        return Breadcrumbs(tuple(self) + (other,))
