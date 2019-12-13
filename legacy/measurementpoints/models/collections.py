# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime

import pytz
from django.db import models
from mptt.models import MPTTModel
from mptt.models import TreeForeignKey
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit
from imagekit.models import ImageSpecField
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _

from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.trackuser.managers import TreeCustomerBoundManager
from gridplatform.trackuser.managers import StoredSubclassTreeCustomerBoundManager  # noqa
from gridplatform.trackuser import get_customer
from gridplatform.trackuser import get_user
from gridplatform.encryption.models import EncryptedModel
from gridplatform.utils.models import StoreSubclass
from gridplatform.customers.models import Customer
from gridplatform.utils import utilitytypes
from gridplatform.utils.units import INPUT_CHOICES
from gridplatform.encryption.fields import EncryptedTextField


class CollectionManager(StoredSubclassTreeCustomerBoundManager):
    """
    Manager for L{Collection}s
    """

    def get_query_set(self):
        customer = get_customer()
        user = get_user()

        qs = super(CollectionManager, self).get_query_set()

        if customer is None or user is None:
            return qs

        constrained_collection_ids = list(
            CollectionConstraint.objects.filter(
                userprofile__user=user).
            values_list('collection_id', flat=True))

        if constrained_collection_ids:
            collection_ids = set()
            root_collections = qs.filter(id__in=constrained_collection_ids)
            for root_collection in root_collections:
                if root_collection.is_leaf_node():
                    collection_ids.add(root_collection.id)
                    continue
                opts = root_collection._mptt_meta
                left = getattr(root_collection, opts.left_attr)
                right = getattr(root_collection, opts.right_attr)
                if not hasattr(self, '_base_manager'):
                    self.init_from_model(self.model)
                collection_ids.update(
                    self._mptt_filter(
                        qs,
                        tree_id=root_collection._mpttfield('tree_id'),
                        left__gte=left,
                        left__lte=right).
                    values_list('id', flat=True))
            return qs.filter(id__in=collection_ids)
        else:
            return qs


