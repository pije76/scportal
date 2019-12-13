# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.template.loader import render_to_string
from django.template import RequestContext
from django.forms import ModelForm
from django.http import HttpResponseForbidden
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from django.utils.html import escape

from gridplatform.utils.views import (
    render_to,
    json_response,
    json_list_options,
)
from legacy.measurementpoints.models import Location
from gridplatform.users.decorators import (
    auth_or_error,
    customer_admin_or_error,
)
from legacy.devices.models import Agent, Meter


def can_delete(request, location):
    agents = location.agent_set.all()
    meters = location.meter_set.all()
    locations = location.children.all()
    dependents = []
    if agents:
        dependents.append(_("Agents:"))
        dependents.append('<ul>')
        for agent in agents:
            dependents.append('<li>%s</li>' % (escape(unicode(agent)),))
        dependents.append('</ul>')
    if meters:
        dependents.append(_("Meters:"))
        dependents.append('<ul>')
        for meter in meters:
            dependents.append('<li>%s</li>' % (escape(unicode(meter)),))
        dependents.append('</ul>')
    if locations:
        dependents.append(_("Locations:"))
        dependents.append('<ul>')
        for location in locations:
            dependents.append('<li>%s</li>' % (escape(unicode(location)),))
        dependents.append('</ul>')
    if dependents:
        # @bug: Use ngettext for plural forms.
        reason = _("This location cannot be deleted because the following "
                   "depends on it:") + "<br />" + "".join(dependents)
    else:
        reason = ""
    return {
        'reason': reason
    }


@customer_admin_or_error
@json_response
def location_delete(request):
    instance = get_object_or_404(Location, pk=request.GET['pk'])
    instance.delete()
    return {
        'success': True,
        'statusText': _('The location has been deleted'),
    }


@auth_or_error
@json_response
def location_list_json(request):
    options = json_list_options(request)
    customer = request.customer
    if options['search']:
        data = list(Location.objects.filter(customer=customer))
    else:
        data = list(Location.objects.filter(customer=customer, level=0))

    if options['search']:
        data = filter(
            lambda location:
            location.satisfies_search(options['search']), data)

    data.sort(key=lambda location: location.name_plain.lower())

    if options['search']:
        rendered = [
            render_to_string(
                'manage_locations/location_normal_block.html',
                {'location': location},
                RequestContext(request))
            for location in data
        ]
    else:
        rendered = [
            render_to_string(
                'manage_locations/location_block.html',
                {'locations': location.get_descendants(include_self=True)},
                RequestContext(request))
            for location in data
        ]

    return {
        'total': len(data),
        'data': rendered,
    }


class LocationForm(ModelForm):
    class Meta:
        model = Location
        fields = ('name', 'parent',)
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(LocationForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            children = [descendant.id for descendant
                        in self.instance.get_descendants(include_self=True)]
        else:
            children = []

        self.fields['parent'].queryset = \
            Location.objects.all().exclude(pk__in=children)


@customer_admin_or_error
@render_to('manage_locations/location_form.html')
def location_form(request, pk=None):
    customer = request.customer
    if pk:
        instance = get_object_or_404(Location, pk=pk)
        if instance.customer != customer:
            return HttpResponseForbidden()
        delete = can_delete(request, instance)
    else:
        instance = None
        delete = False

    form = LocationForm(instance=instance, auto_id=False)

    return {
        'form': form,
        'object': instance,
        'location': instance,
        'delete': delete,
    }


# parent = 0 means no change in parent.
# parent > 0 is the id of the parent
# parent = None means no parent
@customer_admin_or_error
@json_response
def location_update(request, pk=None):
    if pk:
        instance = get_object_or_404(Location, pk=pk)
        old_parent = instance.parent
    else:
        instance = None
        old_parent = None

    form = LocationForm(request.POST, instance=instance, auto_id=False)
    if form.is_valid():
        location = form.save()

        if old_parent == location.parent:
            parent = 0
        else:
            if location.parent is not None:
                parent = location.parent.id
            else:
                parent = None

        return {
            'success': True,
            'statusText': _('The location has been saved'),
            'html': render_to_string(
                'manage_locations/location_normal_block.html',
                {'location': location},
                RequestContext(request)
            ),
            'parent': parent,
        }
    else:
        return {
            'success': False,
            'html': render_to_string(
                'manage_locations/location_form.html',
                {
                    'form': form,
                    'object': instance,
                    'agent': instance,
                },
                RequestContext(request)
            ),
        }


@auth_or_error
@json_response
def agent_list_json(request, location):
    options = json_list_options(request)
    data = list(Agent.objects.filter(location=location).select_related(
        'location'))

    if options['search']:
        data = filter(
            lambda agent: agent.satisfies_search(options['search']), data)
    order_map = {
        'location': lambda agent: unicode(agent.location),
        'mac': lambda agent: unicode(agent.mac),
    }
    if options['order_by'] and options['order_by'] in order_map:
        data.sort(key=order_map[options['order_by']])
    if options['direction'].lower() == 'desc':
        data.reverse()
    data_slice = data[options['offset']:options['offset'] + options['count']]
    rendered = [
        render_to_string(
            'manage_devices/agent_block.html',
            {'agent': agent},
            RequestContext(request))
        for agent in data_slice
    ]
    return {
        'total': len(data),
        'data': rendered,
    }


@auth_or_error
@json_response
def meter_list_json(request, location):
    options = json_list_options(request)
    data = list(Meter.objects.filter(location=location).select_related(
        'agent', 'location'))

    if options['search']:
        data = filter(
            lambda meter: meter.satisfies_search(options['search']), data)
    order_map = {
        'name': lambda meter: meter.name_plain.lower(),
        'location': lambda meter: unicode(meter.location),
        'agent': lambda meter: unicode(meter.agent),
    }
    if options['order_by'] and options['order_by'] in order_map:
        data.sort(key=order_map[options['order_by']])
    if options['direction'].lower() == 'desc':
        data.reverse()

    data_slice = data[options['offset']:options['offset'] + options['count']]
    rendered = [
        render_to_string(
            'manage_devices/meter_block.html',
            {'meter': meter},
            RequestContext(request))
        for meter in data_slice
    ]
    return {
        'total': len(data),
        'data': rendered,
    }
