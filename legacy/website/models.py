# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db.models.signals import post_save

from gridplatform.users.models import User
from legacy.legacy_utils.models import UserProfile


def create_user_profile(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
