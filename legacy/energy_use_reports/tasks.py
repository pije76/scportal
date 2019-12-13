# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from collections import namedtuple
from datetime import datetime
from datetime import time
from datetime import timedelta  # RelativeTimeDelta does not work for dates.

from django.utils.translation import ugettext_lazy as _

from celery import shared_task
from celery import Task

from legacy.measurementpoints import default_unit_for_data_series
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils.utilitytypes import UTILITY_TYPE_TO_COLOR
from legacy.measurementpoints.models.graph import AbstractGraph
from legacy.measurementpoints.models import Summation
from gridplatform.trackuser.tasks import trackuser_task
from gridplatform.trackuser import get_user

from .models import EnergyUseReport
from .models import EnergyUseArea


class DataCollectionError(object):
    """
    Class for reporting errors during data collection in Celery tasks where
    encryption context is absent.

    Intended for use with L{EnergyUseReportTask}

    Actual localization and the string interpolation that follows is intended
    to happen once the a view receives C{DataCollectionError}s from the
    task that created these.
    """

    def __init__(self, error_message_format, measurement_point=None,
                 energy_use_area=None):
        """
        @param error_message_format: A ugettext_lazy object optionally
        containing formatters depending on other arguments.

        @param measurement_point: An optional measurement point. If given the
        C{error_message_format} must contain C{'{measurement_point}'}.

        @param energy_use_area: An optional area of energy use. If given the
        C{error_message_format} must contain C{'{energy_use_area}'}.
        """
        assert measurement_point is None or \
            '{measurement_point}' in unicode(error_message_format)
        assert energy_use_area is None or \
            '{energy_use_area}' in unicode(error_message_format)
        self.error_message_format = error_message_format

        if measurement_point is not None:
            self.measurement_point_id = measurement_point.id
        else:
            self.measurement_point_id = None

        if energy_use_area is not None:
            self.energy_use_area_id = energy_use_area.id
        else:
            self.energy_use_area_id = None

    def __unicode__(self):
        if self.measurement_point_id is not None:
            measurement_point = ConsumptionMeasurementPoint.objects.get(
                id=self.measurement_point_id)
        else:
            measurement_point = None

        if self.energy_use_area_id is not None:
            energy_use_area = EnergyUseArea.objects.get(
                id=self.energy_use_area_id)
        else:
            energy_use_area = None

        return self.error_message_format.format(
            measurement_point=measurement_point,
            energy_use_area=energy_use_area)


