# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
Test module for the L{legacy.display_measurementpoints} Django
app.
"""

from django.test import TestCase
from django.utils import translation

from .templatetags.display_measurementpoints import physicalquantity


class TemplateFilterTest(TestCase):
    def test_physicalquantity(self):
        with translation.override('da-dk'):
            self.assertEqual(
                u'0,3333333333 Å', physicalquantity((1 / 3., u'Å'), 10))

        with translation.override('en-uk'):
            self.assertEqual(
                u'0.3333333333 Å', physicalquantity((1 / 3., u'Å'), 10))
