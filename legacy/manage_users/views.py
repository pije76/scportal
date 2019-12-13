# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from django.forms import ModelForm
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.http import HttpResponseForbidden
from django.http import Http404
from django.conf import settings
from django.core.mail import send_mail

from gridplatform.utils.views import render_to
from gridplatform.utils.views import json_response
from gridplatform.utils.views import json_list_options
from gridplatform.trackuser import get_user
from gridplatform.trackuser import get_customer
from gridplatform.users.models import User
from gridplatform.users.managers import hash_username
from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.models import CollectionConstraint
from gridplatform.users.decorators import customer_admin_or_error
from legacy.legacy_utils.models import UserProfile


@customer_admin_or_error
@json_response
def list_json(request):
    options = json_list_options(request)
    customer = request.customer
    data = list(UserProfile.objects.filter(
        user__customer=customer, user__is_active=True).select_related('user'))
    if options['search']:
        data = filter(
            lambda userprofile:
            userprofile.user.satisfies_search(options['search']),
            data)
    order_map = {
        'name': lambda userprofile: userprofile.user.name_plain.lower(),
        'email': lambda userprofile: userprofile.user.e_mail_plain,
    }
    if options['order_by'] in order_map:
        data.sort(key=order_map[options['order_by']])
    if options['direction'].lower() == 'desc':
        data.reverse()
    data_slice = data[options['offset']:options['offset'] + options['count']]
    rendered = [
        render_to_string(
            'manage_users/user_block.html', {'userprofile': userprofile},
            RequestContext(request))
        for userprofile in data_slice
    ]
    return {
        'total': len(data),
        'data': rendered,
    }


class UserForm(ModelForm):
    send_password = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['user_type'].choices = [
            (User.CUSTOMER_USER, _('User')),
            (User.CUSTOMER_SUPERUSER, _('Superuser'))]

    def clean_e_mail(self):
        e_mail = self.cleaned_data['e_mail']
        if User.objects.filter(username=hash_username(e_mail)):
            raise forms.ValidationError(
                _("A user with that e-mail already exists"))
        return e_mail

    class Meta:
        model = User
        fields = ('name', 'e_mail', 'phone', 'mobile', 'user_type')
        localized_fields = '__all__'


class UserEditForm(UserForm):
    def clean_e_mail(self):
        e_mail = self.cleaned_data['e_mail']
        current_email = User.objects.get(id=self.instance.id).e_mail_plain

        if User.objects.filter(username=hash_username(e_mail)) \
                .exclude(username=hash_username(current_email)).exists():
            raise forms.ValidationError(
                _("A user with that e-mail already exists"))
        return e_mail


class UserProfileForm(ModelForm):

    collections = forms.MultipleChoiceField(required=False)

    class Meta:
        model = UserProfile
        fields = ()
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and kwargs['instance'] is not None:
            initial = kwargs.setdefault('initial', {})
            initial['collections'] = \
                kwargs['instance'].collections.values_list(
                    'id', flat=True)
        super(UserProfileForm, self).__init__(*args, **kwargs)

        self.fields["collections"].choices = [
            (group.id,
             mark_safe('&nbsp;' * 2 * group.level +
                       escape(unicode(group))))
            for group in Collection.objects.filter(
                customer=get_customer(), role=Collection.GROUP)]

    def save(self, commit=True):
        super(UserProfileForm, self).save(False)

        def save_m2m():
            self.instance.collections.clear()
            for collection in self.cleaned_data['collections']:
                CollectionConstraint.objects.create(
                    collection_id=collection,
                    userprofile=self.instance)
        self.save_m2m = save_m2m

        if commit:
            self.instance.save()
            self.save_m2m()

        return self.instance


@customer_admin_or_error
@render_to('manage_users/user_form.html')
def user_form(request, pk=None):
    user = get_user()
    reason = None
    instance = None
    userprofile = None

    if pk:
        instance = get_object_or_404(User, pk=pk)
        userprofile = instance.get_profile()

        if instance.customer != get_customer():
            return HttpResponseForbidden()

        if instance.is_active is False:
            raise Http404

        if instance.id == user.id:
            reason = {'reason': _('It is not allowed to delete yourself')}
        user_form = UserEditForm(instance=instance, auto_id=False)
    else:
        user_form = UserForm(instance=instance, auto_id=False)

    userprofile_form = UserProfileForm(instance=userprofile, auto_id=False)

    return {
        'user_form': user_form,
        'userprofile_form': userprofile_form,
        'delete': (reason or {'reason': ''}),
    }


