# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from collections import namedtuple
from datetime import datetime
from datetime import timedelta
from fractions import Fraction
import itertools

from django.db import models
from django.db.models import Sum
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.db.models import Q

import pytz

from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.models import CollectionConstraint
from gridplatform.customers.models import Customer
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.fields import EncryptedTextField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_user
from gridplatform.trackuser import replace_user
from gridplatform.utils import condense
from gridplatform.utils import deprecated
from gridplatform.utils import unix_timestamp
from gridplatform.utils import utilitytypes
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.unitconversion import PhysicalQuantity
from legacy.legacy_utils.preferredunits import get_preferred_unit_converter
from legacy.measurementpoints import default_unit_for_data_series
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import DataSeries


def payback_period_years(investment, subsidy, annual_cost_savings):
    """
    Calculate payback period in years given an investment, subsidy (possibly
    0), and annual cost savings. If annual_cost_savings <= 0 then None is
    returned.
    """
    if annual_cost_savings:
        return (investment - subsidy) / annual_cost_savings
    else:
        return None


class BenchmarkProjectManager(models.Manager):
    def get_query_set(self):
        customer = get_customer()
        user = get_user()
        qs = super(BenchmarkProjectManager, self).get_query_set()

        if customer is None or user is None:
            assert user is None
            return qs

        qs = qs.filter(customer=customer)

        constraints = CollectionConstraint.objects.filter(
            userprofile__user=user)
        if constraints:
            with replace_user(None):
                customer_collections = set(
                    Collection.objects.all().values_list('id', flat=True))
            user_collections = set(
                Collection.objects.all().values_list('id', flat=True))
            hidden_collections = customer_collections - user_collections
            qs = qs.exclude(
                baseline_measurement_points__in=hidden_collections)
            qs = qs.exclude(result_measurement_points__in=hidden_collections)
        return qs


