# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import os
from shutil import rmtree
from tempfile import mkdtemp
from decimal import Decimal

from django.template import Context
from django.template import Template
from django.template.defaultfilters import floatformat as django_floatformat
from django.test import TestCase

from .templatetags.reports import pgfcolor
from .templatetags.reports import texescape
from .templatetags.reports import floatformat
from .pdf import _generate_gnuplot
from .csv import generate_csv


class TranslationTest(TestCase):
    def test_trans(self):
        t = Template('{% load reports %}{% trans "Some$" %}')
        val = t.render(Context({}))
        self.assertEqual(val, texescape('Some$'))

    def test_trans_as(self):
        t = Template(
            '{% load reports %}{% trans "Some$" as testvar %}{{ testvar }}')
        val = t.render(Context({}))
        self.assertEqual(val, texescape('Some$'))

    def test_blocktrans(self):
        t = Template(
            '{% load reports %}{% blocktrans with foo="bar$" %}'
            'Blah% {{ foo }}{% endblocktrans %}')
        val = t.render(Context({}))
        self.assertEqual(val, texescape('Blah% bar$'))


class PgfColorTest(TestCase):

    def test_pgfcolor(self):
        """
        Test that some HTML style color can be converted to the desired pgfplot
        compliant RGB format.
        """
        self.assertEqual(
            '{rgb:red,138;green,82;blue,232}', pgfcolor('#8A52E8'))

    def test_pgfcolor_failure(self):
        """
        Template filters must output their argument or the empty string in case
        of errors.  We test that the argument is returned, since that makes
        debugging that much easier, in case the argument is not valid.
        """
        self.assertEqual('this is not a HTML style color',
                         pgfcolor('this is not a HTML style color'))


class GnuPlotTest(TestCase):
    def test_generate_gnuplot(self):
        tmp_dir = mkdtemp(prefix='django-unit-test')
        try:
            _generate_gnuplot(
                """
                set boxwidth 1.0
                set style fill solid
                set output "test.tex"
                set terminal epslatex color
                plot "-" using 1:3:xtic(2) with boxes
                0 label 100
                1 label2 450
                2 "bar label" 75
                e
                set output
                """,
                tmp_dir)

            self.assertTrue(os.path.exists(os.path.join(tmp_dir, 'test.tex')))
            self.assertTrue(os.path.exists(os.path.join(tmp_dir, 'test.eps')))
        finally:
            rmtree(tmp_dir)


class CSVTest(TestCase):
    def test_generate_cvs(self):
        data = [["test", "test", "°C"], ["something", "something", "°C"]]
        unit = generate_csv(data)
        self.assertIn("°C".encode('utf-8'), unit)


class FloatFormatTest(TestCase):
    """
    Apparently the Django floatformat is implemented in terms of Decimal
    methods that take significant digits into account.
    """

    def test_insignificant_digits_workaround(self):
        """
        Test that the work-around fixes the issue.
        """
        self.assertEqual(
            '740.000',
            floatformat(str(Decimal(666000) / Decimal('0.9')), 0))

    def test_insignificant_digits_bug(self):
        """
        Test that the django floatformat still has the bug (once this test
        fails, the L{templatetags.reports.floatformat} should be deleted again.
        """
        self.assertNotEqual(
            '740.000',
            django_floatformat(str(Decimal(666000) / Decimal('0.9')), 0))
