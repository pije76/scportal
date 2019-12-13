# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.views.generic import TemplateView, DetailView

from gridplatform.users.decorators import auth_or_redirect
from gridplatform.utils.views import FileView
from legacy.measurementpoints.models import Collection
from legacy.manage_collections.models import Floorplan

urlpatterns = patterns(
    'legacy.manage_collections.views',
    url(r'^$',
        auth_or_redirect(TemplateView.as_view(
            template_name='manage_collections/group_list.html')),
        name='manage-groups-list'),
    url(r'^form/$',
        'group_form',
        name='manage-groups-form'),
    url(r'^form/(?P<pk>\d+)$',
        'group_form',
        name='manage-groups-form'),
    url(r'^json/groups/$',
        'group_list_json',
        name='manage-groups-list-json'),
    url(r'^update/$',
        'group_update',
        name='manage-groups-update'),
    url(r'^update/(?P<pk>\d+)$',
        'group_update',
        name='manage-groups-update'),
    url(r'^delete/$',
        'group_delete',
        name='manage-groups-delete'),
    url(r'^(?P<pk>\d+)$',
        auth_or_redirect(DetailView.as_view(
            model=Collection,
            template_name='manage_collections/group_details.html')),
        name='manage-groups-details'),
    url(r'^json/measurementpoints/(?P<group_id>\d+)$',
        'measurementpoints_list_json',
        name='manage-groups-measurementpoints-list-json'),
    url(r'^floorplan/(?P<pk>\d+)$',
        'floorplan',
        name='manage-groups-floorplan'),
    url(r'^floorplan/(?P<pk>\d+)/image$',
        FileView.as_view(model=Floorplan, field='image'),
        name='manage-groups-floorplan_image'),
    url(r'^collection/(?P<pk>\d+)/image$',
        FileView.as_view(model=Collection, field='image'),
        name='manage-groups-collection_image'),
    url(r'^collection/(?P<pk>\d+)/thumbnail$',
        FileView.as_view(model=Collection, field='thumbnail'),
        name='manage-groups-collection_thumbnail'),
    url(r'^floorplan/additem/(?P<pk>\d+)$',
        'place_item',
        name='manage-groups-place_item'),
    url(r'^floorplan/addinfoitem/(?P<pk>\d+)$',
        'place_infoitem',
        name='manage-groups-place_infoitem'),
    url(r'^floorplan/updateplacement/$',
        'update_placement',
        name='manage-groups-update_placement'),
    url(r'^floorplan/removeitem$',
        'remove_item',
        name='manage-groups-remove_item'),
    url(r'^floorplan/saveinfoitem$',
        'save_info_item',
        name='manage-groups-save_info_item'),
)
