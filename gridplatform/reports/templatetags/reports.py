# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import os.path
from fractions import Fraction

from django import template
from django.utils.safestring import mark_safe
from django.conf import settings
from django.templatetags import i18n
from django.template.defaultfilters import floatformat as django_floatformat

register = template.Library()


@register.simple_tag
def media_file(path):
    """
    Get an absolute file path from a relative "media" file path.
    """
    return mark_safe(os.path.abspath(os.path.join(settings.MEDIA_ROOT, path)))


@register.simple_tag
def static_file(path):
    """
    Get an absolute file path from a relative "static" file path.
    """
    # Find files in app directories, STATICFILES_DIRS and wherever else the
    # development static files server and collectstatic would find them.
    # (Unlike "media", each app may have its own "static" files, and we want to
    # be able to use them during development, without explicitly running
    # "manage.py collectstatic".)
    from django.contrib.staticfiles import finders
    return mark_safe(finders.find(path))


rewrite_rules = (
    ('\\', r'\\'),
    ('{', r'\{'),
    ('}', r'\}'),
    ('\\\\', r'\textbackslash{}'),
    ('#', r'\#'),
    ('$', r'\$'),
    ('%', r'\%'),
    ('&', r'\&'),
    ('~', r'\~'),
    ('_', r'\_'),
    ('^', r'{$\hat{~}$}'),
    ('\r', ''),
    ('\n', r'\newline{}'),
)


@register.filter
def texescape(value):
    """
    Escape/replace characters with special meanings in (La)TeX.
    """
    result = unicode(value)
    for (string, replacement) in rewrite_rules:
        result = result.replace(string, replacement)
    return mark_safe(result)


class TexTranslateNode(i18n.TranslateNode):
    """
    Specialisation of translation node; escaping output for TeX.
    """
    def render(self, context):
        value = super(TexTranslateNode, self).render(context)
        if self.asvar:
            context[self.asvar] = texescape(context[self.asvar])
        return texescape(value)


class TexBlockTranslateNode(i18n.BlockTranslateNode):
    """
    Specialisation of block translation node; escaping output for TeX.
    """
    def render(self, context):
        return texescape(super(TexBlockTranslateNode, self).render(context))


@register.tag
def trans(parser, token):
    """
    Specialisation of translation tag; escaping output for TeX.

    NOTE: Same tag name as the standard Django tag, to ensure that they are
    included in translation as normal.
    """
    node = i18n.do_translate(parser, token)
    node.__class__ = TexTranslateNode
    return node


@register.tag
def blocktrans(parser, token):
    """
    Specialisation of block translation tag; escaping output for TeX.

    NOTE: Same tag name as the standard Django tag, to ensure that they are
    included in translation as normal.

    @param notexescape: If this argument is given texescaping will be
    disabled::

        {% blocktrans notexescape with page as "\thePage{}" %}
        Page {{ page }}
        {% endblocktrans %}

    @bug: If the string C{'notexescape'} is part of any of the other arguments,
    it will be removed, and interpreted as the notexescape option.
    """
    if 'notexescape' in token.contents:
        token.contents = token.contents.replace('notexescape', '')
        node = i18n.do_block_translate(parser, token)
    else:
        node = i18n.do_block_translate(parser, token)
        node.__class__ = TexBlockTranslateNode
    return node


@register.filter
def pgfcolor(value):
    """
    Translate a HTML style hexadecimal color to something that works with LaTeX
    pgf. For instance::

        #8A52E8

    should be converted to::

        {rgb:red,138;green,82;blue,232}
    """
    try:
        red = int(value[1:3], base=16)
        green = int(value[3:5], base=16)
        blue = int(value[5:7], base=16)
        return mark_safe('{rgb:red,%d;green,%d;blue,%d}' % (red, green, blue))
    except:
        # from the docs: Filter functions should always return something. They
        # shouldn't raise exceptions. They should fail silently. In case of
        # error, they should return either the original input or an empty
        # string - whichever makes more sense.
        #
        # https://docs.djangoproject.com/en/dev/howto/custom-template-tags/
        return value


@register.filter
def seqsplit(value, arg=10):
    """
    Wrap "long" words in \seqsplit{}, in order to allow linebreaks at any place
    inside them.
    """
    parts = value.split(' ')

    def do_split(s):
        if len(s) > arg:
            return '\seqsplit{%s}' % s
        else:
            return s
    result = ' '.join(map(do_split, parts))
    return mark_safe(result)


@register.filter(is_safe=True)
def floatformat(text, arg=-1):
    """
    Work-around for bug in Python Decimal.  See L{FloatFormatTest} for details.
    """
    try:
        return django_floatformat(float(Fraction(str(text))), arg)
    except:
        return django_floatformat(text, arg)
