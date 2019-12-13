# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from celery import shared_task
from celery import Task

from legacy.measurementpoints.models import AbstractGraph
from legacy.measurementpoints.models import Summation
from legacy.measurementpoints.models import Utilization
from legacy.measurementpoints.models import DataSeries
from legacy.measurementpoints.models import SimpleLinearRegression
from legacy.measurementpoints.models import PiecewiseConstantIntegral
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils import utilitytypes
from legacy.energy_use_reports.tasks import TaskProgressMixin
from gridplatform.utils.condense import get_date_formatter
from gridplatform.trackuser.tasks import trackuser_task
from gridplatform.trackuser import get_user

from .models import ENPIReport
from .models import ENPIUseArea


class AbstractENPIGraph(AbstractGraph):
    def __init__(self, enpi_report_task):
        self.enpi_report_task = enpi_report_task

        # @bug: utility_types can be mixed, but the term preferred unit for
        # mixed resource types makes no sense.  Hopefully we find a solution
        # before non-energies are to be used.
        self.utility_type = utilitytypes.OPTIONAL_METER_CHOICES.electricity

    def get_energy_data_series(self):
        raise NotImplementedError('not implemented by %r' % self.__class__)

    def get_enpi_data_series(self, energy):
        raise NotImplementedError('not implemented by %r' % self.__class__)

    def no_enpi_data(self):
        raise NotImplementedError('not implemented by %r' % self.__class__)

    def initial_enpi_is_zero(self):
        raise NotImplementedError('not implemented by %r' % self.__class__)

    def _get_data_series(self):
        energy = Summation(
            role=DataRoleField.CONSUMPTION,
            unit=self.enpi_report_task.enpi_report.energy_unit,
            utility_type=self.utility_type,
            customer=self.enpi_report_task.enpi_report.customer)
        energy.plus_data_series = self.get_energy_data_series()
        enpi = self.get_enpi_data_series(energy)

        trendline = SimpleLinearRegression(data=enpi)
        trendline.full_clean(exclude=['data'])

        return [enpi, trendline]

    def tick_progress(self):
        self.enpi_report_task.tick_progress()

    def get_colors(self):
        return ['#00A8F0', '#A80000']

    def collect_data(self, from_timestamp, to_timestamp, sample_resolution):
        """
        Collect data for this graph.

        The data is not only used in the graph plot, but also for other
        purposes.

        @postcondition: The result of L{get_graph_data()} can be found in
        self.graph_data.
        """
        self.errors = []

        # calculate num_samples
        num_samples = 0
        while from_timestamp + num_samples * sample_resolution < to_timestamp:
            num_samples += 1

        self.graph_data = self.get_graph_data(
            min(num_samples, 12),
            from_timestamp,
            sample_resolution=sample_resolution,
            num_samples=num_samples,
            weekends_are_special=False)
        enpi_data = self.graph_data['data'][0]['data']
        self.table_data = []

        if enpi_data:
            SAMPLE_VALUE = 1
            first_value = enpi_data[0][SAMPLE_VALUE]
            date_formatter = get_date_formatter(
                from_timestamp, to_timestamp, resolution=sample_resolution)
            for i, s in enumerate(enpi_data, start=0):
                self.table_data.append(
                    {
                        'label': date_formatter(
                            from_timestamp + sample_resolution * i),
                        'enpi': s[SAMPLE_VALUE],
                    })
                if first_value != 0:
                    saved_pct = (
                        first_value - s[SAMPLE_VALUE]) * 100.0 / first_value
                    self.table_data[-1]['saved_pct'] = saved_pct
            if first_value == 0:
                self.initial_enpi_is_zero()
        else:
            self.no_enpi_data()


class TotalENPIGraph(AbstractENPIGraph):

    def get_energy_data_series(self):
        result = []

        for enpi_use_area in \
                self.enpi_report_task.enpi_report.enpiusearea_set.all():
            result.extend([
                ds.subclass_instance for ds in DataSeries.objects.filter(
                    role=DataRoleField.CONSUMPTION,
                    graph__hidden=False,
                    graph__collection_id__in=enpi_use_area.measurement_points.
                    all().values_list('id', flat=True))])
        return result

    def get_enpi_data_series(self, energy):
        if self.enpi_report_task.enpi_report.energy_driver_role in (
                DataRoleField.AREA, DataRoleField.EMPLOYEES):
            energy_drivers = [
                PiecewiseConstantIntegral(
                    role=DataRoleField.ENERGY_DRIVER,
                    data=enpi_use_area.energy_driver.subclass_instance)
                for enpi_use_area in
                self.enpi_report_task.enpi_report.enpiusearea_set.all()]

        elif self.enpi_report_task.enpi_report.energy_driver_role == \
                DataRoleField.PRODUCTION:
            energy_drivers = [
                enpi_use_area.energy_driver.subclass_instance for
                enpi_use_area in
                self.enpi_report_task.enpi_report.enpiusearea_set.all()]

        assert energy_drivers

        for energy_driver in energy_drivers:
            energy_driver.full_clean()

        enpi = Utilization(
            role=self.enpi_report_task.enpi_report.enpi_role,
            unit=self.enpi_report_task.enpi_report.enpi_unit,
            consumption=energy,
            utility_type=self.utility_type,
            customer=self.enpi_report_task.enpi_report.customer)
        enpi.energy_driver = Summation(
            role=DataRoleField.ENERGY_DRIVER,
            unit=energy_drivers[0].unit,
            utility_type=self.utility_type,
            customer=self.enpi_report_task.enpi_report.customer)

        enpi.energy_driver.plus_data_series = energy_drivers

        return enpi

    def no_enpi_data(self):
        # avoid non-ascii characters here
        self.errors.append(_('No total EnPI data available.'))

    def initial_enpi_is_zero(self):
        # avoid non-ascii characters here
        self.errors.append(
            _('EnPI for first period in total EnPI is zero.  '
              'Savings in percent cannot be calculated'))