# Used by user_update
def create_user(request, customer, user_form, userprofile_form):
    user = None
    password = User.objects.make_random_password()

    user = User.objects.create_user(
        user_form.cleaned_data['e_mail'],
        password,
        user_type=user_form.cleaned_data['user_type'],
        customer=customer)
    user_profile = userprofile_form.save(commit=False)
    user_profile.user = user
    user_profile.id = user.get_profile().id
    user_profile.save()
    userprofile_form.save_m2m()

    user.e_mail_plain = user_form.cleaned_data['e_mail']
    user.phone_plain = user_form.cleaned_data['phone']
    user.mobile_plain = user_form.cleaned_data['mobile']
    user.name_plain = user_form.cleaned_data['name']
    user.save()

    send_password = user_form.cleaned_data['send_password']

    if send_password:
        subject = _('%(site_name)s user information') % {
            'site_name': settings.SITE_NAME
        }
        message = _("""Username: %(username)s
Password: %(password)s""") % {
            'username': user_form.cleaned_data['e_mail'],
            'password': password
        }

        send_mail(
            subject,
            message,
            settings.SITE_MAIL_ADDRESS,
            [user_form.cleaned_data['e_mail']],
            fail_silently=False)

    return user, password


@customer_admin_or_error
@json_response
def user_delete(request):
    instance = get_object_or_404(User, pk=request.GET['pk'])
    if instance.customer != get_customer():
        return HttpResponseForbidden()

    instance.is_active = False
    instance.save()
    return {
        'success': True,
        'statusText': _('The user has been deleted'),
    }


@customer_admin_or_error
@json_response
def user_update(request, pk=None):
    customer = request.customer
    if pk:
        instance = get_object_or_404(User, pk=pk)
        userprofile = instance.get_profile()
        if instance.customer != customer:
            return HttpResponseForbidden()
        if instance.id == get_user().id:
            reason = {'reason': _('It is not allowed to delete yourself')}
        else:
            reason = None
        user_form = UserEditForm(
            request.POST,
            instance=instance,
            auto_id=False)
    else:
        userprofile = None
        instance = None
        reason = None
        user_form = UserForm(
            request.POST,
            instance=instance,
            auto_id=False)

    userprofile_form = UserProfileForm(
        request.POST,
        instance=userprofile,
        auto_id=False)

    groups = list(customer.collection_set.all())

    userprofile_form.fields["collections"].choices = [
        (group.id,
         mark_safe('&nbsp;' * 2 * group.level +
                   escape(unicode(group))))
        for group in groups]

    if all([user_form.is_valid(), userprofile_form.is_valid()]):
        if pk:
            user = user_form.save(commit=False)
            user.username = hash_username(user.e_mail_plain)
            user.save()
            if request.POST.get('send_password', False):
                password = User.objects.make_random_password()
                user.reset_password(request, password)
                user.save()
                subject = _('%(site_name)s user information') % {
                    'site_name': settings.SITE_NAME
                }
                message = _(
                    "Username: %(username)s\n"
                    "Password: %(password)s") % {
                    'username': user_form.cleaned_data['e_mail'],
                    'password': password}

                send_mail(
                    subject,
                    message,
                    settings.SITE_MAIL_ADDRESS,
                    [user_form.cleaned_data['e_mail']],
                    fail_silently=False)

            userprofile_form.save()
            statusText = _('The user has been updated')
            returnDict = {'userprofile': user.get_profile()}
        else:
            user_info = create_user(
                request, customer, user_form, userprofile_form)
            returnDict = {'userprofile': user_info[0].get_profile(),
                          'password': user_info[1]}
            statusText = _('The user has been created')

        return {
            'success': True,
            'statusText': statusText,
            'html': render_to_string(
                'manage_users/user_block.html',
                returnDict,
                RequestContext(request)
            ),
        }

    else:
        return {
            'success': False,
            'html': render_to_string(
                'manage_users/user_form.html',
                {
                    'user_form': user_form,
                    'userprofile_form': userprofile_form,
                    'object': instance,
                    'user': instance,
                    'delete': reason or {'reason': ''},
                },
                RequestContext(request)
            ),
        }
