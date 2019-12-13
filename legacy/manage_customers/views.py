# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings
from django.forms import ModelForm, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.db.models import Q
from django.utils.translation import ugettext as _

from gridplatform.customers.models import Customer
from gridplatform.users.decorators import admin_or_error
from gridplatform.users.managers import hash_username
from gridplatform.users.models import User
from gridplatform.utils.views import json_list_options
from gridplatform.utils.views import json_response
from gridplatform.utils.views import render_to

from legacy.manage_devices.views import agent_list_json
from legacy.manage_devices.views import meter_list_json
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import DataSeries


@admin_or_error
@json_response
def customer_list_json(request):
    options = json_list_options(request)
    data = list(Customer.objects.all())
    if options['search']:
        data = filter(
            lambda customer:
            customer.satisfies_search(options['search']),
            data)
    order_map = {
        'name': lambda customer: customer.name_plain.lower()
        if customer.name_plain else _('Encrypted'),
    }
    if options['order_by'] in order_map:
        data.sort(key=order_map[options['order_by']])
    if options['direction'].lower() == 'desc':
        data.reverse()
    data_slice = data[options['offset']:options['offset'] + options['count']]
    rendered = [
        render_to_string(
            'manage_customers/customer_block.html', {'customer': customer},
            RequestContext(request))
        for customer in data_slice
    ]
    return {
        'total': len(data),
        'data': rendered,
    }


class CustomerProfileForm(ModelForm):
    def __init__(self, *args, **kwargs):
        defaults = {
            'auto_id': False
        }
        defaults.update(kwargs)
        super(CustomerProfileForm, self).__init__(*args, **defaults)

        base_tariff_queryset = DataSeries.objects.filter(
            Q(customer=self.instance) | Q(customer__isnull=True))

        self.fields['electricity_tariff'].queryset = \
            base_tariff_queryset.filter(role=DataRoleField.ELECTRICITY_TARIFF)
        self.fields['gas_tariff'].queryset = \
            base_tariff_queryset.filter(role=DataRoleField.GAS_TARIFF)
        self.fields['water_tariff'].queryset = \
            base_tariff_queryset.filter(role=DataRoleField.WATER_TARIFF)
        self.fields['heat_tariff'].queryset = \
            base_tariff_queryset.filter(role=DataRoleField.HEAT_TARIFF)
        self.fields['oil_tariff'].queryset = \
            base_tariff_queryset.filter(role=DataRoleField.OIL_TARIFF)

    class Meta:
        model = Customer
        localized_fields = '__all__'


class UserForm(ModelForm):
    def __init__(self, *args, **kwargs):
        defaults = {
            'auto_id': False
        }
        defaults.update(kwargs)
        super(UserForm, self).__init__(*args, **defaults)

    class Meta:
        model = User
        fields = ('e_mail', 'phone', 'mobile', 'name')
        localized_fields = '__all__'

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=hash_username(username)).exists():
            raise ValidationError(_('The username already exists'))
        return username


@admin_or_error
@render_to('manage_customers/customerprofile_edit_form.html')
def customer_form(request, pk=None):
    if pk:
        customer = get_object_or_404(Customer, pk=pk)
        instance = customer
    else:
        instance = None
        customer = None

    form = CustomerProfileForm(instance=instance, auto_id=False)
    return {
        'form': form,
        'object': instance,
        'customerprofile': instance,
        'customer': customer,
    }


@admin_or_error
@json_response
def customer_update(request, pk=None):
    if pk:
        customer = get_object_or_404(Customer, pk=pk)
        instance = customer
    else:
        instance = None
        customer = None

    form = CustomerProfileForm(request.POST, instance=instance, auto_id=False)
    if form.is_valid():
        customer = form.save()
        return {
            'success': True,
            'statusText': _('The customer has been saved'),
            'html': render_to_string(
                'manage_customers/customer_block.html',
                {'customer': customer},
                RequestContext(request)
            ),
        }
    else:
        return {
            'success': False,
            'html': render_to_string(
                'manage_customers/customerprofile_edit_form.html',
                {
                    'form': form,
                    'object': instance,
                    'customerprofile': instance,
                    'customer': customer
                },
                RequestContext(request)
            ),
        }


@admin_or_error
@render_to('manage_customers/customer_agent_list.html')
def customer_agent_list(request, customer):
    customer = get_object_or_404(Customer, pk=customer)
    return {
        'customer': customer,
    }


@admin_or_error
@json_response
def customer_agent_list_json(request, customer):
    customer = get_object_or_404(Customer, pk=customer)
    return agent_list_json(request, customer)


@admin_or_error
@render_to('manage_customers/customer_meter_list.html')
def customer_meter_list(request, customer):
    customer = get_object_or_404(Customer, pk=customer)
    return {
        'customer': customer,
    }


@admin_or_error
@json_response
def customer_meter_list_json(request, customer):
    customer = get_object_or_404(Customer, pk=customer)
    return meter_list_json(request, customer)


@admin_or_error
def as_customer(request, pk):
    # sanity check
    customer = get_object_or_404(Customer, pk=pk)
    request.session['customer_id'] = customer.id
    return redirect(settings.LOGIN_REDIRECT_URL)


@admin_or_error
def as_admin(request):
    request.session['customer_id'] = None
    return redirect(settings.LOGIN_REDIRECT_URL)