class ErrorCollector(object):
    """
    Collect errors during data collection.

    @ivar errors: A list of L{DataCollectionErrors} collected.

    @ivar consumption_error_collector: A PeriodErrorCollector for consumption.

    @ivar cost_error_collector: A  PeriodErrorCollector for cost.

    @ivar co2_error_collector: A  PeriodErrorCollector for co2.

    @cvar PeriodErrorCollector: Adaptor aggregate with two methods that will
    forward to the revelant method in C
    {ErrorCollector}. C{extrapolated_current_period()} is for telling this
    error collector about current period being extrapolated and
    C{extrapolated_previous_period()} is for telling this error collector about
    previous period being extrapolated.
    """

    PeriodErrorCollector = namedtuple(
        'PeriodErrorCollector',
        [
            'extrapolated_current_period',
            'extrapolated_previous_period'])

    def __init__(self, errors, mp):
        """
        Construct an error collector for a given error list and a given
        measurement point.

        @param errors: The list to be used as C{self.errors}.  Note that lists
        in Python are mutable, so the same list can be shared between multiple
        error collectors.

        @param mp: The L{ConsumptionMeasurementPoint} to collect errors about.
        """
        self.errors = errors
        self.mp = mp

        self.consumption_error_collector = self.PeriodErrorCollector(
            self.extrapolated_consumption_current_period,
            self.extrapolated_consumption_previous_period)

        self.cost_error_collector = self.PeriodErrorCollector(
            self.extrapolated_cost_current_period,
            self.extrapolated_cost_previous_period)

        self.co2_error_collector = self.PeriodErrorCollector(
            self.extrapolated_co2_current_period,
            self.extrapolated_co2_previous_period)

    def extrapolated_consumption_current_period(self):
        """
        Tell this C{ErrorCollector} that consumption of C{mp} has been
        extrapolated for the current period.
        """
        raise NotImplementedError()

    def extrapolated_consumption_previous_period(self):
        """
        Tell this C{ErrorCollector} that consumption of C{mp} has been
        extrapolated for the previous period.
        """
        raise NotImplementedError()

    def no_tariff(self):
        """
        Tell this C{ErrorCollector} that there is no tariff associtated with
        this C{mp}, and cost therefore cannot be calculated.
        """
        raise NotImplementedError()

    def bad_currency(self):
        """
        Tell this C{ErrorCollector} that the cost currency of C{mp} is
        incompatible with that of the energy use report, and cost therefore
        will not be inclued.
        """
        raise NotImplementedError()

    def extrapolated_cost_current_period(self):
        """
        Tell this C{ErrorCollector} that the cost of C{mp} for the current
        period is extrapolated.
        """
        raise NotImplementedError()

    def extrapolated_cost_previous_period(self):
        """
        Tell this C{ErrorCollector} that the cost of C{mp} for the previous
        period is extrapolated.
        """
        raise NotImplementedError()

    def no_co2_index(self):
        """
        Tell this C{ErrorCollector} that the CO2 emissions of C{mp} cannot be
        calculated because no CO2 index has been assigned.
        """
        raise NotImplementedError()

    def extrapolated_co2_current_period(self):
        """
        Tell this C{ErrorCollector} that the CO2 emissions of C{mp} for the
        current period are extrapolated.
        """
        raise NotImplementedError()

    def extrapolated_co2_previous_period(self):
        """
        Tell this C{ErrorCollector} that the CO2 emissions of C{mp} for the
        previous period are extrapolated.
        """
        raise NotImplementedError()


class MainMeasurementPointErrorCollector(ErrorCollector):
    def extrapolated_consumption_current_period(self):
        self.errors.append(
            DataCollectionError(
                _('The consumption of the main measurement point '
                  '{measurement_point}, is calculated from incomplete data '
                  'in the current period'), self.mp))

    def extrapolated_consumption_previous_period(self):
        self.errors.append(
            DataCollectionError(
                _('The consumption of the main measurement point '
                  '{measurement_point}, is calculated from incomplete data '
                  'in the previous period'), self.mp))

    def no_tariff(self):
        self.errors.append(
            DataCollectionError(
                _('Unable to calculate cost for '
                  'the main measurement point '
                  '{measurement_point}, because it has no tariff'), self.mp))

    def bad_currency(self):
        self.errors.append(
            DataCollectionError(
                _('Unable to calculate cost for '
                  'the main measurement point '
                  '{measurement_point}, because the '
                  'tariff currency is different '
                  'from the report currency'), self.mp))

    def extrapolated_cost_current_period(self):
        self.errors.append(
            DataCollectionError(
                _('The cost of the main measurement point '
                  '{measurement_point}, is calculated from incomplete data '
                  'in the current period'), self.mp))

    def extrapolated_cost_previous_period(self):
        self.errors.append(
            DataCollectionError(
                _('The cost of the main measurement point '
                  '{measurement_point}, is calculated from incomplete data '
                  'in the previous period'), self.mp))

    def no_co2_index(self):
        self.errors.append(
            DataCollectionError(
                _(u'Unable to calculate CO₂ emissions for '
                  'the main measurement point {measurement_point}, '
                  'because the '
                  u'measurement point has no CO₂ index assigned'),
                self.mp))

    def extrapolated_co2_current_period(self):
        self.errors.append(
            DataCollectionError(
                _(u'The CO₂ emissions of the main measurement point '
                  '{measurement_point} are calculated from incomplete data '
                  'in the current period'), self.mp))

    def extrapolated_co2_previous_period(self):
        self.errors.append(
            DataCollectionError(
                _(u'The CO₂ emissions of the main measurement point '
                  '{measurement_point} are calculated from incomplete data '
                  'in the previous period'), self.mp))


