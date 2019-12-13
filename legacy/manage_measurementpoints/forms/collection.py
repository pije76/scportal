# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms

from legacy.measurementpoints.models import Collection
from gridplatform import trackuser


class CollectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CollectionForm, self).__init__(*args, **kwargs)

        self.fields['parent'].queryset = \
            self.fields['parent'].queryset.filter(
                customer=trackuser.get_customer(),
                role__in=Collection.PARENTS)

        if self.instance.id:
            subtree = self.instance.get_descendants(
                include_self=True).values_list('id', flat=True)
            self.fields['parent'].queryset = \
                self.fields['parent'].queryset.exclude(id__in=subtree)

    class Meta:
        model = Collection
        fields = ('name', 'parent')
        localized_fields = '__all__'
