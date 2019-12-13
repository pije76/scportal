import django_filters


class DecryptingSearchFilter(django_filters.CharFilter):
    """
    A :class:`django_filters.CharFilter` specialization that supports searching
    in encrypted char fields.
    """
    def filter(self, qs, value):
        if value in ([], (), {}, None, ''):
            return qs
        return qs.decrypting_search(value, [self.name])
