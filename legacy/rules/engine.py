# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Strategy:

Every hour, reload set of active rules.
(... may give scalability problems later --- but not anytime soon.)

Continuously check currently active rules.
(... rules that do not depend on current inputs and thus will only do something
at a predetermined time may be a bit silly to recheck --- but it's also cheap
to do so; avoiding it takes a bigger change than necessary now...)


Get active rules for timestamp:
* Iterate over all UserRule objects
* Get timestamp in userrule timezone
* Include if from_time < to_time and from_time <= timestamp <= to_time and rule
* active for timestamp.weekday  (rule does not span day change; simple check)
* Also include if to_time <= from_time and timestamp >= from_time and rule
* active for timestamp.weekday  (rule spans day; after start today; before stop
* tomorrow)
* Also include if to_time <= from_time and timestamp <= to_time and rule active
* for timestamp.weekday - 1  (rule spans day; after start yesterday; before
* stop today)

... for now, generate_rules is modified to be conservative; include rules
starting at current date and rules starting at previous date when they span
over midnigt...
... and, we take timezones into account...
"""

import datetime
import time

import pytz

from legacy.rules.models import UserRule, EngineRule
from legacy.devices.models import Meter


def get_tainted_meter_ids():
    """
    Tainted L{Meters}, are L{Meters} whose relays are controlled by
    anything different than static time schedules, and therefore needs to
    be handled by this Engine.

    @return: Returns a list of ids of Meters that are considered tainted.
    """
    # Meters with RelayActions of TriggeredRules having Invariants are
    # considered tainted.
    return Meter.objects.filter(
        relayaction__rule__triggeredrule__inputinvariant__isnull=False).\
        distinct().values_list('id', flat=True)


def get_engine_rules(date):
    """
    Rules to be processed by this C{Engine} at a given date.

    @param date: The given date.

    @return: A list of L{EngineRule}s and L{AgentRules} to be processed by
    this C{Engine} at the given C{date}.
    """
    assert isinstance(date, datetime.datetime)
    assert date.tzinfo is not None
    tainted_meters = get_tainted_meter_ids()

    engine_rules = []

    rules = UserRule.objects.filter(enabled=True).select_related('relayaction')

    # Both AgentRules and EngineRules that have RelayActions that work on
    # the relays of tainted Meters must be processed by the Engine.
    for user_rule in rules.filter(
            relayaction__meter__in=tainted_meters).distinct():
        engine_rules.extend(user_rule.generate_rules(date))

    # For all other rules, only the actual EngineRules should be handled by
    # the engine.
    for user_rule in rules.exclude(
            relayaction__meter__in=tainted_meters).distinct():
        for rule in user_rule.generate_rules(date):
            if isinstance(rule, EngineRule):
                engine_rules.append(rule)

    return engine_rules


def refresh_rules(rules, hour):
    """
    HACK: figure out what rules have become active/inactive, in order to
    construct a set of currently active rules --- but keep the objects from the
    old set where possible, to let the value of the process_again property
    survive...
    """
    hour_rules = set(get_engine_rules(hour))
    new_rules = hour_rules - rules
    removed_rules = rules - hour_rules
    return (rules - removed_rules) | new_rules


def run():
    last_hour = None
    rules = set()

    while True:
        now = datetime.datetime.now(pytz.utc).replace(microsecond=0)
        hour = now.replace(minute=0, second=0, microsecond=0)

        # NOTE: new rules are taken in on next iteration --- we need to handle
        # "obsoleted" rules before updating the rule set to ensure that their
        # final action is executed.
        for rule in rules:
            if rule.process_again:
                map(lambda action: action.execute(), rule.process(now))

        if hour != last_hour:
            rules = refresh_rules(rules, hour)
            last_hour = hour

        time.sleep(10)