class AreaErrorCollector(ErrorCollector):
    def __init__(self, errors, mp, area):
        super(AreaErrorCollector, self).__init__(errors, mp)
        self.area = area

    def extrapolated_consumption_current_period(self):
        self.errors.append(
            DataCollectionError(
                _('The consumption of the measurement point '
                  '{measurement_point} in the area of energy use '
                  '{energy_use_area}, is calculated from incomplete data '
                  'in the current period'),
                self.mp, self.area))

    def extrapolated_consumption_previous_period(self):
        self.errors.append(
            DataCollectionError(
                _('The consumption of the measurement point '
                  '{measurement_point} in the area of energy use '
                  '{energy_use_area}, is calculated from incomplete data '
                  'in the previous period'),
                self.mp, self.area))

    def no_tariff(self):
        self.errors.append(
            DataCollectionError(
                _('Unable to calculate cost for the measurement point '
                  '{measurement_point} in the area of energy use '
                  '{energy_use_area}, because the measurement point has '
                  'no tariff'), self.mp, self.area))

    def bad_currency(self):
        self.errors.append(
            DataCollectionError(
                _('Unable to calculate cost for the measurement point '
                  '{measurement_point} in the area of energy use '
                  '{energy_use_area}, because the tariff currency is '
                  'different from the report currency'), self.mp, self.area))

    def extrapolated_cost_current_period(self):
        self.errors.append(
            DataCollectionError(
                _('The cost of the measurement point {measurement_point} '
                  'in the area of energy use {energy_use_area}, is calculated '
                  'from incomplete data in the current period'),
                self.mp, self.area))

    def extrapolated_cost_previous_period(self):
        self.errors.append(
            DataCollectionError(
                _('The cost of the measurement point {measurement_point} '
                  'in the area of energy use {energy_use_area}, is calculated '
                  'from incomplete data in the previous period'),
                self.mp, self.area))

    def no_co2_index(self):
        self.errors.append(
            DataCollectionError(
                _(u'Unable to calculate CO₂ emissions for the measurement '
                  'point {measurement_point} in the area of energy use '
                  '{energy_use_area}, because the '
                  u'measurement point has no CO₂ index assigned'),
                self.mp, self.area))

    def extrapolated_co2_current_period(self):
        self.errors.append(
            DataCollectionError(
                _(u'The CO₂ emissions of the measurement point '
                  '{measurement_point} in the area of energy use '
                  '{energy_use_area}, is calculated from incomplete data in '
                  'the current period'), self.mp, self.area))

    def extrapolated_co2_previous_period(self):
        self.errors.append(
            DataCollectionError(
                _(u'The CO₂ emissions of the measurement point '
                  '{measurement_point} in the area of energy use '
                  '{energy_use_area}, is calculated from incomplete data in '
                  'the previous period'), self.mp, self.area))


class EnergyUseGraph(AbstractGraph):
    def __init__(self, energy_use_report_task, errors):
        self.energy_use_report_task = energy_use_report_task
        self.errors = errors

    MAX_SAMPLES = 1000

    @classmethod
    def get_sample_resolution(cls, from_timestamp, to_timestamp):
        """
        Derive desired sample resolution from from_timestamp and to_timestamp
        """
        if from_timestamp + RelativeTimeDelta(hours=cls.MAX_SAMPLES) > \
                to_timestamp:
            sample_resolution = RelativeTimeDelta(hours=1)
        elif from_timestamp + RelativeTimeDelta(days=cls.MAX_SAMPLES) > \
                to_timestamp:
            sample_resolution = RelativeTimeDelta(days=1)
        else:
            assert from_timestamp + RelativeTimeDelta(months=cls.MAX_SAMPLES) > \
                to_timestamp
            sample_resolution = RelativeTimeDelta(months=1)
        return sample_resolution

    def get_bar_graph_data(self, from_timestamp, to_timestamp):
        sample_resolution = self.get_sample_resolution(
            from_timestamp, to_timestamp)
        num_samples = 0
        while from_timestamp + sample_resolution * (num_samples + 1) <= \
                to_timestamp:
            num_samples += 1
        assert from_timestamp + num_samples * sample_resolution <= to_timestamp
        assert num_samples <= self.MAX_SAMPLES

        result = self.get_graph_data(
            num_ticks=min(5, num_samples),
            from_timestamp=from_timestamp,
            num_samples=num_samples,
            sample_resolution=sample_resolution,
            weekends_are_special=False)

        return result

    def tick_progress(self):
        """
        Update progress on L{EnergyUseReportTask} task.
        """
        self.energy_use_report_task.tick_progress()


