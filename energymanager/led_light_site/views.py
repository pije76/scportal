# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import calendar

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext_lazy
from django import forms
from django.core.urlresolvers import reverse
from django.db.models.fields import BLANK_CHOICE_DASH

from gridplatform.utils import generic_views
from gridplatform.utils import units
from gridplatform.utils.breadcrumbs import Breadcrumb
from gridplatform.utils.breadcrumbs import Breadcrumbs
from gridplatform.utils.views import ChooseCustomerBase
from gridplatform.utils.views import CustomerInKwargsMixin
from gridplatform.utils.views import CustomerListMixin
from gridplatform.utils.views import CustomerViewBase
from gridplatform.utils.views import HomeViewBase
from gridplatform.customers.models import Customer
from gridplatform.utils.forms import YearWeekPeriodForm
from gridplatform.utils.forms import this_week_initial_values


from energymanager.energy_projects.models import LedLightProject


class HomeView(HomeViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'led_light_site:dashboard',
            kwargs={'customer_id': customer_id})

    def get_choose_customer_url(self):
        return reverse(
            'led_light_site:choose-customer')


class ChooseCustomer(ChooseCustomerBase):
    template_name = 'led_light_site/choose_customer.html'


class CustomerView(CustomerViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'led_light_site:dashboard',
            kwargs={'customer_id': customer_id})


class DashboardDetailView(
        CustomerListMixin, generic_views.DetailView):
    model = Customer
    template_name = \
        'led_light_site/dashboard.html'

    def get_breadcrumbs(self):
        return (
            (_('Dashboard'), ''),
        )

    def get_object(self, queryset=None):
        return self.model.objects.get(pk=self.kwargs['customer_id'])

    def get_context_data(self, **kwargs):
        context = super(DashboardDetailView, self).get_context_data(**kwargs)

        projects = self.object.ledlightproject_set.all()
        projects_width_savings = []

        total_saved = None
        total_previous_price = None
        total_led_price = None

        year = int(self.request.GET.get(
            'year', datetime.datetime.today().year))
        month_number = int(self.request.GET.get(
            'month_number', datetime.datetime.today().month))

        from_time = None
        to_time = None

        month_options = (
            '...',
            _('January'),
            _('February'),
            _('March'),
            _('April'),
            _('May'),
            _('June'),
            _('Juli'),
            _('August'),
            _('September'),
            _('October'),
            _('November'),
            _('December'),
        )

        if month_number == 0:
            from_time = datetime.datetime(year, 1, 1, 0, 0, 0).replace(tzinfo=self.object.timezone)
            to_time = datetime.datetime(year + 1, 1, 1, 0, 0, 0).replace(tzinfo=self.object.timezone)
        else:
            from_time = datetime.datetime(year, month_number, 1, 0, 0, 0).replace(tzinfo=self.object.timezone)
            to_time = datetime.datetime(
                year, month_number, calendar.monthrange(
                    year, month_number)[1], 23, 59, 59).replace(tzinfo=self.object.timezone) + datetime.timedelta(
                        seconds=1)

        for project in projects:
            previous_price = project.calculated_previous_price(
                from_time=from_time, to_time=to_time)

            led_price = project.measured_price(
                from_time=from_time, to_time=to_time)

            saved = project.calculate_savings(
                from_time=from_time, to_time=to_time)
            if saved:
                if total_saved:
                    total_saved += saved
                    total_previous_price += previous_price
                    total_led_price += led_price
                else:
                    total_previous_price = previous_price
                    total_led_price = led_price
                    total_saved = saved

                projects_width_savings.append({
                    'name': project.name_plain,
                    'saved': saved,
                    'previous_price': previous_price,
                    'led_price': led_price
                })
            else:
                projects_width_savings.append({
                    'name': project.name_plain,
                    'saved': '-',
                    'previous_price': '-',
                    'led_price': '-'
                })

        context['year'] = year
        context['month_number'] = month_number
        context['month'] = month_options[month_number]
        context['total_saved'] = total_saved
        context['total_previous_price'] = total_previous_price
        context['total_led_price'] = total_led_price
        context['projects'] = projects_width_savings
        context['chart_form'] = YearWeekPeriodForm(
                this_week_initial_values())
        return context


