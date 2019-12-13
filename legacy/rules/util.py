# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import itertools
import datetime

from pytz import utc

from legacy.ipc import agentserver

from .models import TURN_ON


# normal week + 1 hour; i.e. longer than actual week except on DST switch
max_week_seconds = int(datetime.timedelta(days=7, hours=1).total_seconds())


def week_start(date):
    return datetime.datetime.combine(
        date - datetime.timedelta(date.weekday()),
        datetime.time())


def to_week_second(timestamp):
    timestamp = timestamp.astimezone(utc).replace(tzinfo=None)
    return int((timestamp - week_start(timestamp.date())).total_seconds())


def agent_rules_to_duration_states(rules):
    """
    Translate a list of simple (week_second, relay_on)-rules to appropriate
    (from_week_second, to_week_second, relay_on)-rules.
    """
    if rules == []:
        return []

    # translate AgentRule object to reltime/relay_on pair
    rules = [(to_week_second(rule.activation_time),
              rule.relay_action.relay_action == TURN_ON)
             for rule in rules]
    rules = sorted(rules, key=lambda (time, relay_on): time)
    period_rules = [(start_time, end_time, relay_on)
                    for (start_time, relay_on), (end_time, _ignored)
                    in zip(rules, rules[1:])]
    start_time, relay_on = rules[-1]
    period_rules.append((start_time, max_week_seconds, relay_on))
    end_time, _ignored = rules[0]
    period_rules.insert(0, (0, end_time, relay_on))
    return filter(
        lambda (time_begin, time_end, relay_on): time_begin != time_end,
        period_rules)


def send_agent_rules(agent_rules):
    """
    Translate L{AgentRule} objects to a format closer to the semantics used by
    current agents.  (As of GridAgent 2.1.1?)
    """
    # group rules by agent
    # for each agent:
    #   group rules by meter/relay
    #   translate rule format --- timestamp/action -> reltime-duration/action
    #   send to agent server

    def get_agent(rule):
        return rule.relay_action.meter.agent

    def get_agent_id(rule):
        return get_agent(rule).id

    def get_meter(rule):
        return rule.relay_action.meter

    def get_meter_id(rule):
        return get_meter(rule).id

    agent_rules = itertools.groupby(sorted(agent_rules, key=get_agent_id),
                                    get_agent)

    for agent, rules in agent_rules:
        grouped = itertools.groupby(sorted(rules, key=get_meter_id), get_meter)

        relay_rules = {
            relay: agent_rules_to_duration_states(rules)
            for relay, rules in grouped}
        rulesets = [([(meter.connection_type, meter.manufactoring_id)], rules)
                    for meter, rules in relay_rules.iteritems()]
        agentserver.agent_rules(agent.mac, rulesets)
