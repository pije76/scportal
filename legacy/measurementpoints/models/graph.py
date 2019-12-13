# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import operator
import datetime

from django import template
from django.template.defaultfilters import floatformat
from django.utils.translation import ugettext_lazy as _
from django.db import models

from gridplatform.utils import unix_timestamp
from gridplatform.utils import condense
from gridplatform.utils.condense import get_date_formatter
from gridplatform.utils.utilitytypes import UTILITY_TYPE_TO_COLOR
from gridplatform.trackuser import get_customer
from gridplatform.trackuser.managers import CustomerBoundManager

from .collections import Collection
from ..fields import DataRoleField


class AbstractGraph(object):
    """
    A C{Graph} visualizes a set of C{DataSeries}.

    Non-abstract subclasses are required to implement L{_get_data_series()}, to
    define which DataSeries to visualize.
    """

    BAR_GRAPH = 0
    PIECEWISE_CONSTANT_GRAPH = 1
    LINEAR_INTERPOLATION_GRAPH = 2

    PROGRESS_TOTAL = 20

    def _get_data_series(self):
        """
        Get the L{DataSeries} visualized in this C{Graph}.

        @return: An iterable of L{DataSeries} subclass instances.
        """
        raise NotImplementedError(
            'Method not implemented for %r.' % self.__class__)

    def _get_float_format_decimals(self):
        """
        Specifies string argument given to the Django template filter
        C{floatformat}, inside this instance.  The intend is to allow for
        subclasses to decide how many decimals are relevant for them, because
        they have a change to know better.
        """
        return '-3'

    def _get_caption_text(self, data_samples, converter, is_rate,
                          is_condensed, avg_value=None):
        """
        Renders caption text. Intended use is inclusion in JSON responses
        with L{get_graph_data()}.

        @param data_samples: List of data samples.

        @param converter: A L{UnitConverter} for converting
        C{sample.physical_quantity} for each sample in C{data_samples}.

        @param is_rate: True if data_samples are to be interpreted as a rate
                        for this graph; False, if data_samples are to
                        be interpreted as accumulation.

        @param is_condensed: True of false whether or not the samples
        are condensed. If samples are condensed, the average text will not be
        applied to the caption text.
        """
        if is_rate or avg_value is not None:
            min_value = None
            max_value = None
            total_value = None

            for sample in data_samples:
                if total_value is None:
                    total_value = sample.physical_quantity
                else:
                    total_value += sample.physical_quantity

                if min_value is None or sample.physical_quantity < min_value:
                    min_value = sample.physical_quantity

                if max_value is None or sample.physical_quantity > max_value:
                    max_value = sample.physical_quantity

            if avg_value is None and data_samples and total_value is not None:
                avg_value = total_value / len(data_samples)

            if min_value is not None and max_value is not None \
                    and avg_value is not None:
                if is_condensed:
                    caption = _('Min: {{ min_value }} {{ unit }} | '
                                'Max: {{ max_value }} {{ unit }}')
                    subcontext = template.Context({
                        'min_value': converter.extract_value(min_value),
                        'max_value': converter.extract_value(max_value),
                        'unit': converter.get_display_unit()})
                else:
                    caption = _('Avg: {{ avg_value }} {{ unit }} | '
                                'Min: {{ min_value }} {{ unit }} | '
                                'Max: {{ max_value }} {{ unit }}')
                    subcontext = template.Context({
                        'avg_value': converter.extract_value(avg_value),
                        'min_value': converter.extract_value(min_value),
                        'max_value': converter.extract_value(max_value),
                        'unit': converter.get_display_unit()})
            else:
                subcontext = template.Context({})
                caption = _('No values in this range.')
        else:
            if data_samples:
                total = converter.extract_value(
                    reduce(
                        operator.add,
                        (sample.physical_quantity for sample in data_samples)))
                caption = _('Total: {{ total }} {{ unit }}')
            else:
                caption = _('No values in this range.')
                total = None
            subcontext = template.Context({
                'total': total,
                'unit': converter.get_display_unit()})

        # Find out if samples are extrapolated and add a notice
        # to caption string about this.
        if data_samples:
            if all(not s.extrapolated for s in data_samples[0:-1]) and \
                    data_samples[-1].extrapolated:
                warning = _('Rightmost sample is incomplete')
                caption = _('{caption} ({warning})').format(caption=caption,
                                                            warning=warning)
            elif (data_samples[0].extrapolated or
                    data_samples[-1].extrapolated):
                warning = _('Graph is based on incomplete data')
                caption = _('{caption} ({warning})').format(caption=caption,
                                                            warning=warning)

        # NOTE: including use of floatformat filter inside caption might be a
        # better approach...
        for elem in ['avg_value', 'min_value', 'max_value', 'total']:
            if elem in subcontext:
                subcontext[elem] = floatformat(
                    subcontext[elem], self._get_float_format_decimals())
        return template.Template(unicode(caption)).render(subcontext)

    def get_graph_data(self, num_ticks, from_timestamp,
                       num_samples=None, sample_resolution=None,
                       data_series_set=None, to_timestamp=None,
                       weekends_are_special=True):
        """
        Returns a dictionary, suitable for rendering by Javascript
        flotr2.  The dictionary will be on the form::

            {"data": data, "options": options}

        where C{data} corresponds to the C{data} argument to
        C{Flotr.draw(container, data, options)} in flotr2, and
        C{options} correspond to the C{options} argument.

        @param num_ticks: The number of ticks (labels) to be shown.
        This must be an integer

        @param from_timestamp: The earliest time used in the returned
        data.

        @param num_samples: The number of sample points in the
        returned data.  There will be data for each L{DataSeries} at
        each sample point.

        @param sample_resolution: The symbolic timespan.  If not given, raw
        data will be used.  In that case to_timestamp must be set, and
        num_samples will be ignored.  This is only supported for non-bar
        graphs.

        @param to_timestamp: Only used when C{sample_resolution is None}, in
        which case it must be set.

        @keyword weekends_are_special: If C{True}, samples contained within
        weekends are colored specially.  Default is C{True}.
        """
        assert from_timestamp.tzinfo is not None, \
            'timezone-aware from_timestamp required'
        assert isinstance(num_ticks, int)
        if sample_resolution:
            from_timestamp = condense.floor(
                from_timestamp, sample_resolution, from_timestamp.tzinfo)
            to_timestamp = from_timestamp + (num_samples * sample_resolution)

            assert num_samples >= num_ticks
            ticks_range = [
                # RelativeTimeDelta does not support division, so we need to do
                # the operations so that division is done on datetime.timedelta
                # objects instead.
                from_timestamp + sample_resolution * x +
                ((from_timestamp + sample_resolution * (x + 1))
                 - (from_timestamp + sample_resolution * x)) / 2 for
                x in range(num_samples)
                if x % (num_samples / num_ticks) == 0 and
                x < num_samples - (num_samples % num_ticks)]
            assert len(ticks_range) == num_ticks
        else:
            assert to_timestamp, \
                "to_timestamp required when sample_resolution is None"
            ticks_range = [
                from_timestamp + i * (to_timestamp - from_timestamp) /
                num_ticks for i in range(num_ticks)]

        if not data_series_set:
            data_series_set = list(self._get_data_series())

        total_seconds = (to_timestamp - from_timestamp).total_seconds()
        self.__progress = 0
        self.__tick_progress()

        self.__when_to_report_progress_next = (
            self.__progress / float(self.PROGRESS_TOTAL)) * \
            len(data_series_set) * total_seconds

        all_data_samples = []

        data = []
        # @bug: get rid of this variable it is never set anyway.
        track_labels = {}

        formatter = get_date_formatter(
            from_timestamp, to_timestamp, resolution=sample_resolution)
        ticks = [(unix_timestamp(t), formatter(t)) for
                 t in ticks_range]
        caption = ''

        # reasonable y-axis scale for data series that sample y(x)=0
        maximum = 0.01
        minimum = -0.001

        tz = from_timestamp.tzinfo

        def point_label(value, timestamp):
            if value is not None:
                ts = tz.normalize(timestamp.astimezone(tz))
                return (floatformat(value, 3),
                        ts.strftime('%Y-%m-%d'),
                        ts.strftime('%H:%M:%S'))

        def range_label(value, from_timestamp, to_timestamp):
            if value is not None:
                from_ts = tz.normalize(from_timestamp.astimezone(tz))
                to_ts = tz.normalize(to_timestamp.astimezone(tz))
                days = int((to_ts - from_ts).total_seconds() /
                           datetime.timedelta(days=1).total_seconds())
                date = from_ts.strftime('%Y-%m-%d')
                time_range = '%s - %s' % (from_ts.strftime('%H:%M'),
                                          to_ts.strftime('%H:%M'))

                if days >= 1:
                    time_range = ''
                if days > 27:
                    date = ''
                    time_range = '%s - %s' % (from_ts.strftime('%Y-%m-%d'),
                                              to_ts.strftime('%Y-%m-%d'))

                return (floatformat(value, 3),
                        date,
                        time_range)

        def report_progress(sample):
            progress_seconds = ds_no * total_seconds + (
                sample.from_timestamp - from_timestamp).total_seconds()
            if progress_seconds > self.__when_to_report_progress_next:
                self.__tick_progress()
                self.__when_to_report_progress_next = (
                    self.__progress / float(self.PROGRESS_TOTAL)) * \
                    len(data_series_set) * total_seconds

        from .dataseries import UndefinedSamples
        from .dataseries import DataSeries
        for ds_no, data_series in enumerate(data_series_set):
            preferred_unit_converter = \
                data_series.get_preferred_unit_converter()
            current_data = []
            current_weekend_data = []

            try:
                data_samples = []
                if sample_resolution:
                    for s in data_series.get_condensed_samples(
                            from_timestamp, sample_resolution,
                            to_timestamp=to_timestamp):
                        report_progress(s)
                        data_samples.append(s)

                else:
                    for s in data_series.get_samples(
                            from_timestamp, to_timestamp):
                        report_progress(s)
                        data_samples.append(s)

                all_data_samples.extend(data_samples)

                if data_series.get_underlying_function() == \
                        DataSeries.CONTINUOUS_RATE:
                    for sample in data_samples:
                        converted_value = float(
                            preferred_unit_converter.extract_value(
                                sample.physical_quantity))
                        current_data.append([unix_timestamp(sample.timestamp),
                                             converted_value,
                                             point_label(converted_value,
                                                         sample.timestamp)])
                        if converted_value is not None:
                            maximum = max(maximum, converted_value)
                            minimum = min(minimum, converted_value)

                    graph_data = {
                        "data": current_data,
                        "trackLabels": track_labels,
                        "lines": {
                            "show": True,
                        }
                    }
                    data.append(graph_data)

                else:
                    for data_sample in data_samples:
                        converted_value = float(
                            preferred_unit_converter.extract_value(
                                data_sample.physical_quantity))
                        if data_series.get_underlying_function() == \
                                DataSeries.PIECEWISE_CONSTANT_RATE:
                            current_data.extend(
                                [[unix_timestamp(data_sample.from_timestamp),
                                  converted_value,
                                  range_label(converted_value,
                                              data_sample.from_timestamp,
                                              data_sample.to_timestamp)],
                                 [unix_timestamp(data_sample.to_timestamp),
                                  converted_value,
                                  range_label(converted_value,
                                              data_sample.from_timestamp,
                                              data_sample.to_timestamp)]])

                        else:
                            assert data_series.get_underlying_function() in (
                                DataSeries.CONTINUOUS_ACCUMULATION,
                                DataSeries.PIECEWISE_CONSTANT_ACCUMULATION,
                                DataSeries.INTERVAL_FUNCTION)
                            data_tuple = [
                                # put the sample at center.
                                unix_timestamp(
                                    data_sample.from_timestamp +
                                    (
                                        data_sample.to_timestamp -
                                        data_sample.from_timestamp) / 2),
                                converted_value,
                                # don't give label data for extrapolated values
                                # that almost equal 0.  These represent "No
                                # data"
                                range_label(converted_value,
                                            data_sample.from_timestamp,
                                            data_sample.to_timestamp) if
                                float("%.7f" % converted_value) or
                                not data_sample.extrapolated else None]

                            if weekends_are_special and \
                                    data_sample.from_timestamp.astimezone(
                                        get_customer().timezone
                                    ).weekday() in [5, 6] \
                                    and (sample_resolution.days == 1
                                         or sample_resolution.hours == 1):
                                # bars contained in weekend.
                                current_weekend_data.append(data_tuple)
                            else:
                                current_data.append(data_tuple)

                        if converted_value is not None:
                            maximum = max(maximum, converted_value)
                            minimum = min(minimum, converted_value)

                    if data_series.get_underlying_function() == \
                            DataSeries.PIECEWISE_CONSTANT_RATE:
                        graph_data = {
                            "data": current_data,
                            "trackLabels": track_labels,
                            "lines": {
                                "show": True,
                            }
                        }
                    else:
                        graph_data = {
                            "data": current_data,
                            "trackLabels": track_labels,
                            "bars": {
                                "show": True,
                                "barWidth": 0.8 *
                                (
                                    to_timestamp -
                                    from_timestamp).total_seconds() /
                                num_samples,
                                'centered': True,
                            }
                        }

                    data.append(graph_data)

                    if len(current_weekend_data) > 0:
                        graph_weekend_data = {
                            "data": current_weekend_data,
                            "trackLabels": track_labels,
                            "bars": {
                                "show": True,
                                "barWidth": 0.8 *
                                (
                                    to_timestamp -
                                    from_timestamp).total_seconds() /
                                num_samples,
                                'centered': True,
                            }
                        }
                        data.append(graph_weekend_data)

            except UndefinedSamples, e:
                caption = unicode(e)

        if hasattr(data_series, 'calculate_enpi'):
            enpi_sample = data_series.calculate_enpi(
                from_timestamp, to_timestamp)
            extrapolated = any(s.extrapolated for s in all_data_samples)
            if enpi_sample is not None and not extrapolated:
                caption = _('Avg: {average} {unit}.').format(
                    average=floatformat(
                        preferred_unit_converter.extract_value(
                            enpi_sample.physical_quantity),
                        self._get_float_format_decimals()),
                    unit=preferred_unit_converter.get_display_unit())
            elif enpi_sample is not None and extrapolated:
                caption = _(
                    'Avg: {average} {unit} (Graph is based on '
                    'incomplete data).').format(
                    average=floatformat(
                        preferred_unit_converter.extract_value(
                            enpi_sample.physical_quantity),
                        self._get_float_format_decimals()),
                    unit=preferred_unit_converter.get_display_unit())
            else:
                caption = _('No values in this range.')
        else:
            caption = self._get_caption_text(
                all_data_samples,
                preferred_unit_converter,
                data_series.is_rate(),
                sample_resolution)

        MAXIMUM_FACTOR = 1.2

        result = {
            "data": data,
            "options": {
                "colors": self.get_colors(),
                "xaxis": {
                    "ticks": ticks,
                    "min": unix_timestamp(from_timestamp),
                    "max": unix_timestamp(to_timestamp),
                    'title': unicode(caption),
                },
                "yaxis": {
                    "title": unicode(
                        preferred_unit_converter.get_display_unit()),
                    "min": float(minimum) * MAXIMUM_FACTOR,
                    "max": float(maximum) * MAXIMUM_FACTOR,
                }
            }
        }

        # tick remaining progress
        while self.__progress < self.PROGRESS_TOTAL:
            self.__tick_progress()

        return result

    def tick_progress(self):
        """
        Hook for subclasses to implement progress reporting.

        Will be called exactly C{PROGRESS_TOTAL} times during each call to
        L{get_graph_data()}
        """
        pass

    def __tick_progress(self):
        """
        Wrapper for L{tick_progress()}, ensuring pre- and postconditions.
        """
        assert 0 <= self.__progress
        self.__progress += 1
        assert self.__progress <= self.PROGRESS_TOTAL, \
            '%s <= %s' % (self.__progress, self.PROGRESS_TOTAL)
        self.tick_progress()

    def get_colors(self):
        """
        @return List of HTML RGB colors to cycle through when plotting graph.
        """
        return ['#00A8F0', '#999999', '#CB4B4B', '#4DA74D', '#9440ED']


