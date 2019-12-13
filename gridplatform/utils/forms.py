# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from isoweek import Week

from django.utils.translation import ugettext_lazy
from django.utils.translation import ugettext as _
from django import forms
from django.core.exceptions import ValidationError

from model_utils import Choices

from gridplatform.trackuser import get_timezone
from gridplatform.trackuser import get_customer

from . import condense
from .relativetimedelta import RelativeTimeDelta


def _date_hour_to_datetime(date, hours, timezone):
    return timezone.localize(
        datetime.datetime.combine(date, datetime.time()) +
        datetime.timedelta(hours=hours))


class TimePeriodFormMixin(object):
    """
    Mixes :meth:`.TimePeriodFormMixin.clean` into a form.  The mixed
    form is required to have the following fields::

        from_date = forms.DateField()
        from_hour = forms.TypedChoiceField(
            choices=TimePeriodFormMixin.HOUR_CHOICES,
            coerce=int, empty_value=None)
        to_date = forms.DateField()
        to_hour = forms.TypedChoiceField(
            choices=TimePeriodFormMixin.HOUR_CHOICES,
            coerce=int, empty_value=None)


    :note: The fields are set on the subclasses
        :class:`.TimePeriodForm` and :class:`.TimePeriodModelForm` ---
        this is intentional.

    Due to how form fields are set up with logic in the metaclasses for
    ``forms.Form`` and ``forms.ModelForm``, "normal" field declarations only
    work on classes that inherit from either of them.  Declaring this class a
    subclass of either would, however, lead to metaclass conflict and make it
    unusable as mixin for the other...

    :cvar HOUR_CHOICES: A :class:`~model_utils.Choices` of clock hours
        00:00 ... 24:00.  These can be accessed with
        ``HOUR_CHOICES.hour_0`` ... ``HOUR_CHOICES.hour_24``.
    """
    HOUR_CHOICES = Choices(*[
        (h, 'hour_{}'.format(h), '{:02d}:00'.format(h))
        for h in range(25)
    ])

    def __init__(self, *args, **kwargs):
        """
        The initial value of ``to_hour`` is 24:00 to include the entire
        duration of ``to_date``.
        """
        super(TimePeriodFormMixin, self).__init__(*args, **kwargs)
        self.initial['to_hour'] = self.HOUR_CHOICES.hour_24

    def clean(self):
        """
        Populates ``self.cleaned_data['from_timestamp']`` and
        ``self.cleaned_data['to_timestamp']`` with cleaned values of
        date and hour fields.
        """
        super(TimePeriodFormMixin, self).clean()
        assert 'from_timestamp' not in self.cleaned_data
        assert 'to_timestamp' not in self.cleaned_data
        if 'from_date' in self.cleaned_data and \
                'from_hour' in self.cleaned_data:
            self.cleaned_data['from_timestamp'] = _date_hour_to_datetime(
                self.cleaned_data['from_date'],
                self.cleaned_data['from_hour'],
                self._get_timezone())
        if 'to_date' in self.cleaned_data and \
                'to_hour' in self.cleaned_data and \
                self.cleaned_data['to_date']:
            self.cleaned_data['to_timestamp'] = _date_hour_to_datetime(
                self.cleaned_data['to_date'],
                self.cleaned_data['to_hour'],
                self._get_timezone())
        return self.cleaned_data

    def _get_timezone(self):
        return get_timezone()


class TimePeriodForm(TimePeriodFormMixin, forms.Form):
    """
    A Non-model form mixed with :class:`.TimePeriodFormMixin`.
    """
    from_date = forms.DateField(
        label=ugettext_lazy('From date'), localize=True)
    from_hour = forms.TypedChoiceField(
        label=ugettext_lazy('From hour'),
        choices=TimePeriodFormMixin.HOUR_CHOICES,
        coerce=int, empty_value=None)
    to_date = forms.DateField(
        label=ugettext_lazy('To date'), localize=True)
    to_hour = forms.TypedChoiceField(
        label=ugettext_lazy('To hour'),
        choices=TimePeriodFormMixin.HOUR_CHOICES,
        coerce=int, empty_value=None)


