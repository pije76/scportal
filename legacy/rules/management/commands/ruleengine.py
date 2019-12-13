# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import traceback

from django.core.management.base import BaseCommand
from django.utils.daemonize import become_daemon
from django.core import mail

from legacy.rules import engine


class Command(BaseCommand):
    args = ""
    help = "Run the Grid Platform rule engine"

    def handle(self, *args, **kwargs):
        """
        """
        become_daemon(out_log='ruleengine.log', err_log='ruleengine.err')
        for i in range(10):
            # limited "retries", to avoid mail-flood in case of recurring
            # exception
            try:
                try:
                    engine.run()
                except Exception as e:
                    mail.mail_admins(
                        'Rule engine error: %s' % (e.__class__,),
                        '%s\n%s' % (e, traceback.format_exc()),
                        fail_silently=False)
            except:
                mail.mail_admins(
                    'Rule engine error (not Exception)',
                    traceback.format_exc(),
                    fail_silently=True)
        mail.mail_admins('Rule engine now stopping', '', fail_silently=True)
