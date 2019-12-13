# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import ugettext as _

from gridplatform.customers.models import Customer
from gridplatform.token_auth.models import create_token
from gridplatform.trackuser import get_provider
from gridplatform.trackuser import _get_user_customer
from gridplatform.users.managers import hash_username
from gridplatform.users.models import User
from gridplatform.utils import generic_views
from gridplatform.utils.views import NoCustomerMixin


class CustomerListView(NoCustomerMixin, generic_views.ListView):
    model = Customer
    template_name = 'provider_site/customer_list.html'

    def get_breadcrumbs(self):
        return (
            (_('Customers'), ''),
        )


class CustomerListContentView(
        NoCustomerMixin, generic_views.ListView):
    sort_fields = ['name_plain', 'is_active']
    search_fields = ['name_plain']
    model = Customer
    paginate_by = 100
    template_name = 'provider_site/_customer_list_content.html'


class CustomerCreateView(
        NoCustomerMixin, generic_views.CreateView):
    model = Customer
    template_name = 'provider_site/customer_form.html'
    fields = (
        'name', 'vat', 'address', 'postal_code', 'city', 'phone',
        'country_code', 'timezone', 'contact_name', 'contact_email',
        'contact_phone', 'electricity_instantaneous',
        'electricity_consumption', 'gas_instantaneous', 'gas_consumption',
        'water_instantaneous', 'water_consumption',
        'heat_instantaneous', 'heat_consumption',
        'oil_instantaneous', 'oil_consumption',
        'temperature', 'currency_unit',
    )

    def get_success_url(self):
        return reverse('provider_site:customer-list')

    def get_cancel_url(self):
        return self.get_success_url()

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.provider = get_provider()
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_breadcrumbs(self):
        return (
            (_('Customers'),
             reverse('provider_site:customer-list')),
            (_('Customer Details'), ''),
        )


class CustomerUpdateView(
        NoCustomerMixin, generic_views.UpdateView):
    model = Customer
    template_name = 'provider_site/customer_form.html'
    fields = (
        'name', 'vat', 'address', 'postal_code', 'city', 'phone',
        'country_code', 'timezone', 'contact_name', 'contact_email',
        'contact_phone', 'electricity_instantaneous',
        'electricity_consumption', 'gas_instantaneous', 'gas_consumption',
        'water_instantaneous', 'water_consumption',
        'heat_instantaneous', 'heat_consumption',
        'oil_instantaneous', 'oil_consumption',
        'temperature', 'currency_unit', 'is_active'
    )

    def get_success_url(self):
        return reverse('provider_site:customer-list')

    def get_cancel_url(self):
        return self.get_success_url()

    def get_breadcrumbs(self):
        return (
            (_('Customers'),
             reverse('provider_site:customer-list')),
            (_('Customer Details'), ''),
        )


class UserListView(
        NoCustomerMixin, generic_views.TemplateView):
    template_name = 'provider_site/user_list.html'


class UserListContentView(
        NoCustomerMixin, generic_views.ListView):
    sort_fields = ['e_mail_plain', 'name_plain']
    search_fields = ['e_mail_plain', 'name_plain']
    model = User
    paginate_by = 100
    template_name = 'provider_site/_user_list_content.html'

    def get_queryset(self):
        qs = super(UserListContentView, self).get_queryset()
        return qs.exclude(user_type=User.API_USER)


class UserFormBase(forms.ModelForm):
    class Meta:
        model = User

    def clean_e_mail(self):
        e_mail = self.cleaned_data['e_mail']
        if User.objects.filter(username=hash_username(e_mail)).exists():
            raise forms.ValidationError(
                _("A user with that e-mail already exists"))
        return e_mail


class UserForm(UserFormBase):
    class Meta(UserFormBase.Meta):
        fields = ('groups', 'e_mail',
                  'phone', 'mobile', 'password',
                  'name')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['password'].initial = User.objects.make_random_password()

        group_perm = Permission.objects.get(codename='provider_admin_group')
        groups = Group.objects.filter(permissions__id__exact=group_perm.id)
        self.fields['groups'].choices = [(g.id, g.name) for g in groups]


class UserCreateForm(UserForm):
    # customer field is editable=False on User model.
    customer = forms.ModelChoiceField(
        label=_('Customer'), queryset=Customer.objects.none())

    def __init__(self, *args, **kwargs):
        super(UserCreateForm, self).__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.all()

    def save(self, commit=True):
        self.instance.customer = self.cleaned_data['customer']
        return super(UserCreateForm, self).save(commit=commit)


class UserCreateView(
        NoCustomerMixin, generic_views.CreateView):
    model = User
    template_name = 'provider_site/user_form.html'
    form_class = UserCreateForm

    def get_success_url(self):
        return reverse('provider_site:user-list')

    def get_cancel_url(self):
        return self.get_success_url()

    def form_valid(self, form):
        self.object = form.save(commit=False)

        if self.object.customer:
            user = User.objects.create_user(
                self.object.e_mail_plain, self.object.password,
                user_type=User.ADMIN,
                customer=self.object.customer,
                groups=form.cleaned_data.get('groups', None))
        else:
            user = User.objects.create_user(
                self.object.e_mail_plain, self.object.password,
                user_type=User.ADMIN,
                provider=get_provider(),
                groups=form.cleaned_data.get('groups', None))

        user.e_mail_plain = self.object.e_mail_plain
        user.name_plain = self.object.name_plain
        user.phone_plain = self.object.phone_plain
        user.mobile_plain = self.object.mobile_plain
        user.save()

        return HttpResponseRedirect(self.get_success_url())