class BenchmarkProject(EncryptedModel):
    """
    Django model for holding benchmark projects.

    @note: The contents of this model is probably generic enough for all kinds
    of projects, and a role/delegate scheme might be applied in the future.
    This change is expected to be small, and therefore only prematurely
    mentioned here, and not prematurely implemented.

    @ivar name: The name of this C{Project}.

    @ivar customer: A customer which the project is bound to.

    @ivar background: The background of this C{Project}.

    @ivar customer: The customer owning this C{Project}.

    @ivar goal: The goal of this C{BenchmarkProject}.  This value is a
    percentage with two decimals between 0 % and 100 %.

    @ivar currency_unit: Legacy field. Should always equal the customers
    currency_unit for new projects.

    @invariant: currency_unit may not be modified after a C{Project} has been
    saved the first time.  Changing currency_unit potentially invalidates all
    involved MeasurementPoints.

    @ivar utility_type: With current specifications, C{BenchmarkProject}s are
    not well-defined if they mix L{MeasurementPoint}s of different data
    origin. This field serves to help validate that only L{MeasurementPoint}s
    of same data origin are selected.

    @invariant: C{utility_type} may not be modified after a C{Project} has been
    saved the first time.  Changing C{utility_type} for sure will invalidate
    all involved L{MeasurementPoint}s.

    @bug: Consumption unit is not stored. Consumption values are invalidated
    when customer changes consumption unit.
    """
    name = EncryptedCharField(
        _('name'),
        max_length=50)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, editable=False, blank=True,
        default=get_customer, verbose_name=_('customer'))
    background = EncryptedTextField(_('background'), blank=True)
    expectations = EncryptedTextField(_('expectations'), blank=True)
    actions = EncryptedTextField(_('actions'), blank=True)

    subsidy = models.DecimalField(
        _('subsidy'), blank=True, null=True, max_digits=19, decimal_places=2)

    result = EncryptedTextField(_('result'), blank=True)
    comments = EncryptedTextField(
        _('comments'),
        blank=True,
        help_text=_(
            'Comments about project schedules, project changes, contact '
            'persons and so on.'))
    # FIMXE: Rename to 'months' or 'duration_in_months'.
    runtime = models.IntegerField(
        _('project duration'),
        default=1)

    estimated_yearly_consumption_costs_before = models.DecimalField(
        _('estimated yearly costs before'),
        blank=True, null=True,
        max_digits=19, decimal_places=2)

    estimated_yearly_consumption_before = models.DecimalField(
        _('estimated yearly consumption before'),
        blank=True, null=True,
        max_digits=19, decimal_places=2)

    estimated_co2_emissions_before = models.DecimalField(
        _(u'estimated yearly CO₂ emissions before'), blank=True, null=True,
        max_digits=19, decimal_places=2)

    expected_savings_in_yearly_total_costs = models.DecimalField(
        _('expected savings in yearly total costs'), default=0, max_digits=19,
        decimal_places=2)

    expected_savings_in_yearly_consumption_after = models.DecimalField(
        _('expected savings in yearly consumption after'), default=0,
        max_digits=19, decimal_places=2)

    expected_reduction_in_yearly_co2_emissions = models.DecimalField(
        _('expected reduction in yearly CO₂ emissions'), default=0,
        max_digits=19, decimal_places=2)

    utility_type = models.IntegerField(
        _('utility type'), choices=utilitytypes.METER_CHOICES)

    include_measured_costs = models.BooleanField(
        _('include measured costs'),
        default=False)

    baseline_from_timestamp = models.DateTimeField(blank=True, null=True)
    baseline_to_timestamp = models.DateTimeField(blank=True, null=True)
    baseline_measurement_points = models.ManyToManyField(
        ConsumptionMeasurementPoint,
        related_name='benchmarkproject_baseline_member',
        blank=True)

    result_from_timestamp = models.DateTimeField(blank=True, null=True)
    result_to_timestamp = models.DateTimeField(blank=True, null=True)
    result_measurement_points = models.ManyToManyField(
        ConsumptionMeasurementPoint,
        related_name='benchmarkproject_result_member',
        blank=True)

    objects = BenchmarkProjectManager()

    def state_description(self):
        now = self.customer.now()
        if self.from_timestamp is None or self.to_timestamp is None or \
                now <= self.from_timestamp:
            return _('In planning')
        elif self.from_timestamp < now < self.to_timestamp:
            return _('In progress')
        else:
            assert self.to_timestamp <= now
            return _('Completed')

    def __unicode__(self):
        state = self.state_description()
        name = self.name_plain or self.name
        return unicode("{name} ({state})".format(name=name, state=state))

    def cost_currency_conflicts(self):
        """
        @return: C{True} if there are any cost currency conflicts, in which
        case measured costs cannot be included in the resulting benchmark
        report.
        """
        measurement_points = list(
            self.baseline_measurement_points.values_list(
                'id', flat=True)) + \
            list(self.result_measurement_points.values_list(
                'id', flat=True))

        return DataSeries.objects.filter(
            role=DataRoleField.COST,
            graph__collection_id__in=measurement_points).exclude(
            unit__contains=self.customer.currency_unit).exists()

    def clean(self):
        dates = (self.baseline_from_timestamp, self.baseline_to_timestamp,
                 self.result_from_timestamp, self.result_to_timestamp)
        if any(dates) and not all(dates):
            raise ValidationError(
                _('Fill in all "baseline" and "result" dates.'))
        elif all(dates):
            if self.baseline_from_timestamp >= self.baseline_to_timestamp:
                raise ValidationError(
                    _('Baseline "to" is not after "from".'))
            if self.result_from_timestamp >= self.result_to_timestamp:
                raise ValidationError(
                    _('Result "to" is not after "from".'))

        return super(BenchmarkProject, self).clean()

    @property
    def from_timestamp(self):
        return min(self.baseline_from_timestamp, self.result_from_timestamp)

    @property
    def to_timestamp(self):
        return max(self.baseline_to_timestamp, self.result_to_timestamp)

    @cached_property
    def baseline_stage(self):
        return BaselineStage(self)

    @cached_property
    def result_stage(self):
        return ResultStage(self)

    def get_encryption_id(self):
        return (Customer, self.customer_id)

    @classmethod
    def active(cls, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now(pytz.utc)
        return cls.objects.filter(
            Q(baseline_to_timestamp__gt=timestamp) |
            Q(result_to_timestamp__gt=timestamp) |
            Q(result_to_timestamp__isnull=True) |
            Q(baseline_to_timestamp__isnull=True))

    @classmethod
    def done(cls, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now(pytz.utc)
        return cls.objects.filter(
            Q(baseline_to_timestamp__lte=timestamp) &
            Q(result_to_timestamp__lte=timestamp))

    def active_stages(self, timestamp=None):
        """
        The active Stage(s).

        @param timestamp: Optional specify time at which the returned stages
        should be active. If not given now is assumed.

        @return: Returns a list of stages that are currently active.
        """
        if timestamp is None:
            timestamp = datetime.now(pytz.utc)
        stages = []
        if self.baseline_from_timestamp <= timestamp <= \
                self.baseline_to_timestamp:
            stages.append(_('Baseline'))
        if self.result_from_timestamp <= timestamp <= self.result_to_timestamp:
            stages.append(_('Result'))
        return stages

    def yearly_additional_co2(self):
        unit = 'tonne'
        before = PhysicalQuantity(0, unit)
        after = PhysicalQuantity(0, unit)
        for saving in self.additionalsaving_set.all():
            before += PhysicalQuantity(
                saving.before_co2 or 0, unit)
            after += PhysicalQuantity(
                saving.after_co2 or 0, unit)
        return {
            'before': before,
            'after': after,
        }

    def yearly_additional_co2_savings(self):
        sums = self.yearly_additional_co2()
        yearly = sums['before'] - sums['after']
        return yearly

    def yearly_co2_savings(self):
        return self.co2_saving_rate * PhysicalQuantity(365, 'day') + \
            self.yearly_additional_co2_savings()

    def project_co2_savings(self):
        return self.yearly_co2_savings() * (float(self.runtime) / 12)

    def yearly_co2_savings_pct(self):
        """
        @return: CO2 savings in %.
        Returns None if no CO2 data exists for stage_1 and no additional
        co2 savings has been provided.
        """
        yearly_additional_co2_savings = \
            self.yearly_additional_co2()['before'] - \
            self.yearly_additional_co2()['after']
        try:
            return (
                (
                    self.co2_saving_rate +
                    yearly_additional_co2_savings /
                    PhysicalQuantity(365, 'day')) * 100 /
                (
                    self.baseline_stage.mean_co2_rate +
                    self.yearly_additional_co2()['before'] /
                    PhysicalQuantity(365, 'day')
                )).convert('none')
        except ZeroDivisionError:
            return None

    def yearly_measured_consumption_savings(self):
        """
        @return: A PhysicalQuantity holding the yearly consumption savings.
        """
        return self.consumption_saving_rate * PhysicalQuantity(365, 'day')

    def yearly_additional_consumption(self):
        unit = default_unit_for_data_series(
            DataRoleField.CONSUMPTION, self.utility_type)
        before = PhysicalQuantity(0, unit)
        after = PhysicalQuantity(0, unit)
        for saving in self.additionalsaving_set.all():
            before += PhysicalQuantity(
                saving.before_energy or 0, saving.energy_unit)
            after += PhysicalQuantity(
                saving.after_energy or 0, saving.energy_unit)
        return {
            'before': before,
            'after': after,
        }

    def yearly_additional_consumption_savings(self):
        sums = self.yearly_additional_consumption()
        yearly = sums['before'] - sums['after']
        return yearly

    def yearly_consumption_savings(self):
        return self.yearly_measured_consumption_savings() + \
            self.yearly_additional_consumption_savings()

    def project_consumption_savings(self):
        return self.yearly_consumption_savings() * (self.runtime / 12)

    def yearly_consumption_savings_pct(self):
        try:
            stage1_consumption = self.baseline_stage.mean_consumption_rate * \
                PhysicalQuantity(365, 'day') + \
                self.yearly_additional_consumption()['before']
            return float(
                (
                    self.yearly_consumption_savings() * 100 /
                    stage1_consumption).convert('none'))
        except ZeroDivisionError:
            return None

    def yearly_consumption_savings_display(self):
        """
        Method for giving tuple suitable for the L{physicalquantity} template
        filter.

        @return: A tuple (n, u) where n is a numeric yearly consumption savings
        in customers preferred unit, and u is the human readable preferred unit
        for the customer.
        """
        preferred_unit_converter = get_preferred_unit_converter(
            DataRoleField.CONSUMPTION, utility_type=self.utility_type)

        return (
            preferred_unit_converter.extract_value(
                self.yearly_consumption_savings()),
            preferred_unit_converter.get_display_unit())

    def yearly_additional_cost(self):
        sums = self.additionalsaving_set.aggregate(
            Sum('before_cost'),
            Sum('after_cost'))
        before_cost = sums['before_cost__sum'] or 0
        after_cost = sums['after_cost__sum'] or 0
        return {
            'before': PhysicalQuantity(
                before_cost, self.customer.currency_unit),
            'after': PhysicalQuantity(after_cost, self.customer.currency_unit),
        }

    def yearly_additional_cost_savings(self):
        sums = self.yearly_additional_cost()
        yearly = sums['before'] - sums['after']
        return yearly

    def yearly_measured_cost_savings(self):
        if not self.include_measured_costs or self.cost_currency_conflicts():
            return PhysicalQuantity(0, self.customer.currency_unit)
        return self.cost_saving_rate * PhysicalQuantity(365, 'day')

    @cached_property
    def investment(self):
        """
        The total expenses for all investments in this project.
        """
        return sum(
            (
                investment.get_total_costs() for
                investment in self.cost_set.all()),
            0)

    def average_monthly_project_costs(self):
        total = self.investment / self.runtime
        return PhysicalQuantity(total, self.customer.currency_unit)

    def average_yearly_project_costs(self):
        return self.average_monthly_project_costs() * 12

    def resulting_annual_cost_savings(self):
        return self.yearly_measured_cost_savings() + \
            self.yearly_additional_cost_savings() - \
            self.average_yearly_project_costs()

    def project_cost_savings(self):
        return self.resulting_annual_cost_savings() * \
            (self.runtime / float(12))

    def resulting_annual_cost_savings_pct(self):
        try:
            stage1_cost = self.yearly_additional_cost()['before']
            if self.include_measured_costs and \
                    not self.cost_currency_conflicts():
                stage1_cost += self.baseline_stage.mean_cost_rate * \
                    PhysicalQuantity(365, 'day')

            return float((self.resulting_annual_cost_savings() * 100 /
                          stage1_cost).convert('none'))
        except ZeroDivisionError:
            return None

    def resulting_annual_cost_savings_display(self):
        """
        Method for giving tuple suitable for the L{physicalquantity} template.

        @return: A tuple (n, u) where n is the yearly cost savings and u is the
        human readable currency of the cost savings.
        """
        return (self.resulting_annual_cost_savings().convert(
                self.customer.currency_unit),
                self.customer.get_currency_unit_display())

    @deprecated
    @property
    def duration(self):
        """
        The duration of this C{Project} is defined as the the earliest stage
        start and the latest stage end.

        @precondition: Both STAGE_1 and STAGE_2 stages have been stored for
        this C{Project}.

        @return: Returns a named tuple C{(from_timestamp, to_timestamp)}
        """
        FromTimeToTime = namedtuple(
            'FromTimeToTime', ['from_timestamp', 'to_timestamp'])
        return FromTimeToTime(self.from_timestamp, self.to_timestamp)

    @deprecated
    @property
    def duration_from_time(self):
        return min(self.baseline_from_timestamp, self.result_from_timestamp)

    @deprecated
    @property
    def duration_to_time(self):
        return max(self.baseline_to_timestamp, self.result_to_timestamp)

    @property
    def consumption_saving_rate(self):
        """
        The consumption saving rate.
        """
        return self.baseline_stage.mean_consumption_rate - \
            self.result_stage.mean_consumption_rate

    @property
    def cost_saving_rate(self):
        """
        The cost saving rate.
        """
        return self.baseline_stage.mean_cost_rate - \
            self.result_stage.mean_cost_rate

    @property
    def co2_saving_rate(self):
        return self.baseline_stage.mean_co2_rate - \
            self.result_stage.mean_co2_rate

    def _samples_to_data_set(self, measurement_point, samples, time_offset):
        """
        Converts a collection of samples to data set suitable for rendering
        (converting values, converting format of timestamp).

        @param measurement_point: The measurement point that these rate
        C{samples} belong to.

        @param samples: The rate samples to convert into a renderable data set.

        @param time_offset: To allow for time alligment of data sets from
        different periods of time, this offset will be subtracted from the
        timestamp in the C{samples}.
        """
        preferred_unit_converter = measurement_point.rate.\
            get_preferred_unit_converter()

        data_set = []
        for sample in samples:
            converted_value = float(
                preferred_unit_converter.extract_value(
                    sample.physical_quantity))
            data_set.append(
                [unix_timestamp(sample.timestamp - time_offset),
                 converted_value])
        return data_set

    def _consumption_samples_to_data_set(self, measurement_point, samples,
                                         time_offset):
        """
        Converts a collection of samples to data set suitable for rendering
        (converting values, converting format of timestamp).

        @param measurement_point: The measurement point that these rate
        C{samples} belong to.

        @param samples: The consumption samples to convert into a renderable
        data set.

        @param time_offset: To allow for time alligment of data sets from
        different periods of time, this offset will be subtracted from the
        timestamp in the C{samples}.
        """
        preferred_unit_converter = measurement_point.consumption.\
            get_preferred_unit_converter()

        data_set = []
        for sample in samples:
            converted_value = float(
                preferred_unit_converter.extract_value(
                    sample.physical_quantity))
            data_set.append(
                [unix_timestamp(sample.from_timestamp - time_offset),
                 converted_value])
        return data_set

    def _get_ticks(self):
        """
        Get ticks.

        @return: Returns a pair C{(ticks_unit, ticks_list)} where C{ticks_unit}
        is a localized unit for the ticks, and C{ticks_list} is a list of
        actual ticks; timestamp-counter pairs.

        @postcondition: The C{ticks_unit} is always representing either
        minutes, hours or days.

        @postcondition: The C{ticks_list} is constructed such that C{0 <
        len(ticks_list) <= 12} and the ticks are evenly distributed across the
        graph.
        """
        SHOW_HOURS = timedelta(hours=1)
        SHOW_DAYS = timedelta(days=1)
        SHOW_MONTHS = timedelta(days=30)
        SHOW_YEARS = timedelta(days=365)

        duration_time = max(
            self.baseline_to_timestamp - self.baseline_from_timestamp,
            self.result_to_timestamp - self.result_from_timestamp)

        resolution = self.get_sample_resolution()

        raw_tick_increment = (duration_time // 12)

        if duration_time < SHOW_HOURS:
            # Show minutes
            ticks_unit = _('minutes')
            tick_factor = (raw_tick_increment.seconds / 60) + 1
            tick_increment = timedelta(minutes=tick_factor)
        elif duration_time < SHOW_DAYS:
            # Show hours
            ticks_unit = _('hours')
            tick_factor = (raw_tick_increment.seconds / (60 * 60)) + 1
            tick_increment = timedelta(hours=tick_factor)
        elif duration_time < SHOW_MONTHS:
            # Show days
            ticks_unit = _('days')
            tick_factor = raw_tick_increment.days + 1
            tick_increment = timedelta(days=tick_factor)
        elif duration_time < SHOW_YEARS:
            # Show months
            ticks_unit = _('months')
            tick_factor = (raw_tick_increment.days / 30) + 1
            tick_increment = timedelta(days=30 * tick_factor)
        else:
            # Show years
            ticks_unit = _('years')
            tick_factor = (raw_tick_increment.days / 365) + 1
            tick_increment = timedelta(days=365 * tick_factor)

        ticks_list = []

        for i in itertools.count():
            if tick_increment * i > duration_time:
                break
            ticks_list.append(
                [
                    unix_timestamp(
                        self.customer.timezone.normalize(
                            condense.floor(
                                self.from_timestamp,
                                resolution,
                                self.customer.timezone) +
                            tick_increment * i)),
                    i * tick_factor])

        assert 0 < len(ticks_list) <= 12, '%r' % ticks_list
        return (ticks_unit, ticks_list)

    CONDENSE_TO_HOURS = timedelta(hours=12)
    CONDENSE_TO_DAYS = timedelta(days=12)
    CONDENSE_TO_MONTHS = timedelta(days=30 * 12)
    CONDENSE_TO_YEARS = timedelta(days=12 * 365)

    def get_sample_resolution(self):
        duration_time = max(
            self.baseline_to_timestamp - self.baseline_from_timestamp,
            self.result_to_timestamp - self.result_from_timestamp)
        return self._get_resolution(duration_time)

    def _get_resolution(self, duration_time):
        """
        Converts a C{timedelta} C{duration_time} to a L{RelativeTimeDelta}
        resolution.

        @postcondition: The result shall be no less M{1/1000} of
        C{duration_time}
        """
        if duration_time < self.CONDENSE_TO_HOURS:
            # Condense to minutes
            resolution = RelativeTimeDelta(minutes=1)
        elif duration_time < self.CONDENSE_TO_DAYS:
            # Condense to hours
            resolution = RelativeTimeDelta(hours=1)
        elif duration_time < self.CONDENSE_TO_MONTHS:
            # Condense to days
            resolution = RelativeTimeDelta(days=1)
        elif duration_time < self.CONDENSE_TO_YEARS:
            # Condense to months
            resolution = RelativeTimeDelta(months=1)
        else:
            # Condense to years
            resolution = RelativeTimeDelta(years=1)
        assert self.from_timestamp + (resolution * 1000) > \
            self.from_timestamp + duration_time
        return resolution

    def get_graph_data(self, measurement_point):
        """
        Get graph data for the given L{ConsumptionMeasurementPoint}
        C{measurement_point}.

        The rate curve of C{measurement_point} from C{stage_1} and C{stage_2}
        are alligned at the start of the graph.

        @return: Returns flotr2 compliant graph data.
        """

        STAGE_1_COLOR = '#A800F0'
        STAGE_2_COLOR = '#00A8F0'

        duration_time = max(
            self.baseline_to_timestamp - self.baseline_from_timestamp,
            self.result_to_timestamp - self.result_from_timestamp)

        xticks_unit, xticks_list = self._get_ticks()

        result = {
            "data": [],
            "options": {
                "colors": [],
                "xaxis": {
                    # Implementation note: tick at
                    # unix_timestamp(self.from_timestamp) is never
                    # displayed.
                    "ticks": xticks_list,
                    "min": unix_timestamp(self.from_timestamp),
                    "max": unix_timestamp(self.from_timestamp +
                                          duration_time),
                    'title': xticks_unit,
                },
                "yaxis": {
                    "title": (
                        measurement_point.rate.get_preferred_unit_converter().
                        get_display_unit()),
                }
            }
        }

        include_stage_1 = self.baseline_measurement_points.filter(
            id=measurement_point.id).exists()
        include_stage_2 = self.result_measurement_points.filter(
            id=measurement_point.id).exists()

        resolution = self._get_resolution(duration_time)

        if include_stage_1:
            # calculate stage 1 data
            result['data'].append(
                {
                    'data': self._samples_to_data_set(
                        measurement_point,
                        measurement_point.rate.get_condensed_samples(
                            condense.floor(
                                self.baseline_from_timestamp, resolution,
                                self.customer.timezone),
                            resolution,
                            condense.floor(
                                self.baseline_to_timestamp, resolution,
                                self.customer.timezone)),
                        self.baseline_from_timestamp - self.from_timestamp),
                    'lines': {
                        'show': True,
                    },
                    'label': _('Baseline'),
                })
            result['options']['colors'].append(STAGE_1_COLOR)

        if include_stage_2:
            # calculate stage 2 data
            result['data'].append(
                {
                    'data': self._samples_to_data_set(
                        measurement_point,
                        measurement_point.rate.get_condensed_samples(
                            condense.floor(
                                self.result_from_timestamp, resolution,
                                self.customer.timezone),
                            resolution,
                            condense.floor(
                                self.result_to_timestamp, resolution,
                                self.customer.timezone)),
                        self.result_from_timestamp - self.from_timestamp),
                    'lines': {
                        'show': True,
                    },
                    'label': _('Result'),
                })
            result['options']['colors'].append(STAGE_2_COLOR)

        return result

    def get_consumption_graph_data(self, measurement_point):
        """
        Get consumption graph data for the given L{ConsumptionMeasurementPoint}
        C{measurement_point}.

        The consumption bars of C{measurement_point} from C{stage_1} and
        C{stage_2} are alligned at the start of the graph.

        @return: Returns flotr2 compliant graph data.
        """

        STAGE_1_COLOR = '#A800F0'
        STAGE_2_COLOR = '#00A8F0'

        duration_time = max(
            self.baseline_to_timestamp - self.baseline_from_timestamp,
            self.result_to_timestamp - self.result_from_timestamp)

        xticks_unit, xticks_list = self._get_ticks()

        result = {
            "data": [],
            "options": {
                "colors": [],
                "xaxis": {
                    # Implementation note: tick at
                    # unix_timestamp(self.from_timestamp) is never
                    # displayed.
                    "ticks": xticks_list,
                    "min": unix_timestamp(self.from_timestamp),
                    "max": unix_timestamp(self.from_timestamp +
                                          duration_time),
                    'title': xticks_unit,
                },
                "yaxis": {
                    "title": (
                        measurement_point.consumption.
                        get_preferred_unit_converter().get_display_unit()),
                }
            }
        }

        include_stage_1 = self.baseline_stage.measurement_points.filter(
            id=measurement_point.id).exists()
        include_stage_2 = self.result_stage.measurement_points.filter(
            id=measurement_point.id).exists()

        resolution = self._get_resolution(duration_time)

        if include_stage_1:
            # calculate stage 1 data
            result['data'].append(
                {
                    'data': self._consumption_samples_to_data_set(
                        measurement_point,
                        measurement_point.consumption.get_condensed_samples(
                            condense.floor(
                                self.baseline_stage.from_timestamp, resolution,
                                self.customer.timezone),
                            resolution,
                            condense.ceil(
                                self.baseline_stage.to_timestamp, resolution,
                                self.customer.timezone)),
                        condense.floor(
                            self.baseline_stage.from_timestamp,
                            resolution,
                            self.customer.timezone) -
                        condense.floor(
                            self.from_timestamp,
                            resolution,
                            self.customer.timezone)),
                    'bars': {
                        'show': True,
                    },
                    'label': _('Baseline'),
                })
            result['options']['colors'].append(STAGE_1_COLOR)

        if include_stage_2:
            # calculate stage 2 data
            result['data'].append(
                {
                    'data': self._consumption_samples_to_data_set(
                        measurement_point,
                        measurement_point.consumption.get_condensed_samples(
                            condense.floor(
                                self.result_stage.from_timestamp, resolution,
                                self.customer.timezone),
                            resolution,
                            condense.ceil(
                                self.result_stage.to_timestamp, resolution,
                                self.customer.timezone)),
                        condense.floor(
                            self.result_stage.from_timestamp,
                            resolution,
                            self.customer.timezone) -
                        condense.floor(
                            self.from_timestamp,
                            resolution,
                            self.customer.timezone)),
                    'bars': {
                        'show': True,
                    },
                    'label': _('Result'),
                })
            result['options']['colors'].append(STAGE_2_COLOR)

        return result

    def get_preferred_consumption_unit_converter(self):
        return get_preferred_unit_converter(
            DataRoleField.CONSUMPTION, self.utility_type,
            customer=self.customer)

    def get_consumption_unit_display(self):
        """
        @deprecated: Method is redundant -- replace invocations with
        implementation.
        """
        return self.get_preferred_consumption_unit_converter().\
            get_display_unit()

    def get_co2_emissions_unit_display(self):
        return get_preferred_unit_converter(
            DataRoleField.CO2, customer=self.customer).get_display_unit()

    @cached_property
    def _now(self):
        return datetime.now(pytz.utc)

    @cached_property
    def baseline_period_completed(self):
        """
        C{True} if base-line period is complete, C{False} otherwise.
        """
        if self.from_timestamp:
            return self.baseline_to_timestamp <= self._now
        else:
            return False

    @cached_property
    def result_period_completed(self):
        """
        C{True} if result period is complete, C{False} otherwise.
        """
        if self.to_timestamp:
            return self.result_to_timestamp <= self._now
        else:
            return False

    @cached_property
    def project_completed(self):
        """
        C{True} if both base-line period and result period are complete,
        C{False} otherwise.
        """
        return self.baseline_period_completed and self.result_period_completed

    @cached_property
    def baseline_annual_consumption(self):
        """
        Base-line annual consumption.

        @return: If the base-line period is complete, the measured base-line
        yearly consumption is returned, otherwise the
        C{estimated_yearly_consumption_before} is returned.
        """
        ONE_YEAR = PhysicalQuantity(365, 'day')
        if self.baseline_period_completed:
            return self.get_preferred_consumption_unit_converter().\
                extract_value(
                    self.baseline_stage.mean_consumption_rate * ONE_YEAR)
        else:
            return self.estimated_yearly_consumption_before

    @cached_property
    def baseline_annual_costs(self):
        """
        Base-line annual cost.

        @return: If the base-line period is complete and
        C{include_measured_costs} is C{True}, the measured base-line yearly
        costs are returned, otherwise the
        C{estimated_yearly_consumption_costs_before} is returned.
        """
        ONE_YEAR = PhysicalQuantity(365, 'day')
        if self.baseline_period_completed and self.include_measured_costs and \
                not self.cost_currency_conflicts():
            return (self.baseline_stage.mean_cost_rate * ONE_YEAR).convert(
                self.customer.currency_unit)
        else:
            return self.estimated_yearly_consumption_costs_before

    @cached_property
    def annual_cost_savings(self):
        """
        Annual cost savings.

        @return: If the project is completed, the measured yearly cost savings,
        additional yearly cost savings and yearly investment costs are included
        in the result.  Otherwise the
        C{expected_savings_in_yearly_total_costs} is returned.
        """
        if self.project_completed:
            return self.resulting_annual_cost_savings().convert(
                self.customer.currency_unit)
        else:
            return self.expected_savings_in_yearly_total_costs

    @cached_property
    def payback_period_years(self):
        """
        Payback period for this project in years.

        If this is undefined, C{None} is returned.
        """
        return payback_period_years(Fraction(self.investment),
                                    Fraction(self.subsidy or 0),
                                    Fraction(self.annual_cost_savings))

    @cached_property
    def expected_payback_period_years(self):
        """
        Estimated payback period for this project in years.

        If this is undefined, C{None} is returned.
        """
        return payback_period_years(
            Fraction(self.investment),
            Fraction(self.subsidy or 0),
            Fraction(self.expected_savings_in_yearly_total_costs))


MeanRateResult = namedtuple(
    'MeanRateResult', ['physical_quantity', 'extrapolated_mps'])


class Stage(object):
    def __init__(self, benchmarkproject):
        self.benchmarkproject = benchmarkproject

    @property
    def currency_unit(self):
        return self.benchmarkproject.customer.currency_unit

    @cached_property
    def _measurement_points(self):
        return self.measurement_points.all()

    def _mean_rate(self, accumulation_attribute_name, accumulation_unit):
        """
        Calculate the total accumulation of this stage normalized with the
        duration of this stage.

        @param accumulation_attribute_name: The L{MeasurementPoint} attribute
        name of the accumulation.

        @param accumulation_unit: The unit of which to accumulate.

        @return: Returns a PhysicalQuantity holding the mean rate with the
        given unit.

        @postcondition: C{report_%s_extrapolated} has been called for all the
        measurement point for which the accumulation sample has been
        extrapolated.  Here C{%s} is replaced by the value of the
        C{accumulation_attribute_name} argument.
        """
        total = PhysicalQuantity(0, accumulation_unit)

        extrapolated_mps = []

        time_now = datetime.now(pytz.utc)
        # round from_timestamp down to nearest 5 minutes
        from_timestamp = self.from_timestamp.replace(
            minute=self.from_timestamp.minute - self.from_timestamp.minute % 5,
            second=0,
            microsecond=0)
        # select to_timestamp and round up to nearest 5 minutes
        to_timestamp = min(self.to_timestamp, time_now)
        to_timestamp = to_timestamp.replace(
            minute=(to_timestamp.minute / 5) * 5,
            second=0,
            microsecond=0)
        if from_timestamp < time_now:
            for mp in [mp.subclass_instance for mp in self._measurement_points
                       if getattr(mp, accumulation_attribute_name, None)]:
                development = getattr(
                    mp, accumulation_attribute_name).calculate_development(
                    from_timestamp, to_timestamp)
                if development is not None:
                    if development.extrapolated:
                        extrapolated_mps.append(mp)
                    total += development.physical_quantity
        return MeanRateResult(
            total / PhysicalQuantity(
                (to_timestamp - from_timestamp).total_seconds(), 'second'),
            extrapolated_mps)

    @cached_property
    def mean_consumption_rate(self):
        """
        The mean consumption rate is the total consumption of this stage
        normalized with the duration of this stage.
        """
        return self._mean_rate(
            'consumption', default_unit_for_data_series(
                DataRoleField.CONSUMPTION,
                self.benchmarkproject.utility_type)).physical_quantity

    @cached_property
    def _mean_cost_rate(self):
        """
        The mean cost rate is the total cost of this stage normalized with the
        duration of this stage.
        """
        if not self.benchmarkproject.cost_currency_conflicts():
            return self._mean_rate('cost', self.currency_unit)
        else:
            return MeanRateResult(
                PhysicalQuantity(0, self.currency_unit) /
                PhysicalQuantity(1, 'second'),
                [])

    @property
    def mean_cost_rate(self):
        return self._mean_cost_rate.physical_quantity

    @cached_property
    def mean_co2_rate(self):
        """
        The mean CO2 rate is the total CO2 of this stage normalized with the
        duration of this stage.
        """
        return self._mean_rate('co2calculation', 'gram').physical_quantity

    @property
    def tariff_domain_warning_measurement_point_ids(self):
        # technically, the result also depends on consumptions being
        # extrapolated.
        return [mp.id for mp in self._mean_cost_rate.extrapolated_mps]

    def tariff_domain_warning(self,
                              tariff_domain_warning_measurement_point_ids):
        """
        Returns a warning text if any of the MP's in this stage
        has a tariff assigned to it, which is not covering the
        consumption domain.

        @param tariff_domain_warning_measurement_point_ids: A list of ids of
        ConsumptionMeasurementPoints whose tariff domain does not cover this
        stage.
        """
        if tariff_domain_warning_measurement_point_ids:
            mps = [
                mp.subclass_instance.name_plain for mp in
                ConsumptionMeasurementPoint.objects.filter(
                    id__in=tariff_domain_warning_measurement_point_ids)]

            return _(
                'Tariff for {mps} does not cover '
                'the duration of {stage}').format(
                mps=', '.join(mps), stage=self.get_role_display())


class BaselineStage(Stage):
    @cached_property
    def from_timestamp(self):
        return self.benchmarkproject.baseline_from_timestamp

    @cached_property
    def to_timestamp(self):
        return self.benchmarkproject.baseline_to_timestamp

    @property
    def measurement_points(self):
        return self.benchmarkproject.baseline_measurement_points.all()

    def get_role_display(self):
        return _('Baseline')


class ResultStage(Stage):
    @cached_property
    def from_timestamp(self):
        return self.benchmarkproject.result_from_timestamp

    @cached_property
    def to_timestamp(self):
        return self.benchmarkproject.result_to_timestamp

    @property
    def measurement_points(self):
        return self.benchmarkproject.result_measurement_points.all()

    def get_role_display(self):
        return _('Result')


class AdditionalSaving(EncryptedModel):
    """
    C{AdditionalSaving} of a C{Project} Stores supplements to annual savings
    """
    project = models.ForeignKey(BenchmarkProject, verbose_name=_('project'))
    description = EncryptedCharField(_('description'), max_length=50)
    before_energy = models.DecimalField(
        _('energy before'),
        blank=True, null=True,
        max_digits=19, decimal_places=2)
    after_energy = models.DecimalField(
        _('energy after'),
        blank=True, null=True,
        max_digits=19, decimal_places=2)
    before_cost = models.DecimalField(
        _('cost before'),
        blank=True, null=True,
        max_digits=19, decimal_places=2)
    after_cost = models.DecimalField(
        _('cost after'),
        blank=True, null=True,
        max_digits=19, decimal_places=2)
    before_co2 = models.DecimalField(
        _('CO² before'),
        blank=True, null=True,
        max_digits=19, decimal_places=6)
    after_co2 = models.DecimalField(
        _('CO² after'),
        blank=True, null=True,
        max_digits=19, decimal_places=6)
    energy_unit = models.CharField(
        _('unit for energy'),
        editable=False, max_length=50, default='kilowatt*hour')

    def diff_energy(self):
        return (self.before_energy or 0) - (self.after_energy or 0)

    def diff_cost(self):
        return (self.before_cost or 0) - (self.after_cost or 0)

    def diff_co2(self):
        return (self.before_co2 or 0) - (self.after_co2 or 0)

    def get_encryption_id(self):
        if self.project_id:
            return (Customer, self.project.customer_id)
        else:
            return None


def validate_positive(value):
    if value is not None and value <= 0:
        raise ValidationError(
            _(u'Must be positive.'))


class Cost(EncryptedModel):
    """
    C{Cost} of a C{Project} Stores the cost of the project. Eg. costs
    for Grid Manager solution, installation, replacement of machinery, etc.

    When both C{amortization_period} and C{interest_rate} are not C{None} we
    are in finance mode.

    @invariant: When not in finance mode, both C{amortization_period} and
    C{interrest_rate} must be C{None}.

    @invariant: C{scrap_value} may only be set when in finance mode.
    """
    project = models.ForeignKey(BenchmarkProject, verbose_name=_('project'))
    description = EncryptedCharField(max_length=50)
    cost = models.DecimalField(
        _('cost'), max_digits=19, decimal_places=2)
    amortization_period = models.IntegerField(
        _('amortization period in months'),
        null=True, blank=True,
        validators=[validate_positive])
    interest_rate = models.DecimalField(
        _('interest rate'),
        null=True, blank=True,
        max_digits=19, decimal_places=2,
        validators=[validate_positive])

    # scrap value is used in some leasing agreements.
    scrap_value = models.DecimalField(
        _('scrap value'),
        null=True, blank=True,
        max_digits=19, decimal_places=2)

    def save(self, *args, **kwargs):
        self._assert_invariants()
        super(Cost, self).save(*args, **kwargs)

    def _finance_mode(self):
        """
        C{True} when both C{amortization_period} and C{interrest_rate} are
        C{None}.
        """
        return self.amortization_period is not None and \
            self.interest_rate is not None

    def _assert_invariants(self):
        """
        Assert invariants.
        """
        if not self._finance_mode():
            assert self.amortization_period is None
            assert self.interest_rate is None

        if self.scrap_value is not None:
            assert self._finance_mode()

    def clean(self):
        super(Cost, self).clean()
        if self.amortization_period and not self.interest_rate:
            raise ValidationError(
                _(u'Interest rate must be set when amortization period is '
                  u'non-zero.'))

        if self.interest_rate and not self.amortization_period:
            raise ValidationError(
                _(u'Amortization period must be non-zero when interest '
                  u'rate is set.'))

        if self.scrap_value and not self.amortization_period and \
                not self.interest_rate:
            raise ValidationError(
                _(u'Scrap value requires amortization period and interest '
                  u'rate to be both non-zero.'))

        self._assert_invariants()

    def get_total_costs(self):
        """
        Total costs

        @return: Returns a Fraction.  In finance mode the result will include
        interests, otherwise the bare costs are returned.
        """
        self._assert_invariants()
        if self.amortization_period is None:
            return Fraction(self.cost)
        else:
            return Fraction(self.amortization_period * self.monthly_payment())

    def monthly_payment(self):
        """
        When the C{Cost} is financed, there will be a monthly payment.

        @precondition: This C{Cost} instance is in finance mode.
        """
        self._assert_invariants()
        assert self._finance_mode()

        PERCENT = 1.0 / 100
        ANNUAL_TO_MONTHLY = 1.0 / 12
        c = float(self.cost)
        r = float(self.interest_rate) * PERCENT * ANNUAL_TO_MONTHLY
        n = self.amortization_period

        scrap = float(self.scrap_value)

        # formula requires interest rate being non-zero and amortization
        # period being positive.
        assert r != 0
        assert n > 0

        # see doc/rje-notes/annuity-formula.jpeg for how to derive this
        # formula without the scrap value.  Scrap value may be seen as the
        # final payment, and the following formula emerges.  When scrap
        # value is zero, the normal annuity formula applies.  The result of
        # this formula is a single payment.
        return (c * r * (1 + r) ** n - scrap * r) / ((1 + r) ** n - 1)

    def get_encryption_id(self):
        if self.project_id:
            return (Customer, self.project.customer_id)
        else:
            return None
