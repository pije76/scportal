# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module defines Django template tags for showing versions.
"""

from django import template
from django.utils.translation import ugettext_lazy as _

import gridplatform
from gridplatform.reports.templatetags.reports import texescape


register = template.Library()


@register.simple_tag
def gridplatform_version():
    """
    Display version information.

    Version will be marked as unknown when working on code not released through
    C{make dist} or C{make release}.

    To change the version number, update C{Makefile} accordingly.
    """
    return _(u'Version: {}').format(gridplatform.__version__)


@register.simple_tag
def gridplatform_version_tex():
    return texescape(gridplatform_version())
