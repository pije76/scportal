# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from datetime import datetime
from datetime import time
from datetime import timedelta

from collections import namedtuple
from operator import attrgetter
from django.shortcuts import get_object_or_404
from django.utils.formats import get_format
from django.utils.translation import ugettext_lazy as _

from gridplatform.reports.pdf import generate_pdf
from gridplatform.reports.templatetags.reports import texescape
from gridplatform.reports.views import FinalizeReportView
from gridplatform.reports.views import ReportInfo
from gridplatform.reports.views import StartReportView
from gridplatform.utils import condense
from gridplatform.trackuser import get_customer

from .models import EnergyUseReport
from .forms import GenerateEnergyUseReportForm
from .tasks import EnergyUseGraph
from .tasks import EnergyUseReportTask


def flotr2_to_gnuplot(graph_data, output_name,
                      # 17.465246375cm appears to be the \the\textwidth
                      terminal='epslatex color solid size 17.465246375cm,6cm',
                      sample_resolution=None):
    """
    Translate a flotr2 dictionary to the corresponding gnuplot script.

    @param graph_data: The flotr2 dictionary; say output from
    L{Graph.get_graph_data()}.

    @param output_name: The name of the plot file generated when running the
    returned gnuplot script.  If the terminal parameter is not changed, this
    will usually need to end in C{.tex}.

    @param terminal: The C{set terminal} argument to gnuplot.  The default
    creates a LaTeX file accompanied with an EPS file in colors and something
    close to text width.

    @return: A GNU plot script that can generate a gnu plot file named
    C{output_name}.
    """
    result = u'set output "%s"\n' % output_name
    result += u'set terminal %s\n' % terminal

    if sample_resolution:
        # Note that clustered histograms assume that the x-axis is just labels,
        # and not numeric.  We use a trick inspired from
        # http://gnuplot-surprising.blogspot.dk/2011/09/
        # plot-histograms-using-boxes.html to do a normal plotting with boxes,
        # but where the boxes are shifted to place them in clusters centered
        # above their numeric x value.
        if sample_resolution == condense.MINUTES:
            resolution = 60
        elif sample_resolution == condense.FIVE_MINUTES:
            resolution = 5 * 60
        elif sample_resolution == condense.HOURS:
            resolution = 60 * 60
        elif sample_resolution == condense.DAYS:
            resolution = 60 * 60 * 24
        elif sample_resolution == condense.MONTHS:
            resolution = 60 * 60 * 24 * 31
        elif sample_resolution == condense.QUARTERS:
            resolution = 60 * 60 * 24 * 365 / 4
        else:
            assert sample_resolution == condense.YEARS
            resolution = 60 * 60 * 24 * 365

        bar_datasets = [dataset for dataset in graph_data['data'] if
                        'bars' in dataset]

        gap = 1 if len(bar_datasets) > 1 else 0  # only set for clusters
        boxwidth = resolution / (len(bar_datasets) + gap)
        cluster_width = boxwidth * len(bar_datasets)

        result += u'set boxwidth %d\n' % boxwidth

    yaxistitle = graph_data['options']['yaxis']['title']
    xaxistitle = graph_data['options']['xaxis']['title']

    def replace_production_unit(s, l):
        return s.replace(
            'production_%s' % l, getattr(
                get_customer(), 'production_%s_unit_plain' % l))
    for letter in ['a', 'b', 'c', 'd', 'e']:
        xaxistitle = replace_production_unit(xaxistitle, letter)
        yaxistitle = replace_production_unit(yaxistitle, letter)

    result += u'unset key\n'
    result += u'set key below\n'
    result += u'set border 3\n'  # bottom(1) + left(2)

    # Hack/workaround: If at least one dataset included has "much" data, don't
    # draw borders on bar graphs.  Having the threshold at 200 elements
    # appeared to work OK for whatever border width we implicitly have now;
    # might look completely wrong otherwise...  For plots displaying multiple
    # datasets, adjusting the appearance of *all* bar charts based on the
    # number if elements in whatever dataset has the most elements (which might
    # not even be/be used as a bar chart) may be problematic --- but "set
    # style" appears to be "global" per plot in gnuplot; if we want multiple
    # datasets in the same output figure, they are forced to use the same
    # style...
    if any([len(dataset['data']) > 200 for dataset in graph_data['data'] if
            dataset['data']]):
        result += u'set style fill solid noborder\n'
    else:
        result += u'set style fill solid border -1\n'
    result += u'set ylabel "%s"\n' % texescape(yaxistitle).replace(
        '\\', '\\\\').replace('"', '\\"')
    result += u'set xlabel "%s"\n' % texescape(xaxistitle).replace(
        '\\', '\\\\').replace('"', '\\"')
    result += u'set xtic nomirror\n'
    result += u'set ytic nomirror\n'
    result += u'set xtics out\n'
    result += u'set xtic (%s)\n' % (
        ', '.join(map(lambda x: u'"{1}" {0}'.format(*x),
                      graph_data['options']['xaxis']['ticks'])))

    if graph_data['options']['colors']:
        for i, color in enumerate(graph_data['options']['colors'], start=1):
            result += u'set linetype %d lc rgb "%s" lw 1\n' % (i, color)
        result += u'set linetype cycle %d\n' % len(
            graph_data['options']['colors'])

    def plot_dataset(dataset, index):
        """
        Returns plot arguments to plot a given C{dataset} with the given
        C{index}.
        """
        if 'lines' in dataset and dataset['lines']['show']:
            return u'"-" using 1:2 title "%s" with lines' % (
                dataset.get('label', ''))
        elif 'bars' in dataset and dataset['bars']['show']:
            assert sample_resolution is not None
            return u'"-" using ($1+%f):2 title "%s" with boxes' % (
                index * boxwidth - (cluster_width - boxwidth) / 2.0,
                dataset.get('label', ''))
        else:
            assert False

    if any(dataset['data'] for dataset in graph_data['data']):
        # the plot command require at least one argument, and each argument
        # requires some data.
        result += (
            u'plot ' + (
                u', '.join(
                    [
                        plot_dataset(dataset, i) for
                        i, dataset in enumerate(
                            dataset_ for dataset_ in graph_data['data'] if
                            dataset_)
                        if dataset['data']])) +
                u'\n')

        for dataset in graph_data['data']:
            if dataset['data']:
                for sample in dataset['data']:
                    result += u'%f %f\n' % (float(sample[0]), float(sample[1]))

                # e means end of graph data.
                result += u'e\n'

    # flushes write buffer
    result += u'set output'
    return result