class DashboardBurnDetailView(
        CustomerListMixin, generic_views.DetailView):
    model = Customer
    template_name = \
        'led_light_site/dashboard_burn.html'

    def get_breadcrumbs(self):
        return (
            (_('Dashboard Burn Hours'), ''),
        )

    def get_object(self, queryset=None):
        return self.model.objects.get(pk=self.kwargs['customer_id'])

    def get_context_data(self, **kwargs):
        context = super(
            DashboardBurnDetailView, self).get_context_data(**kwargs)

        projects = self.object.ledlightproject_set.all()
        projects_width_savings = []

        total_burned = None

        year = int(self.request.GET.get(
            'year', datetime.datetime.today().year))
        month_number = int(self.request.GET.get(
            'month_number', datetime.datetime.today().month))

        from_time = None
        to_time = None

        month_options = (
            '...',
            _('January'),
            _('February'),
            _('March'),
            _('April'),
            _('May'),
            _('June'),
            _('Juli'),
            _('August'),
            _('September'),
            _('October'),
            _('November'),
            _('December'),
        )

        if month_number == 0:
            from_time = datetime.datetime(year, 1, 1, 0, 0, 0).replace(
                tzinfo=self.object.timezone)
            to_time = datetime.datetime(year + 1, 1, 1, 0, 0, 0).replace(
                tzinfo=self.object.timezone)
        else:
            from_time = datetime.datetime(
                year, month_number, 1, 0, 0, 0).replace(
                    tzinfo=self.object.timezone)
            to_time = datetime.datetime(
                year, month_number, calendar.monthrange(
                    year, month_number)[1], 23, 59, 59).replace(
                        tzinfo=self.object.timezone) + datetime.timedelta(
                        seconds=1)

        for project in projects:
            burned = project.calculate_burn_hours(
                from_time=from_time, to_time=to_time)

            if burned:
                if total_burned:
                    total_burned += burned
                else:
                    total_burned = burned

                projects_width_savings.append({
                    'name': project.name_plain,
                    'burned': burned,
                })
            else:
                projects_width_savings.append({
                    'name': project.name_plain,
                    'burned': '-',
                })

        context['year'] = year
        context['month_number'] = month_number
        context['month'] = month_options[month_number]
        context['total_burned'] = total_burned
        context['projects'] = projects_width_savings
        return context


class LedLightProjectList(CustomerListMixin, generic_views.TemplateView):
    template_name = 'led_light_site/led_light_project_list.html'

    @staticmethod
    def build_breadcrumbs(customer_id):
        return Breadcrumbs() + Breadcrumb(
            _('Led Light Projects'),
            reverse(
                'led_light_site_projects:led-light-project-list',
                kwargs={'customer_id': customer_id}))

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id)


class LedLightProjectListContentView(
        CustomerListMixin,
        generic_views.ListView):
    search_fields = ['name_plain', ]
    sort_fields = ['name_plain', ]
    model = LedLightProject
    paginate_by = 100
    template_name = 'led_light_site/_led_light_project_list_content.html'


class LedLightProjectForm(forms.ModelForm):

    class Meta:
        model = LedLightProject
        fields = (
            'name', 'previous_tube_count', 'previous_consumption_per_tube',
            'led_tube_count', 'led_consumption_per_tube', 'price',
            'datasource',
        )


class LedLightProjectCreateView(CustomerListMixin,
                                generic_views.CreateView):
    model = LedLightProject
    template_name = 'led_light_site/led_light_project_form.html'
    form_class = LedLightProjectForm

    def form_valid(self, form):
        form.instance.customer_id = self._customer.id
        result = super(LedLightProjectCreateView, self).form_valid(form)
        assert self.object.id
        self._customer.ledlightproject_set.add(self.object)
        return result

    def get_success_url(self):
        return reverse('led_light_site_projects:led-light-project-list',
                       kwargs={'customer_id':
                               self._customer.id})

    def get_cancel_url(self):
        return self.get_success_url()

    def get_breadcrumbs(self):
        return LedLightProjectList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Create LED Light Project'))


class LedLightProjectUpdateView(CustomerListMixin,
                                generic_views.UpdateView):
    model = LedLightProject
    template_name = 'led_light_site/led_light_project_form.html'
    form_class = LedLightProjectForm

    def get_success_url(self):
        return reverse('led_light_site_projects:led-light-project-list',
                       kwargs={'customer_id':
                               self._customer.id})

    def get_cancel_url(self):
        return self.get_success_url()

    def get_delete_url(self):
        return reverse('led_light_site_projects:led-light-project-delete',
                       kwargs={'customer_id':
                               self._customer.id,
                               'pk':
                               self.object.id})

    def get_breadcrumbs(self):
        return LedLightProjectList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(self.object)


class LedLightProjectDeleteView(
        CustomerListMixin, generic_views.DeleteView):
    model = LedLightProject

    def get_success_url(self):
        return reverse('led_light_site_projects:led-light-project-list',
                       kwargs={'customer_id':
                               self._customer.id})
