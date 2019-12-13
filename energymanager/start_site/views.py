# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import urlparse

from django.conf import settings
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import login as auth_login
from django.contrib.sites.models import get_current_site
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.contrib.staticfiles.templatetags.staticfiles import static

from gridplatform.trackuser import get_provider_id
from gridplatform.trackuser import replace_selected_customer


def applist(request, user):
    """
    Returns a list off apps that the loggedin user has access to
    """

    with replace_selected_customer(None):
        app_selection = []

        app_selection.append(
            {'name': _('SC-Portal 2.0'), 'url': reverse('website-home'),
                'icon': static('start_site/images/portal2_icon.png')})

        if user is None:
            return app_selection

        if user.has_perm('users.access_provider_site') and get_provider_id():
            app_selection.append(
                {'name': _('Administration'),
                 'url': reverse('provider_site:home'),
                 'icon': static('start_site/images/administration_icon.png')})

            app_selection.append(
                {'name': _('Configuration'),
                 'url': reverse('configuration_site:home'),
                 'icon': static('start_site/images/administration_icon.png')})

        if user.has_perm('users.access_led_light_site'):
            app_selection.append(
                {'name': _('LED Light'),
                 'url': reverse('led_light_site:home'),
                 'icon': static('start_site/images/led_light_icon.png')})

        if user.has_perm('users.access_project_site'):
            app_selection.append(
                {'name': _('ESCo Lite'),
                 'url': reverse('project_site:home'),
                 'icon': static('start_site/images/energy_manager_icon.png')})

        if user.has_perm('users.access_price_relay_site'):
            app_selection.append(
                {'name': _('Price Relay'),
                 'url': reverse('price_relay_site:home'),
                 'icon': static('start_site/images/energy_manager_icon.png')})

        if user.has_perm('users.access_datahub_site'):
            app_selection.append(
                {'name': _('Datahub'),
                 'url': reverse('datahub_site:home'),
                 'icon': static('start_site/images/energy_manager_icon.png')})

        return app_selection


class LoginView(FormView):
    template_name = "start_site/login.html"
    form_class = AuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        self.redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
        request.session.set_test_cookie()
        self.current_site = get_current_site(request)

        return super(
            LoginView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # login user
        user = form.get_user()
        auth_login(self.request, user)

        netloc = urlparse.urlparse(self.redirect_to)[1]

        # Use applist or default setting if self.redirect_to is empty
        if not self.redirect_to:
            app_selection = applist(self.request, user)
            if len(app_selection) == 1:
                self.redirect_to = app_selection[0]['url']
            else:
                self.redirect_to = settings.LOGIN_REDIRECT_URL

        # Heavier security check -- don't allow redirection to a different
        # host.
        elif netloc and netloc != self.request.get_host():
            self.redirect_to = settings.LOGIN_REDIRECT_URL

        if self.request.session.test_cookie_worked():
            self.request.session.delete_test_cookie()

        return HttpResponseRedirect(self.redirect_to)

    def render_to_response(self, context, **response_kwargs):
        context.update(
            {'REDIRECT_FIELD_NAME': self.redirect_to,
             'site': self.current_site,
             'site_name': self.current_site.name, })

        return super(
            LoginView, self).render_to_response(context, **response_kwargs)


class AppsView(TemplateView):
    template_name = "start_site/apps.html"
