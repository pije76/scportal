# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import pytz

from django.core.management.base import BaseCommand

from legacy.rules import engine
from legacy.rules.util import send_agent_rules
from legacy.rules.models import UserRule, AgentRule
from gridplatform.utils.relativetimedelta import RelativeTimeDelta


class Command(BaseCommand):
    args = ""
    help = "Send Agent rules to AgentServer"

    def handle(self, *args, **kwargs):
        now = datetime.datetime.now(pytz.utc)
        hour = now.replace(minute=0, second=0, microsecond=0)

        tainted = engine.get_tainted_meter_ids()

        agent_rules = []

        for user_rule in UserRule.objects.filter(enabled=True).exclude(
                relayaction__meter__in=tainted).distinct().select_related(
                'relayaction'):
            try:
                agent_rules.extend([
                    rule for rule
                    in user_rule.generate_rules(
                        hour - RelativeTimeDelta(days=1),
                        days=7)
                    if isinstance(rule, AgentRule)
                ])
            except Exception as e:
                print e
        send_agent_rules(agent_rules)
