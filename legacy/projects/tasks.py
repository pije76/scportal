# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from fractions import Fraction

from celery import shared_task
from celery import Task

from legacy.energy_use_reports.tasks import TaskProgressMixin
from gridplatform.customers.models import Customer
from gridplatform.trackuser.tasks import trackuser_task
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_user

from .models import BenchmarkProject
from .models import payback_period_years


@trackuser_task
@shared_task(
    timelimit=1860, soft_time_limit=1800,
    name='legacy.projects.tasks.AnnualSavingsPotentialReportTask')
class AnnualSavingsPotentialReportTask(TaskProgressMixin, Task):
    def run(self, data):
        self.update_state(
            state='PROGRESS',
            meta={
                'task_user_id': get_user().id,
                'current': 0,
                'total': 0
            }
        )

        self.PROGRESS_TOTAL = len(data['projects'])
        self.progress = 0

        total_expected_annual_cost_savings = Fraction(0)
        total_subsidy = Fraction(0)
        total_investment = Fraction(0)
        for project in BenchmarkProject.objects.filter(
                id__in=data['projects'].keys()):
            expected_annual_cost_savings = Fraction(
                project.expected_savings_in_yearly_total_costs or 0)
            subsidy = Fraction(project.subsidy or 0)
            investment = Fraction(project.investment)

            total_expected_annual_cost_savings += expected_annual_cost_savings
            total_subsidy += subsidy
            total_investment += investment

            data['projects'][project.id]['baseline_annual_consumption'] = \
                project.baseline_annual_consumption
            data['projects'][project.id]['expected_annual_cost_savings'] = \
                expected_annual_cost_savings
            data['projects'][project.id]['baseline_annual_costs'] = \
                project.baseline_annual_costs
            data['projects'][project.id]['subsidy'] = subsidy
            data['projects'][project.id]['investment'] = investment
            data['projects'][project.id]['expected_payback_period_years'] = \
                project.expected_payback_period_years
            self.tick_progress()

        total_expected_payback_period = payback_period_years(
            total_investment,
            total_subsidy,
            total_expected_annual_cost_savings)

        data['total_expected_annual_cost_savings'] = \
            total_expected_annual_cost_savings
        data['total_subsidy'] = total_subsidy
        data['total_investment'] = total_investment
        data['total_expected_payback_period'] = total_expected_payback_period
        data['currency_unit'] = \
            Customer.objects.get(id=get_customer().id).\
            get_currency_unit_display()
        return data
