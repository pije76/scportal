# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import traceback
import warnings
from django import forms

from legacy.manage_collections.views import NoUrlClearableFileInput


class MeasurementPointForm(forms.ModelForm):
    """
    Maps proxy instance properties to form fields initial values, and
    the other way; maps fields from form to proxy instance properties.

    To take advantage of this functionaly, fill in the fields in the internal
    ProxyMeta class. Please notice that fields are mapped by their name.
    """
    class ProxyMeta:
        fields = []

    def __init__(self, *args, **kwargs):
        """
        @param utility_type: Optional argument to initialize resource type of
        C{self.instance}.
        """
        utility_type = kwargs.pop('utility_type', None)
        super(MeasurementPointForm, self).__init__(*args, **kwargs)
        if utility_type:
            self.instance.utility_type = utility_type

        # Assign form fields intial values from corresponding model properties
        for field in self.ProxyMeta.fields:
            self.initial[field] = getattr(self.instance, field)

        if 'image' in self.fields:
            self.fields['image'].widget.__class__ = NoUrlClearableFileInput

    def clean(self):
        # Assign form fields to corresponding model properties.  Must be done
        # before calling super clean() as super clean() will call clean on
        # self.instance.
        for field in self.ProxyMeta.fields:
            setattr(self.instance, field, self.cleaned_data.get(field, None))

        cleaned_data = super(MeasurementPointForm, self).clean()

        return cleaned_data

    def get_headline_display(self):
        """
        To be called directly from template.

        @return: The localized headline to be used for this form.
        """
        try:
            if self.instance.id:
                return self._get_edit_headline_display()
            else:
                return self._get_new_headline_display()
        except:
            # Django is kind enough to replace a useful stacktrace with
            # XYZXYZXYZ in template output. Until that error camouflage has
            # been removed, this remains a work-around.
            warnings.warn(
                '%s.get_headline_display() raised an exception\n%s' %
                (self.__class__, traceback.format_exc()))
            raise

    def _get_new_headline_display(self):
        """
        Abstract method.

        Not to be called directly.  See L{get_headline_display}

        @return: The localized headline to be used for new measurement points.
        """
        raise NotImplementedError()

    def _get_edit_headline_display(self):
        """
        Abstract method.

        Not to be called directly.  See L{get_headline_display}

        @return: The localized headline to be used for editing existing
        measurement points.
        """
        raise NotImplementedError()