class Collection(MPTTModel, EncryptedModel, StoreSubclass):
    """
    The way for customers to organise measurement points.  Prices may be
    attached to collections, and then apply to all monitored equipment in that
    collection.  Users may be bound to a set of collections, and will then only
    be able to see monitored equipment in those collections.

    @ivar role: The role that this C{Collection} is used in.

    C{GROUP}: This C{Collection} is strictly used to group other collections.
    This is the default.

    C{CONSUMPTION_GROUP}: This C{Collection} defines a consumption group for a
    module.  The role of all descendants will either be in C{DATA_POINTS} or
    equal C{GROUP}.

    C{MEASUREMENT_POINT} (in C{DATA_POINTS}: A leaf C{Collection} (whith no
    children) holding one or more L{Graph}s.
    """
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT,
                                 blank=True, default=get_customer)
    parent = TreeForeignKey('self', related_name='children',
                            blank=True, null=True)
    name = EncryptedCharField(_('Name'), max_length=50)
    # The next two fields are used for billing meters in Denmark. They are
    # shown as part of the consumption/cost report.
    billing_meter_number = models.CharField(_('meter number'),
                                            max_length=20, blank=True)
    billing_installation_number = models.CharField(
        _('installation number'), max_length=20, blank=True)

    # Design-note: Keep unrelated roles in their own 100s, so that there is
    # room to add new roles in-between.  The hope is that the number of roles
    # will be stabilized before this schema is preempted.
    GROUP = 0

    CONSUMPTION_GROUP = 150

    MEASUREMENT_POINT_TEMPERATURE = 204
    MEASUREMENT_POINT_PRODUCTION = 205
    MEASUREMENT_POINT_CURRENT = 206
    MEASUREMENT_POINT_VOLTAGE = 207
    MEASUREMENT_POINT_POWER = 208
    MEASUREMENT_POINT_EFFICIENCY = 209
    MEASUREMENT_POINT_REACTIVE_POWER = 210
    MEASUREMENT_POINT_REACTIVE_ENERGY = 211
    MEASUREMENT_POINT_POWER_FACTOR = 212
    CONSUMPTION_MEASUREMENT_POINT = 250

    CONSUMPTION_GROUPS = (CONSUMPTION_GROUP,)
    MEASUREMENT_POINTS = (
        MEASUREMENT_POINT_TEMPERATURE,
        MEASUREMENT_POINT_PRODUCTION,
        CONSUMPTION_MEASUREMENT_POINT,
        MEASUREMENT_POINT_CURRENT,
        MEASUREMENT_POINT_VOLTAGE,
        MEASUREMENT_POINT_POWER,
        MEASUREMENT_POINT_REACTIVE_POWER,
        MEASUREMENT_POINT_REACTIVE_ENERGY,
        MEASUREMENT_POINT_POWER_FACTOR,
        MEASUREMENT_POINT_EFFICIENCY,
    )
    DATA_POINTS = MEASUREMENT_POINTS
    PARENTS = (GROUP,)

    ROLE_CHOICES = (
        (GROUP, _('Group')),
        (CONSUMPTION_GROUP, _('Consumption group')),
        (MEASUREMENT_POINT_TEMPERATURE, _('Temperature measurement point')),
        (MEASUREMENT_POINT_PRODUCTION, _('Production measurement point')),
        (MEASUREMENT_POINT_VOLTAGE, _('Voltage measurement point')),
        (MEASUREMENT_POINT_CURRENT, _('Current measurement point')),
        (MEASUREMENT_POINT_POWER, _('Power measurement point')),
        (MEASUREMENT_POINT_REACTIVE_POWER,
         _('Reactive power measurement point')),
        (MEASUREMENT_POINT_REACTIVE_ENERGY,
         _('Reactive energy measurement point')),
        (MEASUREMENT_POINT_POWER_FACTOR, _('Power factor measurement point')),
        (MEASUREMENT_POINT_EFFICIENCY, _('Efficiency measurement point')),
        (CONSUMPTION_MEASUREMENT_POINT, _('Consumption measurement point')),
    )

    # NOTE: Superseded by ContentType. Only used in
    # display_measurementpoints/views.py
    # manage_reports/templates/manage_reports/generate_report.html
    # manage_measurementpoints/forms/consumptionsummation.py
    # customers/models.py and then ofcourse in each and every one of
    # customers/proxies/*.py
    #
    # The question is: is there a ContentType for each role?  Are there any
    # stale ContentTypes?
    #
    # A1: There are ContentTypes without a role, in particular for
    # SummationMeasurementPoint and DistrictHeatingMeasurementPoint.
    #
    # A2: There are also roles without a ContentType, in particular GROUP does
    # not have a ContentType.  It probably should have though.  But that
    # requires data migrations (setting the content type on all collection with
    # role GROUP), so it will wait for now.
    role = models.IntegerField(_("Role"), choices=ROLE_CHOICES)
    utility_type = models.IntegerField(
        _('utility type'), choices=utilitytypes.OPTIONAL_METER_CHOICES)

    gauge_lower_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    gauge_upper_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    gauge_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    gauge_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    gauge_preferred_unit = models.CharField(
        max_length=50, null=True, blank=True, choices=INPUT_CHOICES)

    GREEN_YELLOW_RED = 1
    RED_GREEN_RED = 2
    YELLOW_GREEN_YELLOW = 3
    RED_YELLOW_GREEN = 4

    GAUGE_COLOR_CHOICES = (
        (GREEN_YELLOW_RED, _('green-yellow-red')),
        (RED_GREEN_RED, _('red-green-red')),
        (YELLOW_GREEN_YELLOW, _('yellow-green-yellow')),
        (RED_YELLOW_GREEN, _('red-yellow-green')),
    )
    gauge_colours = models.PositiveIntegerField(
        _('Gauge colours'), choices=GAUGE_COLOR_CHOICES, blank=True, null=True)

    relay = models.ForeignKey("devices.Meter", on_delete=models.PROTECT,
                              null=True, blank=True)

    hidden_on_details_page = models.BooleanField(default=False)

    hidden_on_reports_page = models.BooleanField(default=False)

    comment = EncryptedTextField(blank=True)

    image = ProcessedImageField(
        upload_to='measuremenpoints',
        processors=[ResizeToFit(900, 900, upscale=False)],
        format='JPEG',
        blank=True,
        null=True)

    thumbnail = ImageSpecField(
        source='image',
        processors=[ResizeToFit(100, 50)],
        format='JPEG',
        options={'quality': 90}
    )

    # Removes warning issued by django_mptt-0.5.4
    #
    # DeprecationWarning: Implicit manager Collection.tree will be removed in
    # django-mptt 0.6.  Explicitly define a TreeManager() on your model to
    # remove this warning.
    #
    # See also:
    # http://django-mptt.github.com/django-mptt/upgrade.html\
    #    #treemanager-is-now-the-default-manager-yourmodel-tree-removed
    objects = tree = CollectionManager()

    class Meta:
        # default ordering for MPTTModel instances is tree order
        verbose_name = _('collection')
        verbose_name_plural = _('collections')
        db_table = 'customers_collection'
        app_label = 'customers'

    def __unicode__(self):
        return unicode(self.name_plain)

    def clean(self):
        super(Collection, self).clean()
        if not self.gauge_preferred_unit and getattr(self, 'rate', None):
            preferred_unit_converter = self.rate.get_preferred_unit_converter()
            if hasattr(preferred_unit_converter, 'physical_unit'):
                self.gauge_preferred_unit = \
                    self.rate.get_preferred_unit_converter().physical_unit

    def get_encryption_id(self):
        return (Customer, self.customer_id)

    def satisfies_search(self, search):
        elems = [
            self.name_plain,
        ]
        if self.parent:
            elems.append([self.parent.name_plain])
        search = search.lower()
        return any([search in unicode(elem).lower() for elem in elems])

    def get_floorplan(self):
        """
        Returns the collection floorplan if it exists, else returns None
        """
        if hasattr(self, 'floorplan'):
            return self.floorplan
        else:
            return None

    def is_online(self):
        """
        Check if this MeasurementPoint is online.

        This is done by checking if any measurements are available from the
        last half hour.  Collections that are not MeasurementPoints are
        considered online always (for some reason).

        ... actually; a Collection will only be considered "offline" if it is a
        measurement point, has at least one logical input attached, and none of
        its logical inputs have stored data inside the last 30 minutes; any
        other combination is "online"...

        @deprecated: Similar concept is implemented better and more clean in
        L{Meter.connection_state}
        """
        if not hasattr(self, '_is_online'):
            self._is_online = False
            if self.role not in self.MEASUREMENT_POINTS or \
                    self.get_last_rate() is not None:
                # being online is True by a a post-condition of get_last_rate()
                # given it didn't return None.
                self._is_online = True
            else:
                from legacy.datasequence_adapters.models import ConsumptionAccumulationAdapter  # noqa
                from legacy.datasequence_adapters.models import NonaccumulationAdapter  # noqa

                input_configurations = list(
                    ConsumptionAccumulationAdapter.objects.filter(
                        link_derivative_set__graph__collection=self)) + list(
                    NonaccumulationAdapter.objects.filter(
                        link_derivative_set__graph__collection=self))
                if not input_configurations:
                    self._is_online = True
                else:
                    now = datetime.datetime.now(pytz.utc)
                    half_hour_ago = now - datetime.timedelta(minutes=30)
                    for ic in input_configurations:
                        data = ic.get_samples(half_hour_ago, now)
                        if any([not sample.extrapolated for sample in data]):
                            self._is_online = True
                            break

        return self._is_online

    def get_last_rate(self):
        """
        Get the last rate for this C{MeasurementPoint}.

        @return: Return a C{(v, u)} tuple where v is a numeric value and u is a
        localized unit.  If there is no last rate, None is returned (for
        instance because there is no gauge data series defined for this
        C{MeasurementPoint}, or this C{Collection} is not a C{MeasurementPoint}
        at all).

        @note: The return format C{(v, u)} is intended to be compatible with
        the physicalquantity template filter.
        """
        if not hasattr(self, '_last_rate'):
            self._last_rate = None
            if self.role in self.MEASUREMENT_POINTS:
                mp = self.subclass_instance
                to_timestamp = datetime.datetime.now(pytz.utc).replace(
                    microsecond=0)
                from_timestamp = to_timestamp - datetime.timedelta(minutes=30)
                gauge_data_series = mp.get_gauge_data_series()
                if gauge_data_series:
                    sample = gauge_data_series.latest_sample(
                        from_timestamp, to_timestamp)
                    if sample:
                        preferred_unit_converter = \
                            gauge_data_series.get_preferred_unit_converter()
                        self._last_rate = (
                            preferred_unit_converter.extract_value(
                                sample.physical_quantity),
                            preferred_unit_converter.get_display_unit())
        return self._last_rate

    def get_icon(self):
        if self.role in (self.CONSUMPTION_GROUP,
                         self.CONSUMPTION_MEASUREMENT_POINT):
            if self.utility_type == \
                    utilitytypes.OPTIONAL_METER_CHOICES.electricity:
                return 'electricity'
            elif self.utility_type == \
                    utilitytypes.OPTIONAL_METER_CHOICES.water:
                return 'water'
            elif self.utility_type == utilitytypes.OPTIONAL_METER_CHOICES.gas:
                return 'gas'
            elif self.utility_type == \
                    utilitytypes.OPTIONAL_METER_CHOICES.district_heating:
                return 'heat'
            elif self.utility_type == utilitytypes.OPTIONAL_METER_CHOICES.oil:
                return 'oil'
            else:
                return 'consumption'
        elif self.role == self.MEASUREMENT_POINT_TEMPERATURE:
            return 'temperature'
        elif self.role == self.GROUP:
            return 'group'
        elif self.role == self.MEASUREMENT_POINT_CURRENT:
            return 'electricity'
        elif self.role == self.MEASUREMENT_POINT_VOLTAGE:
            return 'electricity'
        elif self.role == self.MEASUREMENT_POINT_POWER:
            return 'electricity'
        elif self.role == self.MEASUREMENT_POINT_REACTIVE_POWER:
            return 'electricity'
        elif self.role == self.MEASUREMENT_POINT_REACTIVE_ENERGY:
            return 'electricity'
        elif self.role == self.MEASUREMENT_POINT_POWER_FACTOR:
            return 'electricity'
        elif self.role == self. MEASUREMENT_POINT_PRODUCTION:
            return 'production'
        elif self.role == self. MEASUREMENT_POINT_EFFICIENCY:
            return 'efficiency'
        else:
            assert False

    def is_measurementpoint(self):
        return self.role in self.MEASUREMENT_POINTS

    def get_role_display_short(self):
        return {
            Collection.GROUP: _("Group"),

            Collection.CONSUMPTION_GROUP: _('Consumption group'),
            Collection.CONSUMPTION_MEASUREMENT_POINT:
            _('Consumption measurement point'),
            Collection.MEASUREMENT_POINT_TEMPERATURE:
            _('Temperature measurement point'),
            Collection.MEASUREMENT_POINT_CURRENT: _("Current"),
            Collection.MEASUREMENT_POINT_VOLTAGE: _("Voltage"),
            Collection.MEASUREMENT_POINT_POWER: _("Power"),
            Collection.MEASUREMENT_POINT_REACTIVE_POWER: _("Reactive power"),
            Collection.MEASUREMENT_POINT_REACTIVE_POWER: _("Reactive energy"),
            Collection.MEASUREMENT_POINT_POWER_FACTOR: _("Power factor"),
        }[self.role]

    def get_delete_prevention_reason(self):
        """
        Returns a HTML formated string with a description of why
        this collection cannot be deleted.
        Returning None, if no reason exist, meaning the collection can
        be deleted without breaking anything.
        """
        if self.is_deletable():
            return None

        measurementpoints = self.children.filter(
            graph__isnull=False).distinct()
        groups = self.children.filter(graph__isnull=True).distinct()
        dependents = []
        if measurementpoints:
            dependents.append(unicode(_("Measurement Points:")))
            dependents.append('<ul>')
            for mp in measurementpoints:
                dependents.append('<li>%s</li>' % (escape(unicode(mp)),))
            dependents.append('</ul>')
        if groups:
            dependents.append(unicode(_("Collections:")))
            dependents.append('<ul>')
            for group in groups:
                dependents.append('<li>%s</li>' % (escape(unicode(group)),))
            dependents.append('</ul>')
        if dependents:
            return _("This group cannot be deleted because the following \
                     depends on it:") + "<br />" + "".join(dependents)

    def is_deletable(self):
        """
        Returns true or false whether
        this collection can be deleted or not.
        """
        if self.children.all():
            return False
        return True