class ErrorCollector(object):
    """
    Collects errors for a specific subjects of distribution.
    """
    def __init__(self, errors):
        self.errors = errors
        self.show_pie_chart = True
        self.show = True

    def area_negative(self, area):
        """
        Tell the C{ErrorCollector} that an area of energy use is negative for
        the particular subject of distribution.

        This will prevent the associated pie chart from being displayed.
        """
        self.show_pie_chart = False

    def accounted_gt_total(self):
        """
        Tell the C{ErrorCollector} that we have accounted for a larger quantity
        than the total of this particular subject of distribution.

        This will prevent the associated pie chart from being displayed.
        """

        self.show_pie_chart = False

    def total_negative(self):
        """
        Tell the C{ErrorCollector} that the total of this particular subject of
        distribution is negative.

        This will prevent the associated pie chart from being displayed, as
        well as the entire section about to this subject of distribution.
        """
        self.show_pie_chart = False
        self.show = False


class ConsumptionErrorCollector(ErrorCollector):
    """
    Collects errors for distribution of consumption.
    """
    def area_negative(self, area):
        super(ConsumptionErrorCollector, self).area_negative(area)
        self.errors.append(
            _('Consumption is negative for the area of energy use '
              '{energy_use_area}.  This prevents the '
              'consumption pie chart from being displayed.').
            format(energy_use_area=area))

    def accounted_gt_total(self):
        super(ConsumptionErrorCollector, self).accounted_gt_total()
        self.errors.append(
            _('Total consumption for main measurement points is less than '
              'the total consumption of the areas of energy use in '
              'current period.   No pie chart for consumption will be shown'))

    def total_negative(self):
        super(ConsumptionErrorCollector, self).total_negative()
        self.errors.append(
            _('Total consumption is negative. Energy use by consumption is '
              'excluded from the report'))


