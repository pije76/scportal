# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

from django import forms
from django.forms.models import ModelForm
from django.utils.translation import ugettext_lazy as _

from legacy.measurementpoints.models import ChainLink
from gridplatform.trackuser import get_customer


class IsoDateField(forms.DateField):
    """
    Crippled forms.DateField for use with JavaScript datepicker.

    In particular this field implements work-arounds for localization issues
    (the format is always ISO 8601 'YYYY-MM-DD') and the input HTML element has
    the right class, so that website.js will attach the datepicker on it
    automatically.
    """

    def __init__(self, **kwargs):
        super(IsoDateField, self).__init__(
            ['%Y-%m-%d'],
            widget=forms.DateInput(attrs={'class': 'date'}, format='%Y-%m-%d'),
            **kwargs)


class TariffPeriodForm(ModelForm):
    """
    A C{TariffPeriodForm} makes a ChainLink appear to know that it is being
    used for defining a tariff in a given period.

    The C{valid_from} is set using a date on the from which is converted to a
    datetime object as needed by the model by combining the date with 0:00 in
    the current customers timezone.
    """
    valid_from = IsoDateField(label=_('valid from'))

    class Meta:
        model = ChainLink
        fields = ('data_series', )
        localized_fields = '__all__'
        error_messages = {
            'data_series': {
                'incompatible_units': _(
                    'The selected tariff has a different currency than '
                    'existing cost calculation.'),
            }
        }

    def __init__(self, *args, **kwargs):
        super(TariffPeriodForm, self).__init__(*args, **kwargs)
        if 'valid_from' not in self.initial:
            if self.instance.valid_from is not None:
                tz = get_customer().timezone
                self.initial['valid_from'] = tz.normalize(
                    self.instance.valid_from.astimezone(tz)).date()
            else:
                self.initial['valid_from'] = get_customer.now().date()

    def clean(self):
        super(TariffPeriodForm, self).clean()
        if 'valid_from' in self.cleaned_data:
            self.instance.valid_from = datetime.datetime.combine(
                self.cleaned_data['valid_from'],
                datetime.time(0, 0, tzinfo=get_customer().timezone))
        return self.cleaned_data

    def has_changed(self):
        """
        Reimplementation of C{models.ModelForm.has_changed()}.

        This is really a work-around for a bug in Django, where the original
        dynamic initial value is not considered when detecting if a field has
        changed.
        """
        if self.empty_permitted:
            # If empty_permitted, this is one of the extra forms in a formset.
            # In that case, we don't considder a valid_from different from the
            # current time as an actual change.
            return bool([name for name in
                         self.changed_data if name != 'valid_from'])
        else:
            return super(TariffPeriodForm, self).has_changed()
