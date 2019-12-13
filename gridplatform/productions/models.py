# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import re

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from model_utils import Choices
from model_utils import FieldTracker

import gridplatform.datasequences.models
from gridplatform.datasequences.utils import add_ranged_sample_sequences
from gridplatform.customers.mixins import EncryptionCustomerFieldMixin
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.fields import EncryptedTextField
from gridplatform.encryption.models import EncryptedModel
from gridplatform.trackuser.managers import CustomerBoundManager
from gridplatform.utils import development_sum
from gridplatform.utils.fields import BuckinghamField
from gridplatform.utils.api import next_valid_date_for_datasequence
from gridplatform.utils.api import previous_valid_date_for_datasequence


class Production(gridplatform.datasequences.models.AccumulationBase):
    """
    An accumulation data sequence for production.  This is a specialization of
    :class:`gridplatform.datasequences.models.AccumulationBase`.

    :cvar STATIC_UNIT_CHOICES: Choices for the ``unit`` field.
        ``STATIC_UNIT_CHOICES`` gives too many choices, so creation forms
        should really use the ``unit_choices`` property.  A default
        :class:`.ModelForm` will be as user friendly as possible without form
        customization regarding the unit field (were there no choices given,
        the default form field would be a text field rather than a choice
        field).
    :ivar unit: The unit of production.  This should never be changed.
    :ivar unit_choices: Dynamic choices for the ``unit`` field.  Gives the
        human readable form of choices for the associated customer.  See also
        :meth:`.Customer.get_production_unit_choices`.
    :ivar period_set: A reverse relation to
        :class:`gridplatform.productions.models.Period` instances that define
        the data of this production data sequence.
    """
    STATIC_UNIT_CHOICES = Choices(
        *('production_%s' % letter for letter in 'abcde'))
    # DO NOT UPDATE
    unit = BuckinghamField(_('unit'), choices=STATIC_UNIT_CHOICES)

    tracker = FieldTracker(fields=['unit'])

    class Meta:
        verbose_name = _('production')
        verbose_name_plural = _('productions')

    @cached_property
    def unit_choices(self):
        return self.customer.get_production_unit_choices()

    def clean(self):
        """
        :raise ValidationError: If ``self.unit`` was updated.
        :raise ValidationError: If ``self.unit`` is not in ``self.unit_choices``.
        """
        previous_unit = self.tracker.previous('unit')
        if previous_unit is not None:
            if previous_unit != self.unit:
                raise ValidationError(
                    {'unit': [ugettext('Cannot be changed.')]})

        if self.unit not in self.unit_choices:
            raise ValidationError({'unit': [ugettext('Invalid choice.')]})

    def get_unit_display(self):
        """
        :return: A human readable representation of ``self.unit``.
        """
        return self.unit_choices[self.unit]