# NOTE: Bound to auto-create on user-create in portal.website.models.
# This app may be used without the auto-create from outside the portal.

class CollectionConstraint(models.Model):
    """
    A {CollectionConstraint} is the relation between L{UserProfile}s and
    L{Collection}s. This relation "table" has been created to prevent a
    Collection to be deleted if a User and the Collection has a relation.
    """
    userprofile = models.ForeignKey(
        'customers.UserProfile', on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT)

    class Meta:
        db_table = 'customers_userprofile_collections'
        app_label = 'customers'


class Location(MPTTModel, EncryptedModel):
    """
    The way for customers to organise agents and meters, i.e. physical
    equipment.  Locations are organised as one or more tree structures per
    customer.
    """
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        blank=True, default=get_customer)
    parent = TreeForeignKey('self', on_delete=models.PROTECT,
                            related_name='children', blank=True, null=True)
    name = EncryptedCharField(_('name'), max_length=50)

    objects = TreeCustomerBoundManager()

    class Meta:
        # default ordering for MPTTModel instances is tree order
        verbose_name = _('location')
        verbose_name_plural = _('locations')
        db_table = 'customers_location'
        app_label = 'customers'

    def __unicode__(self):
        return unicode(self.name_plain)

    def get_encryption_id(self):
        return (Customer, self.customer_id)

    def satisfies_search(self, search):
        return search.lower() in unicode(self).lower()