class CostErrorCollector(ErrorCollector):
    """
    Collects errors for distribution of costs.
    """

    def area_negative(self, area):
        super(CostErrorCollector, self).area_negative(area)
        self.errors.append(
            _('Costs are negative for the area of energy use '
              '{energy_use_area}.  This prevents the '
              'costs pie chart from being displayed.').
            format(energy_use_area=area))

    def accounted_gt_total(self):
        super(CostErrorCollector, self).accounted_gt_total()
        self.errors.append(
            _('Total costs for main measurement points are less than '
              'the total costs of the areas of energy use in current '
              'period.  No pie chart for costs will be shown.'))

    def total_negative(self):
        super(CostErrorCollector, self).total_negative()
        self.errors.append(
            _('Total costs are negative. Energy use by cost is '
              'excluded from the report'))


class Co2ErrorCollector(ErrorCollector):
    """
    Collects errors for distribution of CO2 emissions.
    """

    def area_negative(self, area):
        super(Co2ErrorCollector, self).area_negative(area)
        self.errors.append(
            _(u'CO₂ emissions are negative for the area of energy use '
              u'{energy_use_area}.  This prevents the '
              u'CO₂ emissions pie chart from being displayed.').
            format(energy_use_area=area))

    def accounted_gt_total(self):
        super(Co2ErrorCollector, self).accounted_gt_total()
        self.errors.append(
            _(u'Total CO₂ emissions for main measurement points are less '
              u'than the total  CO₂ emissions of the areas of energy use '
              u'in current period.  No pie chart for CO₂ emissions will '
              u'be shown.'))

    def total_negative(self):
        super(Co2ErrorCollector, self).total_negative()
        self.errors.append(
            _(u'Total CO₂ emissions are negative. Energy use by CO₂ emissions '
              u'is excluded from the report'))


EnergyUseAreaTuple = namedtuple(
    'EnergyUseAreaTuple',
    'name, previous_value, value, percent, change_percent, has_errors,')
ColoredEnergyUseAreaTuple = namedtuple(
    'ColoredEnergyUseAreaTuple',
    'name, previous_value, value, percent, change_percent, has_errors, color')


def change_percent(current, previous):
    if previous:
        return (current - previous) * 100.0 / previous
    else:
        return ''


