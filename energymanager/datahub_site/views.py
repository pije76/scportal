# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import calendar
import pycurl
import StringIO

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext_lazy
from django import forms
from django.core.urlresolvers import reverse
from django.db.models.fields import BLANK_CHOICE_DASH
from django.http import HttpResponse
from django.conf import settings

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
from gridplatform.datahub.models import DatahubConnection
from legacy.devices.models import PhysicalInput


class HomeView(HomeViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'datahub_site:connection-list',
            kwargs={'customer_id': customer_id})

    def get_choose_customer_url(self):
        return reverse(
            'datahub_site:choose-customer')


class ChooseCustomer(ChooseCustomerBase):
    template_name = 'datahub_site/choose_customer.html'


class CustomerView(CustomerViewBase):
    def get_redirect_with_customer_url(self, customer_id):
        return reverse(
            'datahub_site:connection-list',
            kwargs={'customer_id': customer_id})


class DatahubConnectionList(CustomerListMixin, generic_views.TemplateView):
    template_name = 'datahub_site/datahub_connection_list.html'

    @staticmethod
    def build_breadcrumbs(customer_id):
        return Breadcrumbs() + Breadcrumb(
            _('Forbindelser'),
            reverse(
                'datahub_site:connection-list',
                kwargs={'customer_id': customer_id}))

    def get_breadcrumbs(self):
        return self.build_breadcrumbs(self._customer.id)


class DatahubConnectionListContentView(
        CustomerListMixin,
        generic_views.ListView):
    search_fields = ['customer_meter_number', ]
    sort_fields = ['customer_meter_number', ]
    model = DatahubConnection
    paginate_by = 100
    template_name = 'datahub_site/_datahub_connection_list_content.html'


class DatahubConnectionForm(forms.ModelForm):

    class Meta:
        model = DatahubConnection
        fields = (
            'customer_meter_number', 'meter'
        )


class DatahubConnectionCreateView(CustomerListMixin,
                                  generic_views.CreateView):
    model = DatahubConnection
    template_name = 'datahub_site/datahub_connection_form.html'
    form_class = DatahubConnectionForm

    def form_valid(self, form):
        form.instance.customer_id = self._customer.id
        meter = form.instance.meter
        input = PhysicalInput.objects.create(
            meter=meter,
            order=0,
            name_plain="Datahub",
            unit="milliwatt*hour",
            type=PhysicalInput.ELECTRICITY
        )

        form.instance.input = input

        response = super(DatahubConnectionCreateView, self).form_valid(form)
        return response

    def get_success_url(self):
        return reverse('datahub_site:connection-list',
                       kwargs={'customer_id':
                               self._customer.id})

    def get_cancel_url(self):
        return self.get_success_url()

    def get_breadcrumbs(self):
        return DatahubConnectionList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(_('Create connection'))


class DatahubConnectionUpdateView(CustomerListMixin,
                                  generic_views.UpdateView):
    model = DatahubConnection
    template_name = 'datahub_site/datahub_connection_form.html'
    fields = (
        'customer_meter_number',
    )

    def get_success_url(self):
        return reverse('datahub_site:connection-list',
                       kwargs={'customer_id':
                               self._customer.id})

    def get_cancel_url(self):
        return self.get_success_url()

    def get_breadcrumbs(self):
        return DatahubConnectionList.build_breadcrumbs(self._customer.id) + \
            Breadcrumb(self.object)


def datahub_authorization_view(request):
    b = StringIO.StringIO()
    c = pycurl.Curl()
    url = 'https://eloverblik.dk/api/authorizationsv2'
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.WRITEFUNCTION, b.write)
    c.setopt(pycurl.SSLKEY, settings.NETS_KEY_DIR + "/plainkey.pem")
    c.setopt(pycurl.SSLCERT, settings.NETS_KEY_DIR + "/crt.pem")
    c.perform()
    c.close()
    response_body = b.getvalue()
    return HttpResponse(response_body, content_type='application/json')