class ProductionGroup(EncryptionCustomerFieldMixin, EncryptedModel):
    """
    A group of :class:`.Production`.

    :ivar customer:  The owning customer.
    :ivar name:  The name of this group.
    :ivar description: A description of this group.
    :ivar productions:  The :class:`.Production` in this group.
    :ivar unit: The unit shared among the :class:`.Production` in this group.
        Updating this field should be avoided.
    :cvar objects:  A :class:`.CustomerBoundManager`.
    """
    name = EncryptedCharField(_('name'), max_length=100)
    description = EncryptedTextField(_('description'), blank=True)

    # WARNING: removing a production from this relation is almost always an
    # error.
    productions = models.ManyToManyField(
        Production, verbose_name=_('productions'), blank=True)

    # TODO: rename to production_unit.
    #
    # TODO: prevent modification.
    unit = BuckinghamField(_('production unit'))

    objects = CustomerBoundManager()

    class Meta:
        verbose_name = _('production group')
        verbose_name_plural = _('production groups')

    def save(self, *args, **kwargs):
        """
        :precondition: ``self.unit`` matches 'production_[abcde]'.
        """
        assert re.match('production_[abcde]', self.unit), self.unit
        return super(ProductionGroup, self).save(*args, **kwargs)

    def clean(self):
        """
        :raise ValidationError: If ``self.unit`` is not found in the choices
            returned by :meth:`.Customer.get_production_unit_choices` for the
            owning :class:`.Customer`.
        """
        if self.unit not in self.customer.get_production_unit_choices():
            raise ValidationError({'unit': ugettext('Invalid choice.')})

    def __unicode__(self):
        return self.name_plain

    # TODO: rename to production_sum
    def development_sum(self, from_timestamp, to_timestamp):
        """
        :return: The total production of all :class:`.Production` in this
            :class:`.ProductionGroup` in the given timespan.
        :rtype: :class:`.PhysicalQuantity`

        :param from_timestamp:  The start of the given timespan.
        :param to_timestamp:  The end of the given timespan.
        """
        return development_sum(
            self.productions.all(), self.unit, from_timestamp, to_timestamp)

    def production_sequence(self, from_timestamp, to_timestamp, resolution):
        """
        Ranged sample sequence of productions between ``from_timestamp`` and
        ``to_timestamp`` with given ``resolution``.
        """
        return add_ranged_sample_sequences(
            [
                production.development_sequence(
                    from_timestamp, to_timestamp, resolution)
                for production in self.productions.all()
            ],
            from_timestamp, to_timestamp, resolution)

    def next_valid_date(self, date, timezone):
        """
        :return: The next date with data among ``self.productions``. If no
            such date exist, ``None`` is returned.

        :param date: The date to find a date after.
        :param tzinfo timezone: The timezone used to translate dates into
            timestamp ranges.
        """
        return next_valid_date_for_datasequence(
            self.productions.all(), date, timezone)

    def previous_valid_date(self, date, timezone):
        """
        :return: The previous date with data among ``self.productions``. If no
            such date exist, ``None`` is returned.

        :param date: The date to find a date before.
        :param tzinfo timezone: The timezone used to translate dates into
            timestamp ranges.
        """
        return previous_valid_date_for_datasequence(
            self.productions.all(), date, timezone)


class Period(gridplatform.datasequences.models.AccumulationPeriodBase):
    """
    Base class for periods of :class:`.Production`.  This is a specialization
    of :class:`gridplatform.datasequences.models.AccumulationPeriodBase`.

    :ivar datasequence:  The :class:`.Production` this period is part of.
    """
    datasequence = models.ForeignKey(
        Production,
        verbose_name=_('data sequence'),
        editable=False)

    class Meta:
        verbose_name = _('production period')
        verbose_name_plural = _('production periods')


class NonpulsePeriod(
        gridplatform.datasequences.models.NonpulseAccumulationPeriodMixin,
        Period):
    """
    A specialization of :class:`gridplatform.productions.models.Period` mixed
    with
    :class:`gridplatform.datasequences.models.NonpulseAccumulationPeriodMixin`

    Defines a period of a :class:`.Production` in terms of a nonpulse data
    source.
    """

    class Meta:
        verbose_name = _('non-pulse production period')
        verbose_name_plural = _('non-pulse production periods')


class PulsePeriod(
        gridplatform.datasequences.models.PulseAccumulationPeriodMixin,
        Period):
    """
    A specialization of :class:`gridplatform.productions.models.Period` mixed
    with
    :class:`gridplatform.datasequences.models.PulseAccumulationPeriodMixin`

    Defines a period of a :class:`.Production` in terms of a pulse data source.
    """

    class Meta:
        verbose_name = _('pulse production period')
        verbose_name_plural = _('pulse production periods')


class SingleValuePeriod(
        gridplatform.datasequences.models.SingleValueAccumulationPeriodMixin,
        Period):
    """
    A specialization of :class:`gridplatform.productions.models.Period` mixed
    with
    :class:`gridplatform.datasequences.models.SingleValueAccumulationPeriodMixin`

    Defines a period of a :class:`.Production` in terms of a fixed value.
    """

    class Meta:
        verbose_name = _('single value production period')
        verbose_name_plural = _('single value production periods')


class OfflineTolerance(
        gridplatform.datasequences.models.OfflineToleranceMixin):
    """
    A :class:`gridplatform.datasequences.models.OfflineToleranceMixin`
    specialization for :class:`.Production`.

    :ivar datasequence: The :class:`.Production` for which this offline
        tolerance is defined.
    """
    datasequence = models.OneToOneField(
        Production,
        editable=False)
