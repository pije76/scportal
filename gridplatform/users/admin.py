# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.auth.admin import csrf_protect_m
from django.contrib.auth.admin import sensitive_post_parameters_m
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from gridplatform.providers.models import Provider

from .models import User


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput)
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        help_text=_("Enter the same password as above, for verification."))

    provider = forms.ModelChoiceField(
        label=_('Provider'),
        queryset=Provider.objects.all(), empty_label=None)

    class Meta:
        model = User
        fields = (
            'name', 'e_mail', 'phone', 'mobile', 'user_type',
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def save(self, commit=True):
        self.instance.provider = self.cleaned_data['provider']
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


def e_mail_address(obj):
    return obj.e_mail_plain


def name(obj):
    return obj.name_plain


class UserAdmin(admin.ModelAdmin):
    add_form_template = 'admin/auth/user/add_form.html'
    fieldsets = (
        (_('Personal info'), {
            'fields': ('name', 'e_mail', 'phone', 'mobile')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions', 'user_type'
            )
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None, {
                'classes': ('wide',),
                'fields': (
                    'name', 'e_mail', 'phone', 'mobile', 'user_type',
                    'provider',
                    'password1', 'password2')
            },
        ),
    )
    add_form = UserCreationForm
    list_display = (e_mail_address, name,)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ()
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super(UserAdmin, self).get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults.update({
                'form': self.add_form,
                'fields': admin.util.flatten_fieldsets(
                    self.add_fieldsets),
            })
        defaults.update(kwargs)
        return super(UserAdmin, self).get_form(request, obj, **defaults)

    def lookup_allowed(self, lookup, value):
        # See #20078: we don't want to allow any lookups involving passwords.
        if lookup.startswith('password'):
            return False
        return super(UserAdmin, self).lookup_allowed(lookup, value)

    @sensitive_post_parameters_m
    @csrf_protect_m
    @transaction.atomic
    def add_view(self, request, form_url='', extra_context=None):
        # It's an error for a user to have add permission but NOT change
        # permission for users. If we allowed such users to add users, they
        # could create superusers, which would mean they would essentially have
        # the permission to change users. To avoid the problem entirely, we
        # disallow users from adding users if they don't have change
        # permission.
        if not self.has_change_permission(request):
            if self.has_add_permission(request) and settings.DEBUG:
                # Raise Http404 in debug mode so that the user gets a helpful
                # error message.
                raise Http404(
                    'Your user does not have the "Change user" permission. In '
                    'order to add users, Django requires that your user '
                    'account have both the "Add user" and "Change user" '
                    'permissions set.')
            raise PermissionDenied
        if extra_context is None:
            extra_context = {}
        username_field = self.model._meta.get_field(self.model.USERNAME_FIELD)
        defaults = {
            'auto_populated_fields': (),
            'username_help_text': username_field.help_text,
        }
        extra_context.update(defaults)
        return super(UserAdmin, self).add_view(
            request, form_url, extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        """
        Determines the HttpResponse for the add_view stage. It mostly defers to
        its superclass implementation but is customized because the User model
        has a slightly different workflow.
        """
        # We should allow further modification of the user just added i.e. the
        # 'Save' button should behave like the 'Save and continue editing'
        # button except in two scenarios:
        # * The user has pressed the 'Save and add another' button
        # * We are adding a user in a popup
        if '_addanother' not in request.POST and \
                IS_POPUP_VAR not in request.POST:
            request.POST['_continue'] = 1
        return super(UserAdmin, self).response_add(
            request, obj, post_url_continue)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'user_permissions':
            qs = kwargs.get('queryset', db_field.rel.to.objects)
            kwargs['queryset'] = qs.select_related('content_type')
        return super(UserAdmin, self).formfield_for_manytomany(
            db_field, request=request, **kwargs)


admin.site.register(
    User,
    UserAdmin)