class TimePeriodModelForm(TimePeriodFormMixin, forms.ModelForm):
    """
    A model form mixed with :class:`.TimePeriodFormMixin`.

    A :class:`.TimePeriodModelForm` facilitates modifying a pair of
    :class:`~django.db.models.DateTimeField` on a model.  These should
    be named ``from_timestamp`` and ``to_timestamp`` by convention,
    but can be customized by the following class variables (not
    recommended):

    :cvar instance_from_attr: Defaults to ``'from_timestamp'``
    :cvar instance_to_attr: Defaults to ``'to_timestamp'``
    """
    from_date = forms.DateField(
        label=ugettext_lazy('From date'), localize=True)
    from_hour = forms.TypedChoiceField(
        label=ugettext_lazy('From hour'),
        choices=TimePeriodFormMixin.HOUR_CHOICES,
        coerce=int, empty_value=None)
    to_date = forms.DateField(
        label=ugettext_lazy('To date'), localize=True)
    to_hour = forms.TypedChoiceField(
        label=ugettext_lazy('To hour'),
        choices=TimePeriodFormMixin.HOUR_CHOICES,
        coerce=int, empty_value=None)

    instance_from_attr = 'from_timestamp'
    instance_to_attr = 'to_timestamp'

    def __init__(self, *args, **kwargs):
        """
        Initializes the :class:`.TimePeriodFormMixin` fields from
        ``self.instance``.

        :note: ``to_timestamp`` midnight is displayed as 24:00, to not
            mention dates that has an empty overlap with the period.
        """
        super(TimePeriodModelForm, self).__init__(*args, **kwargs)
        timezone = self._get_timezone()
        from_timestamp = getattr(self.instance, self.instance_from_attr, None)
        if from_timestamp:
            from_timestamp = timezone.normalize(
                from_timestamp.astimezone(timezone))
            self.initial['from_date'] = from_timestamp.date()
            self.initial['from_hour'] = from_timestamp.hour
        to_timestamp = getattr(self.instance, self.instance_to_attr, None)
        if to_timestamp:
            to_timestamp = timezone.normalize(
                to_timestamp.astimezone(timezone))
            if to_timestamp.hour == 0:
                # to_timestamp midnight is displayed as 24:00, to not
                # mention dates that has an empty overlap with the period.
                self.initial['to_date'] = to_timestamp.date() - \
                    datetime.timedelta(days=1)
                self.initial['to_hour'] = 24
            else:
                self.initial['to_date'] = to_timestamp.date()
                self.initial['to_hour'] = to_timestamp.hour

    def clean(self):
        """
        Sets ``instance`` fields from :class:`.TimePeriodFormMixin` fields
        """
        super(TimePeriodModelForm, self).clean()
        if 'from_timestamp' in self.cleaned_data:
            setattr(
                self.instance,
                self.instance_from_attr,
                self.cleaned_data['from_timestamp'])
        if 'to_timestamp' in self.cleaned_data:
            setattr(
                self.instance,
                self.instance_to_attr,
                self.cleaned_data['to_timestamp'])

        return self.cleaned_data


class HalfOpenTimePeriodModelForm(TimePeriodModelForm):
    """
    Specialization of :class:`.TimePeriodModelForm` that allows for
    empty ``to_date``.
    """
    to_date = forms.DateField(
        label=ugettext_lazy('To date'), localize=True, required=False)

    def clean(self):
        """
        Clears ``instance.to_timestamp`` if ``to_date`` is blank.
        """
        super(HalfOpenTimePeriodModelForm, self).clean()
        if 'to_timestamp' not in self.cleaned_data and \
                'to_date' not in self.errors and 'to_time' not in self.errors:
            setattr(self.instance, self.instance_to_attr, None)

        return self.cleaned_data


