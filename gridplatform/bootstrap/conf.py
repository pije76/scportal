# -*- coding: utf-8 -*-
"""
.. py:data:: settings.BOOTSTRAP_THEME

    Defaults to 'base'.  Templates used by Bootstrap tags in this app are
    loaded from the template path 'bootstrap/<theme>/'.  See also
    :meth:`gridplatform.bootstrap.templatetags.bootstrap_tags.BootstrapNode.get_templates`.

.. py:data:: settings.BOOTSTRAP_FORM_LAYOUT

    Layout applied by default to forms using
    :func:`gridplatform.bootstrap.templatetags.bootstrap_tags.do_form` (``{%
    form ... %}``) template tag.  Must be one of "horizontal", "inline" and
    "basic".

Bootstrap uses a grid-layout so that cells in each row take up a total of 12
columns.  The following two settings are used to balance these 12 columns
between the label and the input field:

.. py:data:: settings.BOOSTRAP_LABEL_COLUMNS

    Defaults to 2.

.. py:data:: settings.BOOSTRAP_INPUT_COLUMNS

    Defaults to 10.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings

from appconf import AppConf


__all__ = ['settings', 'BootstrapConf']


class BootstrapConf(AppConf):
    THEME = 'base'
    # Default layout: "horizontal", "inline", "basic"
    FORM_LAYOUT = 'horizontal'
    # Default columns for label [1..12]:
    FORM_LABEL_COLUMNS = 2
    # Default columns for field [1..12]:
    FORM_INPUT_COLUMNS = 10
