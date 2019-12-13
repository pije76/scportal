# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.db.models.fields import BLANK_CHOICE_DASH

from gridplatform.utils.views import (
    render_to,
    json_response,
    json_list_options,
)
from gridplatform.users.decorators import admin_or_error
from legacy.devices.models import Agent, SoftwareImage
from legacy.ipc import agentserver


@admin_or_error
@json_response
def agent_list_json(request):
    options = json_list_options(request)
    data = list(Agent.objects.select_related(
        'location', 'customer', 'customer'))
    if options['search']:
        data = filter(
            lambda agent: agent.satisfies_search(options['search']), data)
    order_map = {
        'location': lambda agent: unicode(agent.location),
        'mac': lambda agent: unicode(agent.mac),
        'customer': lambda agent: (
            (agent.customer and unicode(agent.customer)) or '')
    }
    if options['order_by'] and options['order_by'] in order_map:
        data.sort(key=order_map[options['order_by']])
    if options['direction'].lower() == 'desc':
        data.reverse()
    data_slice = data[options['offset']:options['offset'] + options['count']]
    rendered = [
        render_to_string(
            'setup_agents/agent_block.html', {'agent': agent},
            RequestContext(request))
        for agent in data_slice
    ]
    return {
        'total': len(data),
        'data': rendered,
    }


class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ('mac', 'customer')


class UpgradeForm(forms.Form):
    software_image = forms.ChoiceField(
        required=True, choices=BLANK_CHOICE_DASH)


@admin_or_error
@render_to('setup_agents/agent_form.html')
def agent_form(request, pk=None):
    if pk:
        instance = get_object_or_404(Agent, pk=pk)
        upgrade_form = UpgradeForm(auto_id=False)
        # the form instance has local copies of the field instances,
        # i.e. modifying is safe
        upgrade_form.fields['software_image'].choices = BLANK_CHOICE_DASH + [
            (image.id, image.get_sw_version_display())
            for image in instance.compatible_software()]
    else:
        instance = None
        upgrade_form = None
    form = AgentForm(instance=instance, auto_id=False)
    return {
        'form': form,
        'upgrade_form': upgrade_form,
        'object': instance,
        'agent': instance,
    }


@admin_or_error
@json_response
def agent_update(request, pk=None):
    if pk:
        instance = get_object_or_404(Agent, pk=pk)
        original_customer = instance.customer
    else:
        instance = None
        original_customer = None
    form = AgentForm(request.POST, instance=instance, auto_id=False)
    if form.is_valid():
        agent = form.save(commit=False)
        if agent.customer != original_customer:
            agent.location = None
            for meter in agent.meter_set.all():
                meter.joined = False
                meter.save()
        agent.save()
        return {
            'success': True,
            'statusText': _('The agent has been saved'),
            'html': render_to_string(
                'setup_agents/agent_block.html',
                {'agent': agent},
                RequestContext(request)
            ),
        }
    else:
        return {
            'success': False,
            'html': render_to_string(
                'setup_agents/agent_form.html',
                {
                    'form': form,
                    'object': instance,
                    'agent': instance,
                },
                RequestContext(request)
            ),
        }


@admin_or_error
@json_response
def agent_swupgrade(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    form = UpgradeForm(request.POST, auto_id=False)
    form.fields['software_image'].choices = BLANK_CHOICE_DASH + [
        (image.id, image.get_sw_version_display())
        for image in agent.compatible_software()]
    if form.is_valid():
        if agent.online:
            sw_image = SoftwareImage.objects.get(
                pk=form.cleaned_data['software_image'])
            agentserver.agent_swupdate(agent.mac, sw_image)
            return {
                'success': True,
                'statusText': _('Sending software update'),
            }
        else:
            return {
                'success': False,
                'statusText': _('Agent currently offline'),
            }
    else:
        return {
            'success': False,
            'statusText': _('Invalid version for agent')
        }