def previous_month_initial_values(timestamp=None):
    """
    Initial values for a form mixed with :class:`.TimePeriodFormMixin`
    covering the duration of a previous month.

    :rtype: :class:`dict`

    :keyword datetime timestamp: Result will be the latest completed
        month before this value.  If ``None`` (the default) now will
        be used instead.
    """
    if timestamp is None:
        timestamp = get_customer().now()
    initial = {
        'from_date': condense.floor(
            timestamp - RelativeTimeDelta(months=1),
            condense.MONTHS, get_timezone()).date(),
        'to_date': (
            condense.floor(
                timestamp,
                condense.MONTHS, get_timezone()) -
            RelativeTimeDelta(days=1)).date(),
        'from_hour': 0,
        'to_hour': 24
    }
    return initial


def this_week_initial_values(timestamp=None):
    """
    Initial values for a form mixed with :class:`.TimePeriodFormMixin`
    covering the duration of a week.

    :rtype: :class:`dict`

    :keyword datetime timestamp: Result will be the week containing
        this value.  If ``None`` (the default) now will be used
        instead.
    """
    if timestamp is None:
        timestamp = get_customer().now()
    week = Week.withdate(timestamp.date())
    initial = {
        'year': week.year,
        'week': week.week,
    }
    return initial


def _year_week_to_timestamps(year, week):
    week = Week.fromstring("%sW%02d" % (year, week))

    from_timestamp = datetime.datetime.combine(
        week.monday(), datetime.time())
    to_timestamp = from_timestamp + datetime.timedelta(days=7)
    return (from_timestamp, to_timestamp, )


class YearWeekPeriodForm(forms.Form):
    """
    Form for selecting a timestamp range with a duration of one week.

    :cvar year: A form field for selecting year of the week.
    :cvar week: A form field for selecting the week number of the week.
    """
    from_timestamp = None
    to_timestamp = None

    year = forms.TypedChoiceField(
        label=ugettext_lazy('Year'),
        choices=[],
        coerce=int, empty_value=2016)

    week = forms.TypedChoiceField(
        label=ugettext_lazy('Week'),
        choices=Choices(*[
            (w, w, w)
            for w in range(1, 54)
        ]),
        coerce=int, empty_value=1)

    def __init__(self, *args, **kwargs):
        """
        Initialize choices for ``self.year`` with 2005 ... next year.
        """
        super(YearWeekPeriodForm, self).__init__(*args, **kwargs)
        self.fields['year'].choices = Choices(*[
            (y, y, y)
            for y in range(
                2005, self._get_timezone().localize(
                    datetime.datetime.now()).year + 1)
        ])

    def clean(self):
        """
        :raise: ValidationError: If no such week number exist in given
            year.
        """
        super(YearWeekPeriodForm, self).clean()
        if 'year' in self.cleaned_data and \
                'week' in self.cleaned_data:
                    year = self.cleaned_data['year']
                    week = self.cleaned_data['week']
                    timestamps = _year_week_to_timestamps(
                        year, week)

                    if week == 53:
                        fourth_jan = datetime.date(year + 1, 1, 4)
                        if timestamps[1] >= datetime.datetime.combine(
                                fourth_jan, datetime.time()):
                            raise ValidationError(
                                _("There's no week %s in %s" % (week, year, )))

                    self.from_timestamp = self._get_timezone().localize(
                        timestamps[0])
                    self.to_timestamp = self._get_timezone().localize(
                        timestamps[1])

        return self.cleaned_data

    def get_timestamps(self):
        """
        After successful validation this method may be called.

        :return: The timestamp range of the selected week.
        :rtype: Pair of :class:`~datetime.datetime`.
        """
        return (self.from_timestamp, self.to_timestamp, )

    def _get_timezone(self):
        return get_timezone()
