# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.auth.views import redirect_to_login
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from django import forms
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.functional import cached_property

from braces.views._access import AccessMixin

from gridplatform.utils import generic_views
from gridplatform.users.models import User
from gridplatform.trackuser import get_user
from gridplatform.trackuser import get_customer


class CustomerAdminOrAdminRequiredMixin(AccessMixin):
    """
    View mixin that ensures user is customer superuser or admin.

    :cvar raise_exception=False: Boolean class member attribute inherited from
        :class:`braces.views._access.AccessMixin`. Controls what happens when
        unauthorized access is attempted.  If set to ``True`` a
        :class:`django.core.exceptions.PermissionDenied` exception is raised,
        if ``False`` redirect to login page.
    """
    def dispatch(self, request, *args, **kwargs):
        """
        Handle authorization checks and delegate to super ``dispatch()``
        implementation.
        """
        if not (request.user.is_authenticated() and
                (request.user.is_customer_superuser or request.user.is_admin)):
            if self.raise_exception:
                raise PermissionDenied
            else:
                return redirect_to_login(
                    request.get_full_path(),
                    self.get_login_url(),
                    self.get_redirect_field_name())
        return super(CustomerAdminOrAdminRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class UserProfileForm(forms.ModelForm):
    """
    :class:`~django.forms.ModelForm` for :class:`.User` model.

    Besides updating regular fields, this form also supports changing password.
    Old password and the new password repeated twice must be entered to update
    the password.
    """
    old_password = forms.CharField(
        label=_('password'), widget=forms.PasswordInput, required=False)
    new_password = forms.CharField(
        label=_('new password'),
        widget=forms.PasswordInput, min_length=8, required=False)
    new_password_check = forms.CharField(
        label=_('new password again'),
        widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ('name', 'phone', 'mobile',)
        localized_fields = '__all__'

    def clean(self):
        """
        :raise ValidationError: If new password is set, but old password is not
            provided or does not authenticate the currently loged in user.
        :raise ValidationError: If new password and password confirmation field
            do not contain the same password.
        """

        cleaned_data = super(UserProfileForm, self).clean()
        user = get_user()

        if cleaned_data.get('new_password'):
            if cleaned_data['old_password'] == "":
                raise ValidationError(_("Please provide your password"))
            else:
                authenticated = authenticate(
                    username=user.e_mail_plain,
                    password=cleaned_data['old_password'])
                if not authenticated:
                    raise ValidationError(_("The password is not correct"))

            if cleaned_data['new_password'] != \
                    cleaned_data['new_password_check']:
                raise ValidationError(_("The passwords doesn't match"))

        return cleaned_data


class UserProfileView(generic_views.FormView):
    """
    View for updating :class:`.User` details.
    """
    form_class = UserProfileForm
    template_name = "users/_user_profile_form.html"

    def get_cancel_url(self):
        return '#'

    def get_form_kwargs(self):
        """
        Ensures that ``form.instance`` is set to the :class:`.User` currently
        logged in.
        """
        kwargs = super(UserProfileView, self).get_form_kwargs()
        kwargs['instance'] = get_user()
        return kwargs

    def form_valid(self, form):
        """
        Changes the password if new password was provided.  Otherwise somewhat
        similar to :meth:`django.views.generic.UpdateView.form_valid`
        """
        user = get_user()
        user.name_plain = form.cleaned_data['name']
        user.phone_plain = form.cleaned_data['phone']
        user.mobile_plain = form.cleaned_data['mobile']

        if form.cleaned_data['new_password'] != "":
            user.set_password(
                form.cleaned_data['new_password'],
                old_password=form.cleaned_data['old_password']
            )

        user.save()
        return HttpResponse('success')

    @cached_property
    def _customer(self):
        return get_customer()
