# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.template import RequestContext
from django.forms import ModelForm, ImageField
from django.http import HttpResponseForbidden
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.forms.widgets import ClearableFileInput

from legacy.measurementpoints.models import Collection
from legacy.manage_collections.models import CollectionItem
from legacy.manage_collections.models import Floorplan
from legacy.manage_collections.models import InfoItem
from legacy.manage_collections.models import Item
from legacy.manage_measurementpoints.forms import CollectionForm
from gridplatform.trackuser import get_customer
from gridplatform.users.decorators import auth_or_error
from gridplatform.users.decorators import customer_admin_or_error
from gridplatform.utils import utilitytypes
from gridplatform.utils.views import json_list_options
from gridplatform.utils.views import json_response
from gridplatform.utils.views import render_to


@customer_admin_or_error
@json_response
def group_delete(request):
    instance = get_object_or_404(Collection, pk=request.GET['pk'])
    customer = request.customer
    if instance.customer != customer or not instance.is_deletable():
        return HttpResponseForbidden()

    instance.delete()
    return {
        'success': True,
        'statusText': _('The group has been deleted'),
    }


@auth_or_error
@json_response
def group_list_json(request):
    options = json_list_options(request)
    customer = request.customer
    if options['search']:
        data = list(Collection.objects.filter(
            customer=customer, role=Collection.GROUP))
    else:
        data = list(Collection.objects.filter(
            customer=customer, role=Collection.GROUP, level=0))

    if options['search']:
        data = filter(
            lambda c: c.satisfies_search(options['search']), data)

    if options['search']:
        rendered = [
            render_to_string(
                'manage_collections/group_normal_block.html',
                {'group': group},
                RequestContext(request))
            for group in data
        ]
    else:
        rendered = [
            render_to_string(
                'manage_collections/group_block.html',
                {'groups': group.get_descendants(include_self=True)
                 .filter(role=Collection.GROUP)},
                RequestContext(request))
            for group in data
        ]

    return {
        'total': len(data),
        'data': rendered,
    }


@customer_admin_or_error
@render_to('manage_collections/group_form.html')
def group_form(request, pk=None):
    customer = request.customer
    if pk:
        instance = get_object_or_404(Collection, pk=pk)
        if instance.customer != customer:
            return HttpResponseForbidden()
        reason = instance.get_delete_prevention_reason()
    else:
        reason = None
        instance = None

    form = CollectionForm(instance=instance, auto_id=False)

    return {
        'form': form,
        'delete_prevention_reason': reason
    }


# parent = 0 means no change in parent.
# parent > 0 is the id of the parent
# parent = None means no parent
@customer_admin_or_error
@json_response
def group_update(request, pk=None):
    if pk:
        instance = get_object_or_404(
            Collection.objects.filter(role=Collection.GROUP), pk=pk)
        old_parent = instance.parent
    else:
        instance = None
        old_parent = None

    form = CollectionForm(request.POST, instance=instance, auto_id=False)
    if form.is_valid():
        group = form.save(commit=False)
        group.role = Collection.GROUP
        group.utility_type = utilitytypes.OPTIONAL_METER_CHOICES.unknown
        group.save()

        if old_parent == group.parent:
            parent = 0
        else:
            if group.parent is not None:
                parent = group.parent.id
            else:
                parent = None

        return {
            'success': True,
            'statusText': _('The group has been saved'),
            'html': render_to_string(
                'manage_collections/group_normal_block.html',
                {'group': group},
                RequestContext(request)
            ),
            'parent': parent,
        }
    else:
        return {
            'success': False,
            'html': render_to_string(
                'manage_collections/group_form.html',
                {
                    'form': form,
                },
                RequestContext(request)
            ),
        }


@auth_or_error
@json_response
def measurementpoints_list_json(request, group_id):
    group = get_object_or_404(Collection, pk=group_id)
    options = json_list_options(request)
    data = list(group.children.filter(
        graph__isnull=False).distinct().select_related('collection'))
    if options['search']:
        data = filter(
            lambda mp: mp.satisfies_search(options['search']), data)
    order_map = {
        'group': lambda coll: unicode(coll.parent),
        'name': lambda coll: unicode(coll.name),
    }
    if options['order_by'] and options['order_by'] in order_map:
        data.sort(key=order_map[options['order_by']])
    if options['direction'].lower() == 'desc':
        data.reverse()
    data_slice = data[options['offset']:options['offset'] + options['count']]
    rendered = [
        render_to_string(
            'manage_measurementpoints/block.html',
            {'graph_collection': measurementpoints, },
            RequestContext(request))
        for measurementpoints in data_slice
    ]
    return {
        'total': len(data),
        'data': rendered,
    }


