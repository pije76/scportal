# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from legacy.measurementpoints.models import Collection


class Command(BaseCommand):
    args = ''
    help = 'Rebuilds the measurement points group tree.'

    def handle(self, *args, **options):
        Collection.tree.rebuild()
