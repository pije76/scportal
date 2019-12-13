# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.forms.util import ErrorList

from gridplatform.users.models import User
from gridplatform.utils.views import render_to, json_response
from gridplatform.users.decorators import auth_or_redirect
from gridplatform.trackuser import get_user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('phone', 'mobile', 'name')
        localized_fields = '__all__'


class PasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    old_password = forms.CharField(widget=forms.PasswordInput)


# AMMH: Consider; is pk argument useful?  If it *has* to be the same as
# get_user().id; why not just use get_user() for the User instance?  ("In
# case the code should later be generalised to let admins change users via
# this"?)
@auth_or_redirect
@render_to('edit_userprofile/userprofile.html')
def userprofile_form(request, pk):
    if get_user().id != int(pk):
        return HttpResponseForbidden()
    instance = get_object_or_404(User, pk=pk)
    form = UserProfileForm(instance=instance)
    password_form = PasswordForm()
    return {
        'form': form,
        'password_form': password_form,
        'object': instance,
        'user': instance,
    }


# AMMH: Template in edit_userprofile/form.html does not include any rendering
# of non_field_errors.
# MCL: We don't get non_field_errors and we don't have
# a concept for it
@json_response
def userprofile_update(request, pk):
    if get_user().id != int(pk):
        return HttpResponseForbidden()
    instance = get_object_or_404(User, pk=pk)
    form = UserProfileForm(request.POST, instance=instance)
    password_form = PasswordForm()
    valid = False
    if form.is_valid():
        instance = form.save(commit=False)
        valid = True

    if request.POST['password'] != '' or request.POST['old_password'] != '':
        password_form = PasswordForm(request.POST)
        valid = False
        if password_form.is_valid():
            try:
                instance.set_password(
                    password_form.cleaned_data['password'],
                    old_password=password_form.cleaned_data['old_password']
                )
                valid = True
            except ValueError as e:
                password_form._errors["old_password"] = ErrorList([e])

    if valid:
        instance.save()
        return {
            'success': True,
            'statusText': _('Your profile has been saved'),
            'html': render_to_string(
                'edit_userprofile/form.html',
                {
                    'form': form,
                    'password_form': password_form,
                    'object': instance,
                    'user': instance,
                },
                RequestContext(request)
            ),
        }
    else:
        return {
            'success': False,
            'html': render_to_string(
                'edit_userprofile/form.html',
                {
                    'form': form,
                    'password_form': password_form,
                    'object': instance,
                    'user': instance,
                },
                RequestContext(request)
            ),
        }