class NoUrlClearableFileInput(ClearableFileInput):
    template_with_initial = '%(clear_template)s<br />%(input_text)s: %(input)s'


class FloorplanForm(ModelForm):
    image = ImageField(
        widget=NoUrlClearableFileInput,
        error_messages={'required': _('Browse and select an image first')})

    class Meta:
        model = Floorplan
        fields = ('image',)
        localized_fields = '__all__'


@render_to('manage_collections/group_floorplan.html')
def floorplan(request, pk):
    """
    Renders an image upload form, L{FloorPlanForm}.

    If a floor plan has previously been created for the group with id C{pk}, a
    list of measurement points (C{collections}) that can be placed on the floor
    plan, and a list of measurement points that has already been placed on the
    floor plan (C{placed_collections}) is rendered too.

    Placement of measurement points is handled in another view.
    """
    group = get_object_or_404(Collection, pk=pk)

    floorplan = group.get_floorplan()
    if floorplan:
        items = [item.subclass_instance for item in floorplan.item_set.all()]
    else:
        items = []

    collections = group.get_descendants(
        include_self=False).\
        exclude(collectionitem__floorplan__collection=group)

    if request.method == 'POST':
        form = FloorplanForm(
            request.POST, request.FILES,
            instance=floorplan)
        if form.is_valid():
            floorplan = form.save(commit=False)
            floorplan.collection = group
            floorplan.save()
    else:
        form = FloorplanForm(instance=floorplan)

    return {
        'object': group,
        'form': form,
        'collections': collections,
        'placed_items': items
    }


class UpdateInfoItemForm(forms.ModelForm):
    class Meta:
        model = InfoItem
        fields = ['info']
        localized_fields = '__all__'


@require_POST
@json_response
def save_info_item(request):
    item = get_object_or_404(InfoItem, pk=request.POST['pk'])
    form = UpdateInfoItemForm(request.POST, instance=item)
    if form.is_valid():
        item.save()

    return {
        'id': item.id
    }


class AddCollectionItemForm(forms.ModelForm):

    class Meta:
        model = CollectionItem
        fields = ['x', 'y', 'z', 'collection']
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super(AddCollectionItemForm, self).__init__(*args, **kwargs)
        self.instance.floorplan = group.floorplan
        self.fields['collection'].queryset = group.get_descendants(
            include_self=False)


class AddInfoItemForm(forms.ModelForm):

    class Meta:
        model = InfoItem
        fields = ['x', 'y', 'z']
        localized_fields = '__all__'

    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super(AddInfoItemForm, self).__init__(*args, **kwargs)
        self.instance.floorplan = group.floorplan


@require_POST
@json_response
def place_item(request, pk):
    group = get_object_or_404(Collection, pk=pk)
    if group.customer != get_customer():
            return HttpResponseForbidden()
    form = AddCollectionItemForm(request.POST, group=group)
    item = form.save()
    item.save()

    return {
        'id': item.id
    }


class UpdateItemForm(forms.ModelForm):

    class Meta:
        model = Item
        fields = ['x', 'y']
        localized_fields = '__all__'


@require_POST
@json_response
def update_placement(request):
    item = get_object_or_404(Item, pk=request.POST['pk'])
    form = UpdateItemForm(request.POST, instance=item)
    form.save()

    return {
        'id': item.id
    }


@require_POST
@json_response
def place_infoitem(request, pk):
    group = get_object_or_404(Collection, pk=pk)
    if group.customer != get_customer():
            return HttpResponseForbidden()
    form = AddInfoItemForm(request.POST, group=group)
    item = form.save()
    return {
        'id': item.id
    }


@json_response
def remove_item(request):

    removedItem = Item.objects.get(pk=int(request.GET['item']))
    if removedItem.floorplan.collection.customer != get_customer():
        return HttpResponseForbidden()
    items = removedItem.floorplan.item_set.filter(z__gt=removedItem.z)
    removedItem.delete()
    for item in items:
        item.z = item.z - 1
        item.save()

    return {
        'success': True,
    }