class FinalizeEnergyUseReportView(FinalizeReportView):
    COLOR_SEQUENCE = (
        '3366A4',
        'A83734',
        '83A440',
        '684C8B',
        '3093AE',
        'EB9659',
        '9CBEFD',
        'FD9A99',
        'D4F89F',
        'C2ADE2',
        '96E5FD',
        'FFB579',
        'A9C8FC',
        'FCA7A6',
        'DEFCAD',
        'CFBBED',
        '8BD8ED',
        'FFA868',
        'B2C4E4',
        'E5B2B1',
        'D0E3B4',
        'C5BAD6',
    )

    def generate_report(self, data, timestamp):
        """
        Implementation of L{FinalizeReportView.generate_report}.

        @param data: Output from L{EnergyUseReportTask} Celery task.

        @param timestamp: The time the report is being build.
        """
        energy_use_report = get_object_or_404(
            EnergyUseReport, id=data['energy_use_report'])
        areas = list(energy_use_report.energyusearea_set.all())

        # Creates function suitable for reduce()
        def create_accounter(name, error_collector):
            # Collects accounted consumptions, costs, emissions,...
            def accounter(value_pair, area):
                total_accounted_value, total_accounted_previous_value = \
                    value_pair
                value = data['data'][area.id][name]
                total_accounted_value += value
                total_accounted_previous_value += data['data'][area.id][
                    'previous_%s' % name]
                if data['data'][area.id][name] < 0:
                    error_collector.area_negative(area)
                return total_accounted_value, total_accounted_previous_value
            return accounter

        def create_tuple_converter(name, total):
            def converter(area):
                return EnergyUseAreaTuple(
                    name=area.name_plain,
                    previous_value=data['data'][area.id][
                        'previous_%s' % name],
                    value=data['data'][area.id][name],
                    percent=data['data'][area.id][
                        name] * 100.0 / total,
                    change_percent=change_percent(
                        current=data['data'][area.id][name],
                        previous=data['data'][area.id][
                            'previous_%s' % name]),
                    has_errors=next((True for x in data['errors'] if
                                     getattr(x, 'energy_use_area_id', None) ==
                                     area.id), False))
            return converter

        has_main_measurement_points = \
            energy_use_report.main_measurement_points.exists()

        consumption_error_collector = ConsumptionErrorCollector(data['errors'])
        total_accounted_consumption, total_accounted_previous_consumption = \
            reduce(create_accounter('consumption',
                                    consumption_error_collector), areas,
                   (0, 0))
        if has_main_measurement_points:
            total_consumption = data['total_consumption']
            total_previous_consumption = data['total_previous_consumption']
        else:
            total_consumption = total_accounted_consumption
            total_previous_consumption = total_accounted_previous_consumption
        if total_accounted_consumption > total_consumption:
            consumption_error_collector.accounted_gt_total()
        if total_consumption <= 0:
            consumption_error_collector.total_negative()
        unaccounted_consumption = \
            total_consumption - total_accounted_consumption
        unaccounted_previous_consumption = \
            total_previous_consumption - total_accounted_previous_consumption

        if total_consumption > 0:
            consumptions = map(
                create_tuple_converter('consumption', total_consumption),
                areas)
            consumptions.append(
                EnergyUseAreaTuple(
                    _('Unaccounted Consumption'),
                    unaccounted_previous_consumption,
                    unaccounted_consumption,
                    unaccounted_consumption * 100.0 / total_consumption,
                    change_percent=change_percent(
                        unaccounted_consumption,
                        unaccounted_previous_consumption),
                    has_errors=next((True for x in data['errors'] if
                                     getattr(x, 'energy_use_area_id', None) is
                                     None), False)))
            consumptions.sort(key=attrgetter('value'), reverse=True)
        else:
            consumption_error_collector.total_negative()
            consumptions = []
        colored_consumptions = [
            ColoredEnergyUseAreaTuple._make(t + ('FFFFFF', )) if
            t.name == _('Unaccounted Consumption') else
            ColoredEnergyUseAreaTuple._make(t + (c, )) for t, c in zip(
                consumptions, self.COLOR_SEQUENCE)]

        if data['include_cost']:
            cost_error_collector = CostErrorCollector(data['errors'])
            total_accounted_cost, total_accounted_previous_cost = reduce(
                create_accounter('cost', cost_error_collector),
                areas, (0, 0))
            if has_main_measurement_points:
                total_cost = data['total_cost']
                total_previous_cost = data['total_previous_cost']
            else:
                total_cost = total_accounted_cost
                total_previous_cost = total_accounted_previous_cost
            unaccounted_cost = total_cost - total_accounted_cost
            unaccounted_previous_cost = \
                total_previous_cost - total_accounted_previous_cost
            if total_accounted_cost > total_cost:
                cost_error_collector.accounted_gt_total()
            if total_cost <= 0:
                cost_error_collector.total_negative()
                colored_costs = []
            else:
                costs = map(create_tuple_converter('cost', total_cost), areas)
                costs.append(
                    EnergyUseAreaTuple(
                        _('Unaccounted Cost'),
                        unaccounted_previous_cost,
                        unaccounted_cost,
                        unaccounted_cost * 100.0 / total_cost,
                        change_percent=change_percent(
                            unaccounted_cost,
                            unaccounted_previous_cost),
                        has_errors=next(
                            (True for x in data['errors'] if
                             getattr(x, 'energy_use_area_id', None) is
                             None), False)))
                costs.sort(key=attrgetter('value'), reverse=True)
                colored_costs = [
                    ColoredEnergyUseAreaTuple._make(t + ('FFFFFF', )) if
                    t.name == _('Unaccounted Cost') else
                    ColoredEnergyUseAreaTuple._make(t + (c, )) for t, c in zip(
                        costs, self.COLOR_SEQUENCE)]

        if data['include_co2']:
            co2_error_collector = Co2ErrorCollector(data['errors'])
            total_accounted_co2, total_accounted_previous_co2 = reduce(
                create_accounter('co2', co2_error_collector),
                areas, (0, 0))
            if has_main_measurement_points:
                total_co2 = data['total_co2']
                total_previous_co2 = data['total_previous_co2']
            else:
                total_co2 = total_accounted_co2
                total_previous_co2 = total_accounted_previous_co2
            unaccounted_co2 = total_co2 - total_accounted_co2
            unaccounted_previous_co2 = total_previous_co2 - \
                total_accounted_previous_co2
            if total_accounted_co2 > total_co2:
                co2_error_collector.accounted_gt_total()
            if total_co2 <= 0:
                co2_error_collector.total_negative()
                colored_co2 = []
            else:
                co2 = map(create_tuple_converter('co2', total_co2), areas)
                co2.append(
                    EnergyUseAreaTuple(
                        _(u'Unaccounted CO₂ Emissions'),
                        unaccounted_previous_co2,
                        unaccounted_co2,
                        unaccounted_co2 * 100.0 / total_co2,
                        change_percent=change_percent(
                            unaccounted_co2,
                            unaccounted_previous_co2),
                        has_errors=next(
                            (True for x in data['errors'] if
                             getattr(x, 'energy_use_area_id', None) is
                             None), False)))
                co2.sort(key=attrgetter('value'), reverse=True)
                colored_co2 = [
                    ColoredEnergyUseAreaTuple._make(t + ('FFFFFF', )) if
                    t.name == _(u'Unaccounted CO₂ Emissions') else
                    ColoredEnergyUseAreaTuple._make(t + (c, )) for t, c in zip(
                        co2, self.COLOR_SEQUENCE)]

        from_timestamp = energy_use_report.customer.timezone.localize(
            datetime.combine(data['from_date'], time(0, 0)))
        to_timestamp = energy_use_report.customer.timezone.localize(
            datetime.combine(data['to_date'] + timedelta(days=1), time(0, 0)))
        sample_resolution = EnergyUseGraph.get_sample_resolution(
            from_timestamp, to_timestamp)

        generate_pdf_data = {
            'show_consumption_pie_chart': (
                consumption_error_collector.show_pie_chart),
            'colored_consumptions': colored_consumptions,
            'total_consumption': total_consumption,
            'total_consumption_change_percent': change_percent(
                total_consumption, total_previous_consumption),
            'total_previous_consumption': total_previous_consumption,
            'energy_use_report': energy_use_report,
            'from_date': data['from_date'],
            'to_date': data['to_date'],
            'previous_from_date': data['previous_from_date'],
            'previous_to_date': data['previous_to_date'],
            'errors': data['errors'],
            'graph_data': data['graph_data'],
            'DECIMAL_SEPARATOR': get_format('DECIMAL_SEPARATOR'),
            'THOUSAND_SEPARATOR': get_format('THOUSAND_SEPARATOR'),
            'include_co2': data['include_co2'],
        }

        if data['include_cost']:
            generate_pdf_data['show_cost_pie_chart'] = \
                cost_error_collector.show_pie_chart,
            generate_pdf_data['colored_costs'] = colored_costs
            generate_pdf_data['total_cost'] = total_cost
            generate_pdf_data['total_cost_change_percent'] = \
                change_percent(total_cost, total_previous_cost)
            generate_pdf_data['total_previous_cost'] = total_previous_cost

        if data['include_co2']:
            generate_pdf_data['show_co2_pie_chart'] = \
                co2_error_collector.show_pie_chart
            generate_pdf_data['colored_co2'] = colored_co2
            generate_pdf_data['total_co2'] = total_co2
            generate_pdf_data['total_co2_change_percent'] = \
                change_percent(total_co2, total_previous_co2)
            generate_pdf_data['total_previous_co2'] = total_previous_co2

        gnuplots = [
            flotr2_to_gnuplot(
                data['graph_data'], 'consumption.tex',
                sample_resolution=sample_resolution)]

        if data['include_co2']:
            gnuplots.append(
                flotr2_to_gnuplot(
                    data['co2_graph_data'],
                    'co2-emission.tex',
                    sample_resolution=sample_resolution))

        return ReportInfo(
            '{}.pdf'.format(
                energy_use_report.title_plain.encode('ascii', 'ignore')),
            'application/pdf',
            generate_pdf(
                template='energy_use_reports/report.tex',
                data=generate_pdf_data,
                title=energy_use_report.get_utility_type_report_name(),
                report_type='energy_use_report',
                customer=energy_use_report.customer,
                gnuplots=gnuplots))


class StartEnergyUseReportView(StartReportView):
    form_class = GenerateEnergyUseReportForm
    task = EnergyUseReportTask

    def get_task_data(self, form):
        data = form.cleaned_data
        return {
            'energy_use_report_id': data['energy_use_report'].id,
            'from_date': data['from_date'],
            'to_date': data['to_date'],
            'previous_period_from_date': data['previous_period_from_date'],
            'previous_period_to_date': data['previous_period_to_date'],
            'include_cost': data['include_cost'],
            'include_co2': data['include_co2'],
        }
