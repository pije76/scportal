# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from django.utils.translation import ugettext as _
from django.db.models import Q

from celery import shared_task
from celery import Task

from gridplatform.trackuser import get_user
from gridplatform.trackuser.tasks import trackuser_task
from gridplatform.utils.unitconversion import PhysicalQuantity
from legacy.legacy_utils import get_customer_preferred_unit_attribute_name
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.proxies import ConsumptionMeasurementPoint
from legacy.projects.models import BenchmarkProject


# Softly kill using exception after 30 minutes. Kill for real after 31 minutes.
@trackuser_task
@shared_task(
    time_limit=1860, soft_time_limit=1800,
    name='legacy.display_projects.tasks.ProjectReportTask')
class ProjectReportTask(Task):
    def report_progress(self, progress, total):
        self.update_state(
            state='PROGRESS',
            meta={
                'task_user_id': get_user().id,
                'current': progress,
                'total': total,
            }
        )

    def run(self, data):
        PROGRESS_TOTAL = 6
        project_id = data['project']
        # DB: BenchmarkProject by ID; should be cheap
        project = BenchmarkProject.objects.get(id=project_id)
        self.report_progress(1, PROGRESS_TOTAL)
        consumption_unit_attribute_name = \
            get_customer_preferred_unit_attribute_name(
                project.customer, DataRoleField.CONSUMPTION,
                project.utility_type)
        consumption_unit_display_attribute_name = \
            'get_{consumption_unit_attribute_name}_display'.format(
                consumption_unit_attribute_name=consumption_unit_attribute_name)  # noqa
        consumption_unit = getattr(project.customer,
                                   consumption_unit_attribute_name)
        consumption_unit_display = getattr(
            project.customer, consumption_unit_display_attribute_name)()
        cost_unit = project.customer.currency_unit
        cost_unit_display = project.customer.get_currency_unit_display()
        co2_unit = 'tonne'
        co2_unit_display = unicode(_('CO₂ (ton)'))

        # DB: obtaining a bunch of dataseries, calling calculate_development()
        # on them...
        project_savings = {}
        # Call sequences until DB queries:
        # project_consumption_savings -> self.yearly_consumption_savings ->
        # yearly_measured_consumption_savings -> consumption_saving_rate ->
        # baseline_stage.mean_consumption_rate -> ...
        #
        # project_consumption_savings -> self.yearly_consumption_savings ->
        # yearly_measured_consumption_savings -> consumption_saving_rate ->
        # result_stage.mean_consumption_rate ->
        # result_measurement_points.all().all()/subclass_instance/
        # consumption.calculate_development()
        #
        # project_consumption_savings -> self.yearly_consumption_savings ->
        # yearly_additional_consumption_savings ->
        # yearly_additional_consumption -> additionalsaving_set.all()
        project_savings['consumption'] = float(
            project.project_consumption_savings().convert(consumption_unit))
        self.report_progress(2, PROGRESS_TOTAL)
        project_savings['cost'] = \
            float(project.project_cost_savings().convert(cost_unit))
        self.report_progress(3, PROGRESS_TOTAL)
        project_savings['co2'] = \
            float(project.project_co2_savings().convert(co2_unit))
        self.report_progress(4, PROGRESS_TOTAL)
        # Just reads fields on the BenchmarkProject instance
        expected = {
            'consumption': (
                project.expected_savings_in_yearly_consumption_after /
                12 * project.runtime),
            'cost': (project.expected_savings_in_yearly_total_costs /
                     12 * project.runtime),
            'co2': (project.expected_reduction_in_yearly_co2_emissions /
                    12 * project.runtime),
        }

        goal_diff = {}
        try:
            goal_diff['consumption_pct'] = (
                (project_savings['consumption'] -
                 float(expected['consumption'])) * 100 /
                float(expected['consumption']))
        except:
            goal_diff['consumption_pct'] = None

        try:
            goal_diff['cost_pct'] = ((project_savings['cost'] -
                                      float(expected['cost'])) * 100 /
                                     float(expected['cost']))
        except:
            goal_diff['cost_pct'] = None

        try:
            goal_diff['co2_pct'] = ((project_savings['co2'] -
                                     float(expected['co2'])) * 100 /
                                    float(expected['co2']))
        except:
            goal_diff['co2_pct'] = None

        # Uses @cached_property for mean_consumption_rate, mean_cost_rate,
        # mean_co2_rate; so avoids new queries for that...
        yearly_stage1 = {
            'consumption': float((
                (project.baseline_stage.mean_consumption_rate *
                 PhysicalQuantity(365, 'day'))).convert(consumption_unit)),
            'cost': float((
                (project.baseline_stage.mean_cost_rate * PhysicalQuantity(
                    365, 'day'))).convert(cost_unit)),
            'co2': float(
                (project.baseline_stage.mean_co2_rate * PhysicalQuantity(
                    365, 'day')).convert(co2_unit)),
        }
        yearly_stage2 = {
            'consumption': float((
                (project.result_stage.mean_consumption_rate * PhysicalQuantity(
                    365, 'day'))).convert(consumption_unit)),
            'cost': float((
                (project.result_stage.mean_cost_rate * PhysicalQuantity(
                    365, 'day'))).convert(cost_unit)),
            'co2': float(
                (project.result_stage.mean_co2_rate * PhysicalQuantity(
                    365, 'day')).convert(co2_unit)),
        }
        # NTS: "yearly" means "yearly measured consumption"; "total" means
        # "yearly measured consumption + additional consumption" DB: repeats
        # additionalsaving_set.all() query for consumption, cost, co2
        total_stage1 = {
            'consumption': float(
                (
                    (
                        project.baseline_stage.mean_consumption_rate *
                        PhysicalQuantity(365, 'day')) +
                    project.yearly_additional_consumption()['before']).
                convert(consumption_unit)),
            'cost': float(
                (
                    (
                        project.baseline_stage.mean_cost_rate *
                        PhysicalQuantity(365, 'day')) +
                    project.yearly_additional_cost()['before']).
                convert(cost_unit)),
            'co2': float(
                (
                    project.baseline_stage.mean_co2_rate * PhysicalQuantity(
                        365, 'day') +
                    project.yearly_additional_co2()['before']).
                convert(co2_unit)),
        }
        # DB: repeats additionalsaving_set.all() query for consumption, cost,
        # co2
        total_stage2 = {
            'consumption': float(
                (
                    (
                        project.result_stage.mean_consumption_rate *
                        PhysicalQuantity(365, 'day')) +
                    project.yearly_additional_consumption()['after']).
                convert(consumption_unit)),
            'cost': float(
                (
                    (
                        project.result_stage.mean_cost_rate * PhysicalQuantity(
                            365, 'day')) +
                    project.yearly_additional_cost()['after'] +
                    project.average_yearly_project_costs()).convert(
                    cost_unit)),
            'co2': float(
                (
                    project.result_stage.mean_co2_rate * PhysicalQuantity(
                        365, 'day') +
                    project.yearly_additional_co2()['after']).convert(
                    co2_unit)),
        }
        self.report_progress(5, PROGRESS_TOTAL)
        measurement_points = []
        # DB: measurementpoints that fulfill one or the other criteria...
        for mp in ConsumptionMeasurementPoint.objects.filter(
                Q(benchmarkproject_baseline_member__id=project.id) |
                Q(benchmarkproject_result_member__id=project.id)).distinct():
            rate_data = None
            if mp.rate is not None:
                rate_data = project.get_graph_data(mp)
            # DB: unsurprisingly, two queries per MP to determine which of the
            # criteria put it in the set to be processed...
            # DB: mp.consumption.get_condensed_samples() for stage1
            # DB: mp.consumption.get_condensed_samples() for stage2
            measurement_points.append(
                {
                    'id': mp.id,
                    'graph_data': rate_data,
                    'consumption_graph_data': (
                        project.get_consumption_graph_data(mp)),
                })
        self.report_progress(6, PROGRESS_TOTAL)
        return {
            'project_id': project.id,
            # NTS: "estimated" are fields from BenchmarkProject instance
            'estimated': {
                'consumption': project.estimated_yearly_consumption_before,
                'cost': project.estimated_yearly_consumption_costs_before,
                'co2': project.estimated_co2_emissions_before,
            },
            'expected': expected,
            'goal_diff': goal_diff,
            # DB: additionalsaving_set.all() repeated for each of consumption,
            # consumption_pct, cost, cost_pct, co2, co2_pct
            # DB: ... actually, additionalsaving_set.all() repeated once more
            # for each of the percent-variants...?
            # NTS: yearly_measured_... are eventually based on @cached_property
            # members on the Stage objects
            'yearly_savings': {
                'consumption': float(
                    project.yearly_consumption_savings().convert(
                        consumption_unit)),
                'consumption_pct': project.yearly_consumption_savings_pct(),
                'cost': float(project.resulting_annual_cost_savings().convert(
                    cost_unit)),
                'cost_pct': project.resulting_annual_cost_savings_pct(),
                'co2': float(project.yearly_co2_savings().convert(co2_unit)),
                'co2_pct': project.yearly_co2_savings_pct(),
            },
            'unit': {
                'consumption': consumption_unit_display,
                'cost': cost_unit_display,
                'co2': co2_unit_display,
            },
            'project_savings': project_savings,
            'yearly_stage1': yearly_stage1,
            'yearly_stage2': yearly_stage2,
            'yearly_stage_diff': {
                'consumption': yearly_stage1['consumption'] -
                yearly_stage2['consumption'],
                'cost': yearly_stage1['cost'] - yearly_stage2['cost'],
                'co2': yearly_stage1['co2'] - yearly_stage2['co2'],
            },
            'total_stage1': total_stage1,
            'total_stage2': total_stage2,
            'project_costs_results': {
                # DB: cost_set.all() --- but via @cached_property investment,
                # so only once...
                'monthly': float(
                    project.average_monthly_project_costs().convert(
                        cost_unit)),
                'yearly': float(
                    project.average_yearly_project_costs().convert(cost_unit)),
            },
            'measurement_points': measurement_points,
            'baseline_tariff_domain_warning_measurement_point_ids':
                project.baseline_stage.tariff_domain_warning_measurement_point_ids,  # noqa
            'result_tariff_domain_warning_measurement_point_ids':
                project.result_stage.tariff_domain_warning_measurement_point_ids,  # noqa
        }