class UserUpdateForm(forms.ModelForm):
    new_password = forms.CharField(required=False, min_length=8)

    class Meta:
        model = User
        fields = ('groups', 'e_mail',
                  'name', 'phone', 'mobile', 'is_active')

    def __init__(self, *args, **kwargs):
        super(UserUpdateForm, self).__init__(*args, **kwargs)
        group_perm = Permission.objects.get(codename='provider_admin_group')
        groups = Group.objects.filter(permissions__id__exact=group_perm.id)
        self.fields['groups'].choices = [(g.id, g.name) for g in groups]

    def save(self, commit=True):
        assert commit
        user = super(UserUpdateForm, self).save(commit=False)
        if self.cleaned_data.get('new_password'):
            user.reset_password(
                self.request, self.cleaned_data.get('new_password'))
            if user.id == self.request.user.id:
                logout(self.request)
        user.save()
        self.save_m2m()
        return user


class UserUpdateView(
        NoCustomerMixin, generic_views.UpdateView):
    model = User
    template_name = 'provider_site/user_form.html'
    form_class = UserUpdateForm

    def get_success_url(self):
        return reverse('provider_site:user-list')

    def get_cancel_url(self):
        return self.get_success_url()

    def form_valid(self, form):
        form.request = self.request
        form.save()
        return HttpResponseRedirect(self.get_success_url())


class APIUserListView(NoCustomerMixin, generic_views.TemplateView):
    template_name = 'provider_site/api_user_list.html'

    def get_breadcrumbs(self):
        return ((_('API Users'), ''), )


class APIUserListContentView(NoCustomerMixin, generic_views.ListView):
    sort_fields = [
        'provider__name_plain', 'customer__name_plain', 'e_mail_plain',
    ]
    search_fields = [
        'provider__name_plain', 'customer__name_plain', 'e_mail_plain',
    ]
    model = User
    paginate_by = 100
    template_name = 'provider_site/_api_user_list_content.html'

    def get_queryset(self):
        qs = super(APIUserListContentView, self).get_queryset()
        return qs.filter(user_type=User.API_USER)


class APIUserForm(UserFormBase):
    class Meta(UserFormBase.Meta):
        fields = ('e_mail', 'groups')


class APIUserCreateForm(APIUserForm):
    def __init__(self, *args, **kwargs):
        super(APIUserCreateForm, self).__init__(*args, **kwargs)
        if _get_user_customer() is None:
            self.fields['customer'].required = False
            self.fields['customer'].widget.is_required = False
            self.fields['customer'].empty_label = \
                'All customers --- Provider API User'

    customer = forms.ModelChoiceField(
        label=_('Customer'),
        queryset=Customer.objects.all(), empty_label=None)

    def save(self, commit=True):
        self.instance.customer = self.cleaned_data['customer']
        if _get_user_customer() is None and not self.instance.customer:
            self.instance.provider = get_provider()
        return super(APIUserCreateForm, self).save(commit=commit)


class APIUserCreateView(NoCustomerMixin, generic_views.CreateView):
    model = User
    template_name = 'provider_site/api_user_form.html'
    form_class = APIUserCreateForm

    def get_success_url(self):
        return reverse('provider_site:apiuser-list')

    def form_valid(self, form):
        self.object = form.save(commit=False)

        password = User.objects.make_random_password(
            length=settings.TOKEN_AUTH_USER_PASSWORD_LENGTH)

        user = User.objects.create_user(
            self.object.e_mail_plain, password, user_type=User.API_USER,
            customer=self.object.customer, provider=self.object.provider,
            groups=form.cleaned_data.get('groups', None))

        user.name_plain = 'API User'
        user.save()
        token = create_token(user, password)

        context = {
            'username': user.e_mail_plain,
            'token': token,
        }
        return render(self.request, 'provider_site/show_token.html', context)

    def get_breadcrumbs(self):
        return (
            (_('API Users'), reverse('provider_site:apiuser-list')),
            (_('API User Create'), ''), )

    def get_cancel_url(self):
        return reverse('provider_site:apiuser-list')


class APIUserUpdateForm(UserFormBase):
    class Meta(UserFormBase.Meta):
        fields = ('groups', 'is_active')


class APIUserUpdateView(NoCustomerMixin, generic_views.UpdateView):
    model = User
    template_name = 'provider_site/api_user_update_form.html'
    form_class = APIUserUpdateForm

    def get_success_url(self):
        return reverse('provider_site:apiuser-list')

    def get_cancel_url(self):
        return reverse('provider_site:apiuser-list')

    def form_valid(self, form):
        form.request = self.request
        form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_breadcrumbs(self):
        return (
            (_('API Users'), reverse('provider_site:apiuser-list')),
            (self.object, ''), )
