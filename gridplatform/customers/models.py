# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import random

import pytz
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.models import TimeStampedModel
from south.modelsinspector import add_introspection_rules
from timezones2.models import TimeZoneField

from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.fields import EncryptedEmailField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.encryption.models import EncryptionKey
from gridplatform.trackuser import get_user
from gridplatform.utils import deprecated
from gridplatform.utils import utilitytypes
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.units import CURRENCY_CHOICES
from gridplatform.utils.units import ENERGY_CHOICES
from gridplatform.utils.units import POWER_CHOICES
from gridplatform.utils.units import TEMPERATURE_CHOICES
from gridplatform.utils.units import VOLUME_CHOICES
from gridplatform.utils.units import VOLUME_FLOW_CHOICES
from gridplatform.utils.units import WATT_HOUR_ENERGY_CHOICES
from gridplatform.utils.units import WATT_POWER_CHOICES

from .managers import CustomerManager


add_introspection_rules([], ["^timezones2\.models\.TimeZoneField"])


def get_default_provider():
    # NOTE: Currently getting id rather than object, to avoid attempting to
    # decrypt, to avoid crashing in existing fixture_hack code.
    from gridplatform.providers.models import Provider
    return Provider.objects.order_by(
        'id').values_list('id', flat=True).first()


class Customer(EncryptedModel, TimeStampedModel):
    """
    Represents a GridManager customer.  Customer is the target of foreign keys
    from various other models.

    :ivar id: The ``id`` for customers is randomly generated on creation/first
        save.  The ``id`` is randomized to hide the number of customers from
        our users.
    :ivar provider: A foreign key to the
        :class:`~gridplatform.providers.models.Provider` that facilitates the
        energy management system to this customer.
    :ivar name:
    :ivar vat: The VAT number of this customer.
    :ivar address:
    :ivar postal_code:  The zip code of this customer.
    :ivar city:
    :ivar phone:
    :ivar country_code:
    :ivar timezone:  The timezone in which the customer operates.

    Details of contact person:

    :ivar contact_name:
    :ivar contact_email:
    :ivar contact_phone:

    Various preferred units applied in GridPortal 2.0.  These are not used
    elsewhere in the gridplatform.

    :ivar electricity_instantaneous: Preferred unit for electric power.
    :ivar electricity_consumption: Preferred unit for electric energy.
    :ivar gas_instantaneous:  Preferred unit for volume flow of gas.
    :ivar gas_consumption: Preferred unit for gas volume.
    :ivar water_instantaneous: Preferred unit for volume flow of water.
    :ivar water_consumption: Preferred unit for water volume.
    :ivar heat_instantaneous: Preferred unit for thermal power of district heating.
    :ivar heat_consumption:  Preferred unit for thermal energy of district heating.
    :ivar temperature: Preferred unit for temperatures.  Note that these need
        not be bucking ham units.
    :ivar oil_instantaneous:  Preferred unit for volume flow of oil.
    :ivar oil_consumption:  Preferred unit for oil volume.
    :ivar currency_unit:  Customers unit of currency.
    :ivar electricity_tariff:  Default tariff for new electricity measurement points.
    :ivar gas_tariff: Default tariff for new gas measurement points.
    :ivar water_tariff: Default tariff for new water measurement points.
    :ivar heat_tariff: Default tariff for new district heating measurement points.
    :ivar oil_tariff: Default tariff for new oil measurement points.

    Filtering specific columns:

    :ivar is_active: A Boolean indicating if customer is active. Inactive
        customers will be filtered out by
        :class:`~gridplatform.customers.managers.CustomerManager`.

    The units ``"production_a"`` ... ``"production_e"`` identify per
    customer unit dimensions whose human readable representation is defined by
    the following fields:

    :ivar production_a_unit:
    :ivar production_b_unit:
    :ivar production_c_unit:
    :ivar production_d_unit:
    :ivar production_e_unit:

    Energy manager specific fields:

    Additional meta data fields:

    :ivar created_by: The :class:`~gridplatform.users.models.User` that created
        this customer.
    """
    id = models.IntegerField(primary_key=True, editable=False)
    provider = models.ForeignKey(
        'providers.Provider', editable=False, default=get_default_provider)
    name = EncryptedCharField(
        _('name'), max_length=50, blank=False)
    vat = EncryptedCharField(
        _('VAT no.'), max_length=20, blank=True)
    address = EncryptedCharField(
        _('address'), max_length=50, blank=True)
    postal_code = EncryptedCharField(
        _('postal code'), max_length=10, blank=True)
    city = EncryptedCharField(
        _('city'), max_length=30, blank=True)
    phone = EncryptedCharField(
        _('phone'), max_length=50, blank=True)
    country_code = EncryptedCharField(
        _('country code'), max_length=3, blank=True)
    timezone = TimeZoneField()
    # Contact person details
    contact_name = EncryptedCharField(
        _('contact person'), max_length=50, blank=True)
    contact_email = EncryptedEmailField(
        _('e-mail'), max_length=50, blank=True)
    contact_phone = EncryptedCharField(
        _('phone'), max_length=50, blank=True)
    # Preferred units
    electricity_instantaneous = models.CharField(
        _('Electricity instantaneous unit'), choices=WATT_POWER_CHOICES,
        default="kilowatt", max_length=50)
    electricity_consumption = models.CharField(
        _('Electricity consumption unit'), choices=WATT_HOUR_ENERGY_CHOICES,
        default="kilowatt*hour", max_length=50)
    gas_instantaneous = models.CharField(
        _('Gas instantaneous unit'), choices=VOLUME_FLOW_CHOICES,
        default="meter*meter*meter*hour^-1", max_length=50)
    gas_consumption = models.CharField(
        _('Gas consumption unit'), choices=VOLUME_CHOICES,
        default="meter*meter*meter", max_length=50)
    water_instantaneous = models.CharField(
        _('Water instantaneous unit'), choices=VOLUME_FLOW_CHOICES,
        default="meter*meter*meter*hour^-1", max_length=50)
    water_consumption = models.CharField(
        _('Water consumption unit'), choices=VOLUME_CHOICES,
        default="meter*meter*meter", max_length=50)
    heat_instantaneous = models.CharField(
        _('Heat instantaneous unit'), choices=POWER_CHOICES,
        default="kilowatt", max_length=50)
    heat_consumption = models.CharField(
        _('Heat consumption unit'), choices=ENERGY_CHOICES,
        default="kilowatt*hour", max_length=50)
    temperature = models.CharField(
        _('Temperature unit'), choices=TEMPERATURE_CHOICES,
        default="celsius", max_length=50)
    oil_instantaneous = models.CharField(
        _('Oil instantaneous unit'), choices=VOLUME_FLOW_CHOICES,
        default="meter*meter*meter*hour^-1", max_length=50)
    oil_consumption = models.CharField(
        _('Oil consumption unit'), choices=VOLUME_CHOICES,
        default="meter*meter*meter", max_length=50)
    currency_unit = BuckinghamField(_('currency'), choices=CURRENCY_CHOICES,
                                    default='currency_dkk')

    electricity_tariff = models.ForeignKey(
        "measurementpoints.DataSeries", related_name="electricity_tariff_set",
        blank=True, null=True)
    gas_tariff = models.ForeignKey(
        "measurementpoints.DataSeries", related_name="gas_tariff_set",
        blank=True, null=True)
    water_tariff = models.ForeignKey(
        "measurementpoints.DataSeries", related_name="water_tariff_set",
        blank=True, null=True)
    heat_tariff = models.ForeignKey(
        "measurementpoints.DataSeries", related_name="heat_tariff_set",
        blank=True, null=True)
    oil_tariff = models.ForeignKey(
        "measurementpoints.DataSeries", related_name="oil_tariff_set",
        blank=True, null=True)

    is_active = models.BooleanField(_('is active'), default=True)

    production_a_unit = EncryptedCharField(
        _('production A unit'), max_length=50, blank=True)

    production_b_unit = EncryptedCharField(
        _('production B unit'), max_length=50, blank=True)

    production_c_unit = EncryptedCharField(
        _('production C unit'), max_length=50, blank=True)

    production_d_unit = EncryptedCharField(
        _('production D unit'), max_length=50, blank=True)

    production_e_unit = EncryptedCharField(
        _('production E unit'), max_length=50, blank=True)

    created_by = models.ForeignKey(
        'users.User',
        related_name='+',
        null=True,
        editable=False)

    objects = CustomerManager()

    class Meta:
        verbose_name = _('customer')
        verbose_name_plural = _('customers')
        ordering = ['id']

    def clean_fields(self, exclude=None):
        """
        :raise ValidationError: if an applied production unit is cleared.
        """
        super(Customer, self).clean_fields(exclude)

        def clean_production_unit(letter):
            do_check_production_unit = (
                exclude is None or exclude is not None and
                'production_%s_unit' % letter not in exclude)
            production_unit_is_set = getattr(
                self, 'production_%s_unit_plain' % letter)
            data_series_using_production_unit = self.dataseries_set.filter(
                unit='production_%s' % letter)

            if do_check_production_unit and \
                    not production_unit_is_set and \
                    data_series_using_production_unit.exists():
                raise ValidationError(
                    _(
                        'Production unit {production_unit_letter} is in use '
                        'and cannot be empty').format(
                        production_unit_letter=letter.upper()))
        for letter in ['a', 'b', 'c', 'd', 'e']:
            clean_production_unit(letter)

    def __unicode__(self):
        return unicode(self.name_plain or self.name)

    def save(self, *args, **kwargs):
        """
        Initializes ``id`` to something random on initial save.
        """
        if not self.id:
            self.created_by = get_user()

            # NOTE: Will fail if another customer is assigned the same random
            # ID between the exists-check and the save --- for now, we assume
            # that the occasion of several customers being added in the same
            # millisecond and the random-generator returning the same number
            # for each is sufficiently unlikely that we won't add code to
            # handle it.  (... apart from the force_insert, so at least we
            # would get an error rather than overwriting existing data...)
            #
            # ID is random from 1 to 10^8 - 1 inclusive --- printable as 8
            # decimal digits, no customer gets ID 0, representable in signed
            # and unsigned 32-bit.

            id = random.randint(1, (10 ** 8) - 1)
            while Customer.objects.filter(id=id).exists():
                id = random.randint(1, (10 ** 8) - 1)

            # HACK: Create other customer object to get encryption set up
            # before we actually store encrypted fields
            if self.provider_id:
                tmp_customer = Customer(provider_id=self.provider_id)
            else:
                tmp_customer = Customer()
            tmp_customer.id = id
            tmp_customer.save(force_insert=True, force_update=False)
            self.id = tmp_customer.id
            # NOTE: Create encryption key to enable logic
            # for sharing key with users on provider associated with
            # customer...
            EncryptionKey.generate((Customer, self.id))

            opts = kwargs.copy()
            opts.update({'force_insert': False, 'force_update': True})
            super(Customer, self).save(*args, **opts)
        else:
            opts = {'force_update': True}
            opts.update(kwargs)
            super(Customer, self).save(*args, **opts)

    @deprecated
    def get_preffered_tariff(self, utility_type):
        if utility_type == utilitytypes.METER_CHOICES.electricity:
            return self.electricity_tariff
        elif utility_type == utilitytypes.METER_CHOICES.gas:
            return self.gas_tariff
        elif utility_type == utilitytypes.METER_CHOICES.water:
            return self.water_tariff
        elif utility_type == utilitytypes.METER_CHOICES.district_heating:
            return self.heat_tariff
        elif utility_type == utilitytypes.METER_CHOICES.oil:
            return self.oil_tariff
        raise ValueError('unsupported utility type: %r' % utility_type)

    @deprecated
    def count_measurementpoints(self):
        # WTF?  (Number of collections with graphs?)
        return self.collection_set.filter(
            graph__isnull=False).distinct().count()

    @deprecated
    def count_collections(self):
        # WTF?  (Number of collections without graphs?)
        return self.collection_set.filter(
            graph__isnull=True).distinct().count()

    @deprecated
    def count_agents(self):
        return {
            'total': self.agent_set.count(),
            'online': self.agent_set.filter(online=True).count(),
            'offline': self.agent_set.filter(online=False).count(),
        }

    @deprecated
    def count_meters(self):
        return {
            'total': self.meter_set.count(),
            'online': self.meter_set.filter(online=True).count(),
            'offline': self.meter_set.filter(online=False).count(),
        }

    def now(self):
        """
        A :class:`~datetime.datetime` object representing the current time in this
        :class:`.Customer`'s timezone.
        """
        tz = self.timezone
        if isinstance(tz, basestring):
            tz = pytz.timezone(tz)
        return tz.normalize(datetime.datetime.now(tz))

    def get_encryption_id(self):
        """
        Implementation of abstract method declared by
        :class:`gridplatform.encryption.models.EncryptedModel`.
        """
        return (Customer, self.id)

    def satisfies_search(self, search):
        """
        Implementation of interface required by
        :py:func:`gridplatform.utils.views.json_list_response` view function
        decorator.

        :param search:  A string to search for.

        :return: True if the ``search`` argument is found in any relevant
            property of this customer.
        """
        elems = [
            self.name_plain,
            self.address_plain,
            self.postal_code_plain,
            self.country_code_plain,
        ]
        search = search.lower()
        return any([search in unicode(elem).lower() for elem in elems])

    def get_production_unit_choices(self):
        """
        Production unit choices for forms.

        :return: A Choices object of non-empty production units.  The database
            representation will be the relevant buckingham unit, and the human
            readable representation will be the decrypted contents of the
            corresponding production unit field.
        """
        result_tuples = []

        for letter in ['a', 'b', 'c', 'd', 'e']:
            plain_text = getattr(self, 'production_%s_unit_plain' % letter)
            unit = 'production_%s' % letter
            if plain_text:
                result_tuples.append((unit, plain_text))

        return Choices(*result_tuples)