class NoENPIUseAreaData(object):
    def __init__(self, enpi_use_area_id):
        self.enpi_use_area_id = enpi_use_area_id

    def __unicode__(self):
        return _('No EnPI data available for {use_area_name}'). \
            format(
                use_area_name=ENPIUseArea.objects.get(
                    id=self.enpi_use_area_id).name_plain)


class InitialUseAreaENPIIsZero(object):
    def __init__(self, enpi_use_area_id):
        self.enpi_use_area_id = enpi_use_area_id

    def __unicode__(self):
        return _(
            'EnPI for first period in {use_area_name} is zero.  '
            'Savings in percent cannot be calculated'). \
            format(
                use_area_name=ENPIUseArea.objects.get(
                    id=self.enpi_use_area_id).name_plain)


class ENPIUseAreaGraph(AbstractENPIGraph):
    def __init__(self, enpi_report_task, enpi_use_area):
        super(ENPIUseAreaGraph, self).__init__(enpi_report_task)
        self.enpi_use_area = enpi_use_area

    def get_energy_data_series(self):
        return [
            ds.subclass_instance for ds in DataSeries.objects.filter(
                role=DataRoleField.CONSUMPTION,
                graph__hidden=False,
                graph__collection_id__in=self.enpi_use_area.measurement_points.
                all().values_list('id', flat=True))]

    def get_enpi_data_series(self, energy):
        if self.enpi_report_task.enpi_report.energy_driver_role in (
                DataRoleField.AREA, DataRoleField.EMPLOYEES):
            enpi = Utilization(
                role=self.enpi_report_task.enpi_report.enpi_role,
                unit=self.enpi_report_task.enpi_report.enpi_unit,
                consumption=energy,
                needs=self.enpi_use_area.energy_driver,
                utility_type=self.utility_type,
                customer=self.enpi_report_task.enpi_report.customer)
        else:
            assert self.enpi_report_task.enpi_report.energy_driver_role in (
                DataRoleField.PRODUCTION, DataRoleField.HEATING_DEGREE_DAYS)
            enpi = Utilization(
                role=self.enpi_report_task.enpi_report.enpi_role,
                unit=self.enpi_report_task.enpi_report.enpi_unit,
                consumption=energy,
                utility_type=self.utility_type,
                customer=self.enpi_report_task.enpi_report.customer)
            enpi.energy_driver = self.enpi_use_area.energy_driver
        return enpi

    def no_enpi_data(self):
        self.errors.append(NoENPIUseAreaData(self.enpi_use_area.id))

    def initial_enpi_is_zero(self):
        self.errors.append(InitialUseAreaENPIIsZero(self.enpi_use_area.id))


# Softly kill using exception after 30 minutes. Kill for real after 31 minutes.
@trackuser_task
@shared_task(
    time_limit=1860, soft_time_limit=1800,
    name='legacy.enpi_reports.tasks.ENPIReportTask')
class ENPIReportTask(TaskProgressMixin, Task):
    def run(self, data):
        self.update_state(
            state='PROGRESS',
            meta={
                'task_user_id': get_user().id,
                'current': 0,
                'total': 0
            }
        )
        self.enpi_report = ENPIReport.objects.get(id=data['enpi_report_id'])
        self.enpi_use_areas = list(self.enpi_report.enpiusearea_set.all())
        self.PROGRESS_TOTAL = ENPIUseAreaGraph.PROGRESS_TOTAL * \
            len(self.enpi_use_areas)
        if len(self.enpi_use_areas) > 1:
            self.PROGRESS_TOTAL += TotalENPIGraph.PROGRESS_TOTAL
        self.progress = 0

        result = {
            'enpi_report': self.enpi_report.id,
            'errors': [],
            'data': {'something': ['something']},
            'enpi_use_areas': dict(),
            'sample_resolution': data['sample_resolution']
        }

        from_timestamp = data['from_timestamp']
        to_timestamp = data['to_timestamp']
        sample_resolution = data['sample_resolution']

        if len(self.enpi_use_areas) > 1:
            graph = TotalENPIGraph(self)
            graph.collect_data(from_timestamp, to_timestamp, sample_resolution)

            result['total_enpi'] = {
                'graph_data': graph.graph_data,
                'table_data': graph.table_data,
                'graph_name': 'total-enpi-graph'
            }
            result['errors'].extend(graph.errors)

        for use_area in self.enpi_use_areas:
            graph = ENPIUseAreaGraph(self, use_area)
            graph.collect_data(from_timestamp, to_timestamp, sample_resolution)

            result['enpi_use_areas'][use_area.id] = {
                'graph_data': graph.graph_data,
                'table_data': graph.table_data,
                'graph_name': 'enpi-use-area-graph-%d' % use_area.id,
            }
            result['errors'].extend(graph.errors)

        return result
