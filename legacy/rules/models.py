# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Django model for rules.

There are two sides of rules:

     - The user rules, which are given by the user, and are
       declarative and generic.  User rules are stored in the
       database, and considered an internal part of the L{Rule} Django
       model.

     - The agent rules, which are generated from user rules, price
       tables and other forms of indexes, and interpreted by agents.
       These are not stored in the database, but generated on the fly
       as they are needed, see also L{Rule.generate_rules()}.
       These are defined by the L{AgentRule} class.
"""

import contextlib
import operator as python_operator
import datetime
import urllib
import math
import urllib2
import warnings
from smtplib import SMTPException

from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from timezones2.models import TimeZoneField

from gridplatform.customers.models import Customer
from legacy.devices.models import Meter
from gridplatform.encryption.fields import EncryptedCharField
from gridplatform.encryption.models import EncryptedModel
from legacy.ipc import agentserver
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.trackuser import get_customer
from gridplatform.trackuser.managers import CustomerBoundManager
from gridplatform.trackuser import get_timezone
from gridplatform.utils import units
from gridplatform.utils.fields import DurationField
from gridplatform.utils.relativetimedelta import RelativeTimeDelta
from gridplatform.utils.unitconversion import PhysicalQuantity

from . import UserRuleIntegrityError


TURN_OFF = 0
TURN_ON = 1


class UserRule(EncryptedModel):
    """
    Model representing rules.

    Rules controls relays and sends out warnings to users, usually
    with the goal to minimize energy expenses.  This is done by
    monitoring various meters, and processing energy price forecasts,
    and similar indexes.

    The user defines user rules, which are the declarative, generic
    and unprocessed form of rules.

    User rules are processed against energy price forecasts and
    similar indexes to generate agent rules.  This is done by the
    L{generate_rules()} method.

    Each rule is specified in terms of weekdays and local time, to allow
    specification of control rules corresponding to relevant employee work
    schedules.

    A rule is I{active} in time intervals specified through weekdays,
    L{DateException} objects, L{from_time} and L{to_time}, as well as the
    L{enabled} switch.  During periods while a rule is active, it will,
    depending on the rule type and specific conditions, have zero or more
    periods of I{activity}.  When a period of I{activity} begins, a number of
    C{INITIAL} L{Action}s are taken, and when the period of I{activity} ends, a
    number of C{FINAL} L{Action}s are taken.

    @ivar customer: A customer which the rule is bound to.
    @ivar name: A human-readable name.
    @ivar enabled: Declares whether this rule should be processed/acted on.
    @ivar timezone: Timezone used ot interpret L{from_time} and L{to_time}.

    @groups Weekdays: *day
    @ivar monday: Whether this rule should be enabled on mondays.
    @ivar tuesday: Whether this rule should be enabled on tuesdays.
    @ivar wednesday: Whether this rule should be enabled on wednesdays.
    @ivar thursday: Whether this rule should be enabled on thursdays.
    @ivar friday: Whether this rule should be enabled on fridays.
    @ivar saturday: Whether this rule should be enabled on saturdays.
    @ivar sunday: Whether this rule should be enabled on sundays.

    @ivar from_time: Local time when the rule becomes enabled.  The specified
    weekdays are the days where the rule becomes enabled at C{from_time}.
    @ivar to_time: Local time when the rule becomes disabled.  If C{to_time <=
    from_time}, this specifies a timestamp on the following day.

    @ivar content_type: Actual type of the rule; otherwise not available when
    initialising objects from the base UserRule database table.
    @ivar content_object: Descriptor for obtaining a corresponding object of
    the appropriate subclass.

    @attention: We assume that only one level of subclasses of this will be
    used.  If/when this is not the case, the code in C{__init__} and C{save}
    may need to be updated.
    """

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        editable=False, blank=True, default=get_customer)
    name = EncryptedCharField(_('name'), max_length=50, blank=False)
    enabled = models.BooleanField(_('enabled'), default=True)
    timezone = TimeZoneField(_('timezone'), default=get_timezone)

    # active on days:
    monday = models.BooleanField(_('Monday'), default=True)
    tuesday = models.BooleanField(_('Tuesday'), default=True)
    wednesday = models.BooleanField(_('Wednesday'), default=True)
    thursday = models.BooleanField(_('Thursday'), default=True)
    friday = models.BooleanField(_('Friday'), default=True)
    saturday = models.BooleanField(_('Saturday'), default=False)
    sunday = models.BooleanField(_('Sunday'), default=False)
    # in interval:
    # (to_time <= from_time implies "on the following day")
    # @bug: Now these are insane default values.
    from_time = models.TimeField(_('from time'), default=datetime.time())
    to_time = models.TimeField(_('to time'), default=datetime.time())

    # Use generic relation to indicate "concrete" UserRule subclass.
    # content_type indicates type; content_object is purely a convenience
    # wrapper for the object lookup; a custom enumeration would hardly reduce
    # the storage-overhead.  (A custom enumeration might be stored as a shorter
    # integer type, depending on DB-backend; not worth the effort.)

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, editable=False)
    content_object = generic.GenericForeignKey('content_type', 'id')

    objects = CustomerBoundManager()

    class Meta:
        verbose_name = _('user rule')
        verbose_name_plural = _('user rules')
        ordering = ['-to_time', '-from_time', '-enabled', 'id']

    def __unicode__(self):
        return unicode(self.name_plain or self.name)

    def __init__(self, *args, **kwargs):
        super(UserRule, self).__init__(*args, **kwargs)
        if self.__class__ != UserRule and \
                not hasattr(self, '_content_object_cache'):
            # The object is already of the subclass; avoid loading it again
            # when accessing content_object.
            # We check for _content_object_cache, as it may have been set
            # during a callback from the pre_init or post_init signals --- in
            # that case, we won't overwrite it.
            self._content_object_cache = self

    def save(self, *args, **kwargs):
        if not self.id:
            # Initial save/creation *must* be of subclass.  (Later, properties
            # like name may be modified with knowledge of/access to the
            # concrete subclass...)
            assert self.__class__ != UserRule
            self.content_type = ContentType.objects.get_for_model(self)
        super(UserRule, self).save(*args, **kwargs)

    def clean(self):
        """
        Basic validation: Check that the time available between L{from_time}
        and L{to_time} is enough for the activity_duration.

        @raise ValidationError: if the time available is shortare than the time
        required.

        @note: Does not check wrt. timezone.  Rules that are problematic only
        on the switch to DST are not caught; rules that are OK only on the
        switch from DST are still considered in error.
        """
        return None
        available_time = self.to_time - self.from_time
        if available_time <= datetime.timedelta():
            # from_time <= to_time; i.e. to_time should be taken to be next day
            available_time += datetime.timedelta(days=1)
        if available_time < self.activity_duration:
            raise ValidationError(
                _("User rule is self-contradictory. "
                  "The earliest usage end is after interval end"))

    def get_encryption_id(self):
        """
        L{Rule} implementation of L{EncryptedModel.get_encryption_id()}.  The
        C{OwnerModelClass} of the L{Rule} class is L{Customer}.
        """
        return (Customer, self.customer_id)

    def satisfies_search(self, substring):
        """
        Check if this L{Rule} matches a given substring.

        @param substring: The given substring.

        @return: Returns C{True} if the C{substring} is matched by
        this L{Rule}, C{False} otherwise.
        """
        return substring.lower() in unicode(self.name_plain).lower()

    def __enabled_at_date(self, date):
        """
        Checks if this Rule applies to a given date.

        @param date: the given date.

        @return: Returns C{True} if the rule applies to the given
        date, C{False} otherwise.
        """
        enabled_weekdays = [
            self.monday, self.tuesday, self.wednesday, self.thursday,
            self.friday, self.saturday, self.sunday]
        return (enabled_weekdays[date.weekday()] and
                not self.dateexception_set.filter(
                    from_date__lte=date, to_date__gte=date).exists())

    def generate_rules(self, begin_timestamp, days=1):
        """
        Generate list of rules that implement the user rule of this Rule
        object.

        @param begin_timestamp: The first date to generate agent and engine
         rules for. This is required to be a datetime object, because dates
         should be in the timezone of this rule.

        @param days: The number of days to generate rules for.

        @raise UserRuleIntegrityError: if for one of the dates, the
        rule can't be run even though it was supposed to.
        """
        result = []

        assert isinstance(begin_timestamp, datetime.datetime)
        tz = self.timezone
        begin_date = tz.normalize(begin_timestamp.astimezone(tz)).date()

        # the rule spans more than one date
        if self.from_time >= self.to_time:
            # Intention is to return rules that start to run, or are already
            # running at the given date, rather than the original
            # implementation, which returned rules that should start run on the
            # given date.
            days += 1
            begin_date -= datetime.timedelta(days=1)

        dates = [begin_date + datetime.timedelta(days=i) for i in range(days)]
        dates = filter(self.__enabled_at_date, dates)
        for date in dates:
            interval_begin = self.timezone.localize(
                datetime.datetime.combine(
                    date,
                    self.from_time))
            interval_end = self.timezone.localize(
                datetime.datetime.combine(
                    date,
                    self.to_time))
            if interval_end <= interval_begin:
                interval_end += RelativeTimeDelta(days=1)
            result.extend(self.content_object._day_rules(interval_begin,
                                                         interval_end))
        return result


class RuleCustomerBoundManager(CustomerBoundManager):
    _field = 'rule__customer'


class DateException(models.Model):
    """
    Specific date range that a rule should I{not} apply to.

    @ivar rule: The L{Rule} this exception is specified for.
    @ivar from_date: The first date the exception is in effect for.
    @ivar to_date: The last date the exception is in effect for.
    """
    rule = models.ForeignKey(
        UserRule, on_delete=models.CASCADE, editable=False)
    from_date = models.DateField(_('from date'))
    to_date = models.DateField(_('to date'))

    objects = RuleCustomerBoundManager()

    class Meta:
        verbose_name = _('date exception')
        verbose_name_plural = _('date exceptions')
        ordering = ['-to_date', '-from_date', 'id']

    def __unicode__(self):
        return u'%(rule_id)s; %(from)s - %(to)s' % {
            'rule_id': self.rule_id,
            'from': self.from_date,
            'to': self.to_date}


class Action(models.Model):
    """
    Base class for rule actions.

    @cvar INITIAL: Initial action.
    @cvar FINAL: Final action.
    @cvar EXECUTION_TIME_CHOICES: Initial/final choice specification for
    Django.

    @ivar rule: The L{Rule} this exception is specified for.
    @ivar execution_time: Choice between C{INITIAL} and C{FINAL} execution.
    """
    INITIAL = 0
    FINAL = 1
    EXECUTION_TIME_CHOICES = (
        (INITIAL, _('initial')),
        (FINAL, _('final')))
    rule = models.ForeignKey(UserRule, on_delete=models.CASCADE)
    execution_time = models.PositiveSmallIntegerField(
        _('execution time'), choices=EXECUTION_TIME_CHOICES)

    objects = RuleCustomerBoundManager()

    class Meta:
        abstract = True
        verbose_name = _('action')
        verbose_name_plural = _('actions')

    def execute(self):
        """
        Executes this action.

        @raise NotImplementedError: This exception is raised, if the
        C{execute()} method is not implemented in the concrete
        C{Action} subclass.
        """
        raise NotImplementedError("Subclass must reimplement this method")


class RelayAction(Action):
    """
    Rule action for setting the state of a relay.

    @cvar RELAY_ACTION_CHOICES: On/off choice specification for Django.

    @ivar meter: The meter to switch relay on.
    @ivar relay_action: Choice between C{TURN_ON} and C{TURN_OFF}.
    """
    RELAY_ACTION_CHOICES = (
        (TURN_ON, _('turn on')),
        (TURN_OFF, _('turn off')))
    meter = models.ForeignKey(Meter, on_delete=models.PROTECT)
    relay_action = models.PositiveSmallIntegerField(
        _('relay action'), choices=RELAY_ACTION_CHOICES)

    class Meta:
        verbose_name = _('relay action')
        verbose_name_plural = _('relay actions')
        ordering = ['id']

    def __unicode__(self):
        """
        @return: Return localized human readable representation of
        this object.
        """
        if self.relay_action == TURN_ON:
            return _(u"set relay on {meter} to on").format(
                meter=unicode(self.meter))
        else:
            assert(self.relay_action == TURN_OFF)
            return _(u"set relay on {meter} to off").format(
                meter=unicode(self.meter))

    def execute(self):
        """
        Executes this action.
        """
        agentserver.relay_state(
            self.meter.agent.mac,
            [(self.meter.connection_type, self.meter.manufactoring_id)],
            self.relay_action)


class EmailAction(Action):
    """
    Rule action for sending an email.

    @ivar recipient: Receiver e-mail address.
    @ivar message: Mail text to send.
    """
    recipient = models.EmailField(_('recipient'))
    message = models.TextField(_('message'))

    class Meta:
        verbose_name = _('email action')
        verbose_name_plural = _('email actions')
        ordering = ['message', 'id']

    def __unicode__(self):
        """
        @return: Return localized human readable representation of
        this object.
        """
        return _(u"send email '{message}' to '{recipient}'").format(
            message=self.message, recipient=self.recipient)

    def execute(self):
        """
        Executes this action.
        """
        try:
            mail.send_mail("Email notification from GridEngine",
                           self.message,
                           settings.SITE_MAIL_ADDRESS,
                           [self.recipient],
                           fail_silently=False)
        except SMTPException, e:
            warnings.warn(
                "EmailAction.execute() (%s) failed with message %s" %
                (self, e),
                SMTPException)


class PhoneAction(Action):
    """
    Rule action for sending an SMS.

    @ivar phone_number: Receiver phone number.
    @ivar message: SMS text to send.
    """

    # Concatenated message lenght is acually 153 chars,
    # but we taking special characters into consideration, which takes
    # two bytes instead of just one.
    CONCATENATED_MESSAGE_LENGHT = 140

    phone_number = models.CharField(_('phone number'), max_length=20)
    message = models.TextField(_('message'))

    class Meta:
        verbose_name = _('phone action')
        verbose_name_plural = _('phone actions')
        ordering = ['phone_number', 'message', 'id']

    def __unicode__(self):
        """
        @return: Return localized human readable representation of
        this object.
        """
        return _(u"send text '{message}' to '{phone_number}'").format(
            message=self.message, phone_number=self.phone_number)

    def execute(self):
        """
        Executes this action.
        """
        message = self.message.encode('iso8859-1')

        # Figure out have many parts we have to split up
        # the message. Rounding up to int.
        concat = int(
            math.ceil(len(message) / float(self.CONCATENATED_MESSAGE_LENGHT)))

        url = "http://api.clickatell.com/http/sendmsg?%s" % (
            urllib.urlencode([
                ("user", "gridmanager"),
                ("password", "1GridManager2Go"),
                ("api_id", "3191312"),
                ("to", self.phone_number),
                ("text", message),
                ("concat", concat)],))

        with contextlib.closing(urllib2.urlopen(url)) as ud:
            result = ud.read()
            if 'ID: ' not in result:
                warnings.warn(
                    'PhoneAction.execute() (%s) failed: url="%s", '
                    'response="%s"' % (self, url, result))


class MinimizeRule(UserRule):
    """
    Rule taking action when a specified index has its minimal value(s) within
    its I{active} interval.  This can lead to one or more periods of
    I{activity}.

    @ivar consecutive: Whether a single consecutive activity interval is
    required, or a sequence of non-consecutive intervals may be used.
    @ivar activity_duration: The total duration of activity required.
    @ivar index: The L{Index} to minimise with regards to.
    """
    consecutive = models.BooleanField(_('Consecutive'))
    activity_duration = DurationField(_('duration of activity'))
    index = models.ForeignKey(
        'indexes.Index', on_delete=models.PROTECT,
        limit_choices_to=~models.Q(
            role__in=[DataRoleField.STANDARD_HEATING_DEGREE_DAYS,
                      DataRoleField.CO2_QUOTIENT]))

    class Meta:
        verbose_name = _('minimize rule')
        verbose_name_plural = _('minimize rules')
        # inherit ordering from UserRule

    def _day_intervals(self, from_time, to_time):
        if (to_time - from_time) < self.activity_duration:
            raise UserRuleIntegrityError(
                "User rule is self-contradictory. "
                "The earliest usage end is after interval end")

        if self.consecutive:
            start_time = self.index.minimize_contiguous(
                from_timestamp=from_time,
                to_timestamp=to_time,
                duration=self.activity_duration)
            assert(start_time.tzinfo is not None)
            return [(start_time,
                     start_time + self.activity_duration)]
        else:
            return self.index.minimize_noncontiguous(
                from_timestamp=from_time,
                to_timestamp=to_time,
                duration=self.activity_duration)

    def _day_rules(self, interval_begin, interval_end):
        result = []
        # intervals is iterated multiple times, and therefore needs to be a
        # list.
        intervals = list(self._day_intervals(interval_begin, interval_end))
        assert intervals is not None
        for from_time, to_time in intervals:
            result.extend([
                AgentRule(from_time, initial_action)
                for initial_action
                in self.relayaction_set.filter(
                    execution_time=Action.INITIAL)])
            result.extend([
                AgentRule(to_time, final_action)
                for final_action
                in self.relayaction_set.filter(
                    execution_time=Action.FINAL)])
        result.append(EngineRule(intervals, [], self, False))
        return result


class TriggeredRule(UserRule):
    """
    Rule taking action when specific conditions are true within its activity
    interval.

    The rule I{activity} starts as soon as all associated L{Invariant}s are
    fulfilled within the rules I{active} interval, and lasts until one or more
    stops being fulfilled or the rule is no longer I{active}.
    """

    class Meta:
        verbose_name = _('triggered rule')
        verbose_name_plural = _('triggered rules')
        # inherit ordering from UserRule

    def _generate_periods(self, from_time, to_time, index_invariants):
        """
        Recursively generate list of periods in which a conjunction of
        propositions holds.  The periods are all generated within a
        given interval.

        @param from_time: The start of the given interval.

        @param to_time: The end of the given interval.

        @param propositions: The list of propositions that must hold
        inside the generated periods.  This list is on the same form
        as the C{"invariants"} member of the L{user_rule} JSON
        object.

        @return: Returns a list of nonoverlapping distinct periods in
        the form of tuples where the first element is a
        C{datetime.datetime} marking the start of the period, and the
        second element is a C{datetime.datetime} marking the end of
        the period.
        """
        assert(isinstance(from_time, datetime.datetime))
        assert(isinstance(to_time, datetime.datetime))
        assert(from_time <= to_time)

        result = []
        if index_invariants == []:
            result = [(from_time, to_time)]
        else:
            for period_from_time, period_to_time in \
                    index_invariants[0].index.generate_true_periods(
                        from_time, to_time, index_invariants[0].compare_value):
                assert(isinstance(period_from_time, datetime.datetime))
                assert(isinstance(period_to_time, datetime.datetime))
                result.extend(self._generate_periods(period_from_time,
                                                     period_to_time,
                                                     index_invariants[1:]))

        return result

    def _day_rules(self, from_time, to_time):
        """
        Generate agent rules for triggered usage, within a given
        interval.

        @param from_time: The start of the given interval.

        @param to_time: The end of the given interval.

        @return: Returns a list of AgentRules that realize the
        triggered usage in the given interval.
        """
        assert(isinstance(from_time, datetime.datetime))
        assert(isinstance(to_time, datetime.datetime))
        result = []
        inputinvariants = list(self.inputinvariant_set.all())
        if inputinvariants:
            result.append(
                EngineRule(
                    self._generate_periods(
                        from_time, to_time,
                        list(self.indexinvariant_set.all())),
                    inputinvariants,
                    self,
                    True))
        else:
            periods = self._generate_periods(
                from_time, to_time,
                list(self.indexinvariant_set.all()))
            for activity_start, activity_end in periods:
                assert(isinstance(from_time, datetime.datetime))
                assert(isinstance(to_time, datetime.datetime))
                result.extend([
                    AgentRule(activity_start, initial_action)
                    for initial_action
                    in self.relayaction_set.filter(
                        execution_time=Action.INITIAL)])
                result.extend([
                    AgentRule(activity_end, final_action)
                    for final_action
                    in self.relayaction_set.filter(
                        execution_time=Action.FINAL)])
            result.append(EngineRule(periods, [], self, False))
        return result


class Invariant(models.Model):
    """
    Base class for L{TriggeredRule} invariants.  Invariants compare
    index value or the input from monitored equipment to a constant.

    @note: LTE, EQ, GTE, NEQ are no longer supported.  They are defined here,
    to preserve their meening, but they are not meant to be used in future
    applications of the Invariant class.
    """
    LT = 0
    LTE = 1
    EQ = 2
    GTE = 3
    GT = 4
    NEQ = 5
    OPERATOR_CHOICES = (
        (LT, '<'),
        (GT, '>'))

    # NOTE: As this class is abstract, this will work as if the fields were
    # declared on the child classes --- including the behaviour of the
    # ForeignKey/reverse relations.
    rule = models.ForeignKey(TriggeredRule, on_delete=models.CASCADE,
                             editable=False)
    operator = models.IntegerField(
        _('operator'), choices=OPERATOR_CHOICES)

    unit = models.CharField(choices=units.UNIT_CHOICES, max_length=100)

    objects = RuleCustomerBoundManager()

    class Meta:
        abstract = True
        verbose_name = _('invariant')
        verbose_name_plural = _('invariants')
        ordering = ['id']

    def save(self, *args, **kwargs):
        assert self.operator in dict(self.OPERATOR_CHOICES).keys()
        assert self.unit in dict(units.UNIT_CHOICES).keys()
        super(Invariant, self).save(*args, **kwargs)

    OPERATOR_MAP = {
        LT: python_operator.lt,
        LTE: python_operator.le,
        EQ: python_operator.eq,
        GTE: python_operator.ge,
        GT: python_operator.gt,
        NEQ: python_operator.ne,
    }

    def compare_value(self, value):
        """
        Check this C{Invariant} against a value.

        Use this method wherever comparing C{Invariant}s against other
        values, so that the left and right hand sides of the operator
        stay consistent.

        @param value: The value to check against.

        @return: True if C{value OPERATOR self.value}, where OPERATOR
        is replaced with the actual operator represented with
        C{self.operator}.  False otherwise.

        @note: Most of these operators are no longer possible to choose when
        creating invariants, but they are kept here to avoid invalidating rules
        created prior to this limitation.  Those rules don't make much sense
        though, but still.  Some day a decission is probably made to delete the
        redundant operators.
        """
        op = Invariant.OPERATOR_MAP[self.operator]
        return op(value, self.value_as_physical_quantity())

    def value_as_physical_quantity(self):
        """
        Converts value to a L{PhysicalQuantity}.

        @precondition: C{self.unit not in ['celsius', 'fahrenheit']}
        """
        assert self.unit != 'celsius'
        assert self.unit != 'fahrenheit'
        return PhysicalQuantity(self.value, self.unit)


class IndexInvariant(Invariant):
    """
    L{TriggeredRule} invariant comparing an index value to a constant.
    """
    index = models.ForeignKey('indexes.Index', on_delete=models.PROTECT)
    value = models.DecimalField(_('value'), decimal_places=3, max_digits=8)

    class Meta:
        verbose_name = _('index invariant')
        verbose_name_plural = _('index invariants')


class InputInvariant(Invariant):
    """
    L{TriggeredRule} invariant comparing a measurement to a constant.
    """
    data_series = models.ForeignKey(
        'measurementpoints.DataSeries', on_delete=models.PROTECT)
    value = models.BigIntegerField(_('value'))

    class Meta:
        verbose_name = _('input invariant')
        verbose_name_plural = _('input invariants')

    def __repr__(self):
        return 'InputInvariant(data_series=%r, value=%r, rule=%r, unit=%r, ' \
            'operator=%r)' % (self.data_series, self.value, self.rule,
                              self.unit, self.operator)

    def clean(self):
        if self.data_series.unit and self.unit:
            if self.unit == 'celsius':
                real_unit = 'kelvin'
            elif self.unit == 'fahrenheit':
                real_unit = 'rankine'
            else:
                real_unit = self.unit
            if not PhysicalQuantity.compatible_units(
                    self.data_series.unit, real_unit):
                raise ValidationError(
                    _(u'Unit incompatible with selected input.'))

    def value_as_physical_quantity(self):
        """
        C{InputInvariant} override of
        L{Invariant.value_as_physical_quantity()}.  This implementation will
        also handle C{self.unit in ['celsius', 'fahrenheit']}.
        """
        if self.unit == 'celsius':
            result = PhysicalQuantity(self.value, 'kelvin')
            if self.data_series.role == DataRoleField.ABSOLUTE_TEMPERATURE:
                result += PhysicalQuantity('273.15', 'kelvin')
        elif self.unit == 'fahrenheit':
            result = PhysicalQuantity(self.value, 'rankine')
            if self.data_series.role == DataRoleField.ABSOLUTE_TEMPERATURE:
                result += PhysicalQuantity('459.67', 'rankine')
        else:
            result = super(InputInvariant, self).value_as_physical_quantity()
        return result


class EngineRule(object):
    """
    A C{EngineRule} is the execution of a rule by acting on
    relevant events when they are detected.  C{EngineRule}s work by
    processing their rule once every time the member method
    L{process_rule()} is called.  The idea is that an owning process
    has a number of C{EngineRule} objects, one for every rule that
    process is responsible for, and the L{process_rule()} method of
    these are then called in turn at a frequent interval.

    Events are transitions in and out of certain states, defined by
    the underlying rule.  Most of these states will be stored as
    measurment values in the database, and state transitions are
    detected some time (hopefully shortly) after they actually occur.
    This means that it is necessary to keep track of state transition
    that has already been detected and handled, and this is what this
    object serves to do.

    @ivar process_again: If C{True} it makes sense to call process()
    again.  If C{False}, this C{EngineRule} is done, and it can be
    deleted.
    """
    def __init__(self, execution_periods, input_invariants, user_rule,
                 engine_controls_relays):
        self.execution_periods = execution_periods
        self.input_invariants = list(input_invariants)
        self.user_rule = user_rule
        self.current_period = None
        self.process_again = True
        self.engine_controls_relays = engine_controls_relays

    def __cmp__(self, other):
        """
        Two EngineRules are considered equal if they are instantiated from the
        same user_rule with the same input invariants and run on the same date.
        EngineRules support updates on the run. So new rules and updates to
        rules do take effect emmidiately when rules are reloaded.  When a rule
        is updated, the final actions are not executed, but the initial actions
        of the updated rule are executed.
        """
        return cmp(self.__class__, other.__class__) or \
            cmp((self.execution_periods,
                 [(ii.data_series, ii.value, ii.operator, ii.unit) for
                  ii in self.input_invariants],
                 self.user_rule),
                (other.execution_periods,
                 [(ii.data_series, ii.value, ii.operator, ii.unit) for
                  ii in other.input_invariants],
                 other.user_rule))

    def __hash__(self):
        return hash((tuple(self.execution_periods),
                     tuple(self.input_invariants),
                     self.user_rule))

    def __repr__(self):
        return 'EngineRule(execution_periods=%r, input_invariants=%r, '\
            'user_rule=%r)' % (self.execution_periods, self.input_invariants,
                               self.user_rule)

    def __get_actions(self, execution_time):
        """
        Construct a list of actions with the given C{execution_time}.
        """
        actions = list(self.user_rule.emailaction_set.filter(
            execution_time=execution_time).distinct())
        actions.extend(list(self.user_rule.phoneaction_set.filter(
            execution_time=execution_time).distinct()))
        if self.engine_controls_relays:
            actions.extend(list(self.user_rule.relayaction_set.filter(
                execution_time=execution_time).distinct()))
        return actions

    def __check_input_invariants(self, from_time, now):
        """
        Check that our input_invariants are met by all inputs.

        @return: C{False} if any input invariant is violated.
        C{True} otherwise.
        """
        for input_invariant in self.input_invariants:
            data_series = input_invariant.data_series.subclass_instance
            from_time
            assert from_time <= now
            if data_series.is_rate():
                measurement = data_series.latest_sample(
                    from_timestamp=from_time,
                    to_timestamp=now)
            else:
                assert data_series.is_accumulation()
                measurement = data_series.calculate_development(
                    from_timestamp=from_time,
                    to_timestamp=now)
            if not measurement or not input_invariant.compare_value(
                    measurement.physical_quantity):
                return False
        return True

    def process(self, now):
        """
        Process input invariants against recent measurement data.

        Relay switch actions are only to be taken if the state of
        input invariants has changed since last time C{process()} was
        called.

        @return Returns a list of L{Action}s to be taken right now.
        """

        result = []
        if self.current_period:
            from_time, to_time = self.current_period
            if now >= to_time or not self.__check_input_invariants(
                    from_time, now):
                self.current_period = None
                result.extend(self.__get_actions(Action.FINAL))

        self.process_again = any([now < to_time_ for from_time_, to_time_
                                  in self.execution_periods])

        if not self.current_period and self.process_again:
            for from_time, to_time in self.execution_periods:
                if from_time <= now < to_time and \
                        self.__check_input_invariants(from_time, now):
                    self.current_period = (from_time, to_time)
                    result.extend(self.__get_actions(Action.INITIAL))
                    break

        return result


class AgentRule(object):
    """
    Agent rules are interpreted by individual agents.

    Unlike user rules (L{Rule}), agent rules are limited to some quite
    minimalistic semantics, namely those on the form "at time t,
    relay NAME is turned on/off"

    @ivar activation_time: A datetime.datetime at which to activate
        this rule.

    @ivar relay_action: A L{RelayAction} to be executed when time
    passes C{activation_time}.

    @ivar process_again: If C{True} it makes sense to call process()
    again.  If C{False}, this C{EngineRule} is done, and it can be
    deleted.
    """

    def __init__(self, activation_time, relay_action):
        """
        Construct an AgentRule.

        @param activation_time: A datetime.datetime at which to
        activate this rule.

        @param relay_action: A L{RelayAction} to be executed when time
        passes C{activation_time}.
        """
        self.activation_time = activation_time
        self.relay_action = relay_action
        self.process_again = True

    def __cmp__(self, other):
        return cmp(self.__class__, other.__class__) or \
            cmp((self.activation_time,
                 self.relay_action.relay_action,
                 self.relay_action.meter_id),
                (other.activation_time,
                 other.relay_action.relay_action,
                 other.relay_action.meter_id))

    def __hash__(self):
        return hash((self.activation_time,
                     self.relay_action.relay_action,
                     self.relay_action.meter_id))

    def __unicode__(self):
        details = {"activation_time":
                   self.activation_time.tzinfo.normalize(self.activation_time),
                   "relay": self.relay_action.meter}
        if self.relay_action.relay_action == TURN_ON:
            return _("at %(activation_time)s relay "
                     "%(relay)s is turned on") % details
        else:
            assert(self.relay_action.relay_action == TURN_OFF)
            return _("at %(activation_time)s relay "
                     "%(relay)s is turned off") % details

    def __repr__(self):
        return b"AgentRule(%r, %r)" % (self.activation_time,
                                       self.relay_action)

    def process(self, now):
        """
        Process the scheduled C{RelayAction} against current time.  If
        C{self.relay_action} has not been executed yet, but C{now >=
        self.activation_time} it is returned, and assumed to be
        executed.

        @param now: The current time.

        @return Returns a list of L{Action}s to be taken right now.
        """
        if self.process_again and now >= self.activation_time:
            self.process_again = False
            return [self.relay_action]
        return []