class EnergyUseConsumptionGraph(EnergyUseGraph):
    def _get_data_series(self):
        consumptions = []
        if self.energy_use_report_task.energy_use_report.\
                main_measurement_points.exists():
            consumptions = [
                mp.subclass_instance.consumption.subclass_instance for mp in
                self.energy_use_report_task.energy_use_report.
                main_measurement_points.all()]
        else:
            for area in self.energy_use_report_task.energy_use_report.\
                    energyusearea_set.all():
                for mp in area.measurement_points.all():
                    consumptions.append(
                        mp.subclass_instance.consumption.subclass_instance)
        result = Summation()
        result.role = DataRoleField.CONSUMPTION
        result.unit = default_unit_for_data_series(
            DataRoleField.CONSUMPTION,
            self.energy_use_report_task.energy_use_report.utility_type)
        result.utility_type = self.energy_use_report_task.\
            energy_use_report.utility_type
        result.plus_data_series = consumptions
        result.customer = self.energy_use_report_task.energy_use_report.\
            customer
        return [result]

    def get_colors(self):
        return [
            UTILITY_TYPE_TO_COLOR[
                self.energy_use_report_task.energy_use_report.utility_type]]


class EnergyUseCo2EmissionGraph(EnergyUseGraph):
    def _get_data_series(self):
        co2 = []
        if self.energy_use_report_task.energy_use_report.\
                main_measurement_points.exists():
            measurement_points = self.energy_use_report_task.\
                energy_use_report.main_measurement_points.all()
        else:
            measurement_points = ConsumptionMeasurementPoint.objects.filter(
                energyusearea__report=self.energy_use_report_task.
                energy_use_report)

        for mp in measurement_points:
            if mp.subclass_instance.co2calculation is not None:
                co2.append(mp.subclass_instance.co2calculation)
            else:
                self.errors.append(
                    DataCollectionError(
                        _('CO₂ emissions for the measurement point '
                          '{measurement_point} are not defined, and '
                          'therefore not included in the CO₂ emissions '
                          'graph.'), mp))

        result = Summation()
        result.role = DataRoleField.CO2
        result.unit = default_unit_for_data_series(
            DataRoleField.CO2,
            self.energy_use_report_task.energy_use_report.utility_type)
        result.utility_type = self.energy_use_report_task.energy_use_report.\
            utility_type
        result.plus_data_series = co2
        result.customer = self.energy_use_report_task.energy_use_report.\
            customer
        return [result]

    def _get_unit_display(self):
        return self.energy_use_report_task.energy_use_report.\
            get_preferred_co2_emission_unit_display()

    def get_colors(self):
        return ['#444444']


class TaskProgressMixin(object):
    """
    Celery Task mixin that provides means for progress reporting.
    """

    def tick_progress(self):
        """
        Make the progress state of this Task tick.

        @precondition: C{self.PROGRESS_TOTAL} must be set.

        @precondition: C{self.progress} must have been reset once for current
        task invocation.

        @precondition: This method must not be called more than
        C{self.PROGRESS_TOTAL} times for each invocation; i.e. C{self.progress
        <= self.PROGRESS_TOTAL}.

        @precondition: get_user() must return a User. (decorate your task with
        L{trackuser_task} if it doesn't)
        """
        assert self.progress <= self.PROGRESS_TOTAL, \
            (self.progress, self.PROGRESS_TOTAL)
        self.update_state(
            state='PROGRESS',
            meta={
                'task_user_id': get_user().id,
                'current': self.progress,
                'total': self.PROGRESS_TOTAL
            }
        )
        self.progress += 1


# Softly kill using exception after 30 minutes. Kill for real after 31 minutes.
@trackuser_task
@shared_task(
    time_limit=1860, soft_time_limit=1800,
    name='legacy.energy_use_reports.tasks.EnergyUseReportTask')