class CollectionCustomerBoundManager(CustomerBoundManager):
    _field = 'collection__customer'


class Graph(models.Model, AbstractGraph):
    """
    A graph displays the data series of one or more L{DataSeries}s for a
    given time span.
    """

    role = DataRoleField()

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    hidden = models.BooleanField(default=False)

    objects = CollectionCustomerBoundManager()

    class Meta:
        verbose_name = _('graph')
        verbose_name_plural = _('graphs')
        ordering = ['role', 'id']
        unique_together = ('collection', 'role')
        app_label = 'measurementpoints'

    def __unicode__(self):
        return self.get_role_display()

    def _get_data_series(self):
        """
        Get the L{DataSeries} associated with this graph.
        """
        return [ds.subclass_instance for ds in self.dataseries_set.all()]

    def _get_float_format_decimals(self):
        if self.role == DataRoleField.COST:
            return '-2'
        else:
            return super(Graph, self)._get_float_format_decimals()

    def get_colors(self):
        if self.role in [DataRoleField.CONSUMPTION, DataRoleField.POWER,
                         DataRoleField.VOLUME_FLOW]:
            return [
                UTILITY_TYPE_TO_COLOR[self.collection.utility_type],
                '#999999']
        elif self.role == DataRoleField.CO2:
            return ['#444444', '#999999']
        else:
            return super(Graph, self).get_colors()