class EnergyUseReportTask(TaskProgressMixin, Task):
    """
    Celery task for collecting energy use report data.

    Intended to work with L{StartReportView} and
    L{GenerateEnergyUseReportForm}.
    """
    ZERO_CO2_EMISSION = PhysicalQuantity(0, 'gram')

    def _collect_data_series_period_data(self, data_series, error_collector):
        data_sample = data_series.calculate_development(
            self.from_timestamp, self.to_timestamp)
        if data_sample is None:
            data = PhysicalQuantity(0, data_series.unit)
            error_collector.extrapolated_current_period()
        elif data_sample.extrapolated:
            data = data_sample.physical_quantity
            error_collector.extrapolated_current_period()
        else:
            data = data_sample.physical_quantity

        data_sample = data_series.calculate_development(
            self.previous_from_time, self.previous_to_time)
        if data_sample is None:
            previous_data = PhysicalQuantity(0, data_series.unit)
            error_collector.extrapolated_previous_period()
        elif data_sample.extrapolated:
            previous_data = data_sample.physical_quantity
            error_collector.extrapolated_previous_period()
        else:
            previous_data = data_sample.physical_quantity

        return {
            'data': data,
            'previous_data': previous_data,
        }

    def _collect_measurement_point_period_data(self, mp, error_collector):
        consumption_data = self._collect_data_series_period_data(
            mp.consumption, error_collector.consumption_error_collector)
        self.consumption += consumption_data['data']
        self.previous_consumption += consumption_data['previous_data']

        if self.include_cost:
            if mp.cost is None:
                error_collector.no_tariff()
            elif not PhysicalQuantity.compatible_units(
                    mp.cost.unit, self.energy_use_report.currency_unit):
                error_collector.bad_currency()
            else:
                cost_data = self._collect_data_series_period_data(
                    mp.cost, error_collector.cost_error_collector)
                self.cost += cost_data['data']
                self.previous_cost += cost_data['previous_data']

        if self.include_co2:
            if mp.co2calculation is None:
                error_collector.no_co2_index()
            else:
                co2_data = self._collect_data_series_period_data(
                    mp.co2calculation, error_collector.co2_error_collector)
                self.co2 += co2_data['data']
                self.previous_co2 += co2_data['previous_data']

    def _reset_period_variables(self):
        self.consumption = self.ZERO_CONSUMPTION
        self.previous_consumption = self.ZERO_CONSUMPTION
        self.cost = self.ZERO_COST
        self.previous_cost = self.ZERO_COST
        self.co2 = self.ZERO_CO2_EMISSION
        self.previous_co2 = self.ZERO_CO2_EMISSION

    def run(self, data):
        """
        @return: Returns a dictionary containing the keys
        C{'energy_use_report'}, C{'errors'} and C{'data'}.  C{'errors'} maps to
        a list of L{DataCollectionError}, and C{'data'} maps to another
        dictionary of L{EnergyUseArea} ids mapped to yet another dictionary
        mapping C{'cost'} to the combined cost of the particular area of energy
        use, and C{'consumption'} to the combined consumption of the particular
        area of energy use.  For example::

            {
                'energy_use_report': 11,
                'errors': [],
                'data': {
                    42: {
                        'cost': Fraction(3, 2),
                        'consumption': Fraction(5, 2)
                    }
                }
            }

        """
        self.update_state(
            state='PROGRESS',
            meta={
                'task_user_id': get_user().id,
                'current': 0,
                'total': 0
            }
        )
        self.energy_use_report = EnergyUseReport.objects.get(
            id=data['energy_use_report_id'])

        self.ZERO_CONSUMPTION = PhysicalQuantity(
            0,
            default_unit_for_data_series(
                DataRoleField.CONSUMPTION,
                self.energy_use_report.utility_type))
        self.ZERO_COST = PhysicalQuantity(
            0, self.energy_use_report.currency_unit)

        customer = self.energy_use_report.customer
        self.from_timestamp = customer.timezone.localize(
            datetime.combine(
                data['from_date'], time()))
        self.to_timestamp = customer.timezone.localize(
            datetime.combine(
                data['to_date'], time())) + \
            RelativeTimeDelta(days=1)
        self.include_cost = data['include_cost']
        self.include_co2 = data['include_co2']

        self.previous_from_time = customer.timezone.localize(
            datetime.combine(
                data['previous_period_from_date'], time()))
        self.previous_to_time = customer.timezone.localize(
            datetime.combine(
                data['previous_period_to_date'], time())) + \
            RelativeTimeDelta(days=1)

        self.PROGRESS_TOTAL = ConsumptionMeasurementPoint.objects.filter(
            energyusearea__report_id=self.energy_use_report.id).count() + \
            self.energy_use_report.main_measurement_points.count() + \
            EnergyUseConsumptionGraph.PROGRESS_TOTAL

        if data['include_co2']:
            self.PROGRESS_TOTAL += EnergyUseCo2EmissionGraph.PROGRESS_TOTAL

        self.progress = 0
        self.tick_progress()

        errors = []
        consumption_graph = EnergyUseConsumptionGraph(self, errors)

        result = {
            'energy_use_report': self.energy_use_report.id,
            'errors': errors,
            'data': {},
            'from_date': self.from_timestamp.date(),
            'to_date': self.to_timestamp.date() - timedelta(days=1),
            'previous_from_date': self.previous_from_time.date(),
            'previous_to_date': (
                self.previous_to_time.date() - timedelta(days=1)),
            'graph_data': consumption_graph.get_bar_graph_data(
                self.from_timestamp, to_timestamp=self.to_timestamp),
            'include_cost': self.include_cost,
            'include_co2': self.include_co2
        }

        if data['include_co2']:
            co2_emission_graph = EnergyUseCo2EmissionGraph(self, errors)
            result['co2_graph_data'] = co2_emission_graph.get_bar_graph_data(
                self.from_timestamp, to_timestamp=self.to_timestamp)

        for area in self.energy_use_report.energyusearea_set.all():
            self._reset_period_variables()
            # period variables are now collecting data for area
            for mp in area.measurement_points.all():
                self.tick_progress()

                mp = mp.subclass_instance

                error_collector = AreaErrorCollector(
                    result['errors'], mp, area)

                self._collect_measurement_point_period_data(
                    mp, error_collector)

            result['data'][area.id] = {
                'consumption': self.consumption.convert(
                    self.energy_use_report.get_preferred_unit()),
                'cost': self.cost.convert(
                    self.energy_use_report.currency_unit),
                'co2': self.co2.convert(
                    self.energy_use_report.get_preferred_co2_emission_unit()),
                'previous_consumption': self.previous_consumption.convert(
                    self.energy_use_report.get_preferred_unit()),
                'previous_cost': self.previous_cost.convert(
                    self.energy_use_report.currency_unit),
                'previous_co2': self.previous_co2.convert(
                    self.energy_use_report.get_preferred_co2_emission_unit()),
            }

        self._reset_period_variables()
        # period variables are now collecting data for main measurement points.
        if self.energy_use_report.main_measurement_points.exists():
            for mp in self.energy_use_report.main_measurement_points.all():

                self.tick_progress()

                mp = mp.subclass_instance

                error_collector = MainMeasurementPointErrorCollector(
                    result['errors'], mp)

                self._collect_measurement_point_period_data(mp,
                                                            error_collector)
        else:
            result['errors'].append(
                DataCollectionError(
                    _('No main measurement point has been selected.  '
                      'Assuming all measurement points are main '
                      'measurement points, and that no costs nor consumptions '
                      'are unaccounted for.')))

        result['total_consumption'] = self.consumption.convert(
            self.energy_use_report.get_preferred_unit())
        result['total_cost'] = self.cost.convert(
            self.energy_use_report.currency_unit)
        result['total_co2'] = self.co2.convert(
            self.energy_use_report.get_preferred_co2_emission_unit())
        result['total_previous_consumption'] = \
            self.previous_consumption.convert(
                self.energy_use_report.get_preferred_unit())
        result['total_previous_cost'] = self.previous_cost.convert(
            self.energy_use_report.currency_unit)
        result['total_previous_co2'] = self.previous_co2.convert(
            self.energy_use_report.get_preferred_co2_emission_unit())

        return result
