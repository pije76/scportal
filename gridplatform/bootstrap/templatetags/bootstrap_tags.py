# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import collections
import os.path

from django import template
from django.forms import ModelMultipleChoiceField
from django.forms.fields import FileField
from django.forms.widgets import CheckboxInput
from django.forms.widgets import TextInput
from django.template.base import Node
from django.template.base import NodeList
from django.template.base import TemplateSyntaxError
from django.template.base import parse_bits
from django.template.defaulttags import CsrfTokenNode
from django.template.loader import render_to_string
from django.utils.translation import ugettext
from django.utils.translation import ugettext_lazy

from ..conf import settings


register = template.Library()


UNSET_OPTION = object()


def parse_token_arguments(parser, token, mandatory, optional):
    """
    Parse arguments/keyword arguments to template tag.  ``mandatory`` and
    ``optional`` specify names of mandatory and optional arguments.  Output is
    a dictionary whose values must resolved at render-time.
    """
    # The (internal) Django parse_bits() function is designed for use with the
    # Django function-to-tag-wrappers; the parameters params, varargs, varkw,
    # defaults are on the form returned by inspect.getargspec(), and the output
    # are args, kwargs to be resolved and used to call the fuction on
    # render-time.  Getting separate args and kwargs values as a result is
    # somewhat inconvenient unless we actually have a function that will
    # combine the argument appropriately when called with *args, **kwargs ---
    # so here, we combine them into the "kwargs" dictionary instead.
    bits = token.split_contents()
    tag_name = bits[0]
    params = mandatory + optional
    # parse_bits uses defaults only to determine the number of optional
    # arguments (to raise TemplateSyntaxError on missing positional arguments);
    # the actual values are not used.
    defaults = optional
    # takes_context=True would check that the first argument was named
    # "context" and skip it; for it to be handled in other code at render time.
    args, kwargs = parse_bits(
        parser, bits[1:], params=params,
        varargs=None, varkw=None, defaults=defaults,
        takes_context=False, name=tag_name)
    # We trust parse_bits to raise TemplateSyntaxError on conflicts between
    # args and kwargs; so just add positional arguments as appropriate to the
    # kwargs dictionary.
    for key, value in zip(params, args):
        kwargs[key] = value
    return tag_name, kwargs


class BootstrapNode(Node):
    """
    A base node for other bootstrap nodes defined in this module.
    """
    template_basename = None
    default_options = {}

    def __init__(self, tag_name, options):
        self.tag_name = tag_name
        self.options = options

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    def get_templates(self):
        """
        :return: List of templates to use, based on ``self.template_basename`` and
            :data:`settings.BOOTSTRAP_THEME`.  Defaults to 'base' theme if
            ``self.template_basename`` could not be resolved using the
            :data:`settings.BOOTSTRAP_THEME` theme.
        """
        return [
            'bootstrap/{}/{}'.format(
                settings.BOOTSTRAP_THEME, self.template_basename),
            'bootstrap/base/{}'.format(self.template_basename),
        ]

    def get_default_options(self, context):
        # NOTE: This returns a new dictionary on each call; so users are free
        # to modify it...
        options = {
            'request': context.get('request', None),
            'view': context.get('view', None),
            'object': context.get('object', None),
        }
        options.update(self.default_options)
        return options

    def resolve_options(self, context):
        # Start with copy of default/outer tag options.
        options = self.get_default_options(context)
        for key, value in self.options.items():
            resolved = value.resolve(context, ignore_failures=True)
            if resolved is not None:
                options[key] = resolved
        return options

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        return render_to_string(templates, options)


ICON_NAMES_FILE = 'font-awesome-icon-names.txt'
with open(os.path.join(os.path.dirname(__file__), ICON_NAMES_FILE), 'r') as f:
    ICON_NAMES = {l.strip() for l in f}
ICON_SIZES = ('', 'lg', '2x', '3x', '4x', '5x', 'fw')


class IconNode(BootstrapNode):
    template_basename = 'icon.html'
    default_options = {'size': '', 'spin': False}

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        name = options['name']
        size = options['size']
        if name not in ICON_NAMES:
            raise TemplateSyntaxError(
                'Not a valid icon name: {}; valid are {}'.format(
                    name, ICON_NAMES))
        if size not in ICON_SIZES:
            raise TemplateSyntaxError(
                'Not a valid icon size: {}; valid are {}'.format(
                    size, ICON_SIZES))
        return render_to_string(templates, options)


@register.tag(name='icon')
def do_icon(parser, token):
    """
    Insert a Font Awesome icon; specifying name and optional size.  Reduces the
    boilerplate to insert an icon and includes sanity checks to catch
    misspelled icon names.

    Usage::

        {% icon name [size="lg"|"2x"|"3x"|"4x"|"5x"|"fw"] [spin=False] %}

    """
    tag_name, options = parse_token_arguments(
        parser, token, ['name'], ['size', 'spin'])
    return IconNode(tag_name, options)


@register.filter()
def checkbox_icon_name(value):
    """
    Filter for extracting icon name given a boolean value for check box icons.

    Usage::

        {% icon value|checkbox_icon_name [size="lg"|"2x"|"3x"|"4x"|"5x"|"fw"] [spin=False] %}  # noqa
    """
    if value:
        return 'check-square-o'
    else:
        return 'square-o'


class PanelNode(BootstrapNode):
    template_basename = 'panel.html'

    def __init__(self, tag_name, options, buttons, body):
        super(PanelNode, self).__init__(tag_name, options)
        self.buttons = buttons
        self.body = body

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        options['buttons'] = self.buttons.render(context)
        options['body'] = self.body.render(context)
        return render_to_string(templates, options)


@register.tag(name='panel')
def do_panel(parser, token):
    """
    Usage::

        {% panel title %}
        [ buttons ... {% endpanelbuttons %}]
        [ body contents... ]
        {% endpanel %}
    """
    tag_name, options = parse_token_arguments(
        parser, token, ['title'], ['search'])
    buttons_or_body = parser.parse(('endpanelbuttons', 'endpanel'))
    token = parser.next_token()
    if token.contents == 'endpanelbuttons':
        buttons = buttons_or_body
        body = parser.parse(('endpanel',))
        token = parser.next_token()
    else:
        buttons = NodeList()
        body = buttons_or_body
    assert token.contents == 'endpanel'
    return PanelNode(tag_name, options, buttons, body)


LAYOUT_OPTION_NAMES = [
    'layout', 'label_columns', 'input_columns',
    'label_class', 'input_class', 'checkbox_class',
]
FORM_OPTION_NAMES = [
    'form_action', 'form_method',
]
LAYOUT_NAMES = ["horizontal", "inline", "basic"]

FORM_BUTTON_OPTION_NAMES = [
    'submit_label',
    'delete_label',
    'cancel_label',
    'cancel_target',
    'delete_target',
]


class FormNodeBase(BootstrapNode):
    def get_default_options(self, context):
        if '_bootstrap_form_options' not in context:
            raise TemplateSyntaxError(
                '{{% {} %}} only valid inside {{% bootstrap_form %}}'.format(
                    self.tag_name))
        options = super(FormNodeBase, self).get_default_options(context)
        options.update(context['_bootstrap_form_options'])
        return options


class FieldInputNode(FormNodeBase):
    template_basename = 'field_input.html'

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        field = options['field']
        input_css_classes = options['input_class'].split()
        # decorate with field class name
        input_css_classes.append(
            field.field.__class__.__name__.lower())
        # decorate with widget class name
        input_css_classes.append(
            field.field.widget.__class__.__name__.lower())
        if not isinstance(field.field.widget, CheckboxInput):
            # If not a checkbox, set form-control class.
            input_css_classes.append('form-control')
        attrs = {
            'class': ' '.join(input_css_classes),
        }
        if 'placeholder' in options:
            if isinstance(field.field.widget, TextInput):
                # Text field or HTML5-specialisation thereof
                attrs['placeholder'] = options['placeholder']
            else:
                raise TemplateSyntaxError(
                    '\"placeholder\" parameter only valid'
                    ' for text field variants')
        if isinstance(field.field, ModelMultipleChoiceField):
            # Avoid adding translation string to this app --- we need to match
            # whatever Django inserted.
            unwanted_base = \
                'Hold down "Control", or "Command" on a Mac, ' + \
                'to select more than one.'
            unwanted = ugettext(unwanted_base)
            field.help_text = field.help_text.replace(unwanted, '').strip()
        options['widget'] = field.as_widget(attrs=attrs)
        # NOTE: registering that field has been rendered
        options['touched_fields'].append(field)
        return render_to_string(templates, options)


@register.tag(name='field_input')
def do_field_input(parser, token):
    """
    Usage::

        {% field_input field [layout options...] [placeholder=...] %}
    """
    tag_name, options = parse_token_arguments(
        parser, token, ['field'], LAYOUT_OPTION_NAMES + ['placeholder'])
    return FieldInputNode(tag_name, options)


class FieldLabelNode(FormNodeBase):
    template_basename = 'field_label.html'


@register.tag(name='field_label')
def do_field_label(parser, token):
    """
    Usage::

        {% field_label field [layout options...] %}
    """
    tag_name, options = parse_token_arguments(
        parser, token, ['field'], LAYOUT_OPTION_NAMES)
    return FieldLabelNode(tag_name, options)


class FieldNode(FormNodeBase):
    template_basename = 'field.html'
    field_label = FieldLabelNode(None, {})
    field_input = FieldInputNode(None, {})

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        field = options['field']
        if field.is_hidden:
            raise TemplateSyntaxError(
                'Attempting to render hidden field {} as visible'.format(
                    field.name))
        # While Bootstrap has special forms for varius checkbox and radiobutton
        # comibinations, and Django also includes widgets for some such
        # combinations, those are not the default widgets on any form/modelform
        # fields.
        options['is_checkbox'] = isinstance(field.field.widget, CheckboxInput)
        context.update({'_bootstrap_form_options': options})
        rendered_field_label = self.field_label.render(context)
        rendered_field_input = self.field_input.render(context)
        context.pop()
        options.update({
            'rendered_field_label': rendered_field_label,
            'rendered_field_input': rendered_field_input,
        })
        return render_to_string(templates, options)


@register.tag(name='field')
def do_field(parser, token):
    """
    Usage::

        {% field field [layout options...] [placeholder=...] %}
    """
    tag_name, options = parse_token_arguments(
        parser, token, ['field'], LAYOUT_OPTION_NAMES + ['placeholder'])
    return FieldNode(tag_name, options)


class HiddenFieldNode(FormNodeBase):
    template_basename = 'hidden_field.html'

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        field = options['field']
        # NOTE: registering that field has been rendered
        options['touched_fields'].append(field)
        return render_to_string(templates, options)


@register.tag(name='hidden_field')
def do_hidden_field(parser, token):
    """
    Usage::

        {% hidden_field field [layout options...] %}
    """
    tag_name, options = parse_token_arguments(
        parser, token, ['field'], LAYOUT_OPTION_NAMES)
    return HiddenFieldNode(tag_name, options)


class NonFieldErrorsNode(FormNodeBase):
    template_basename = 'non_field_errors.html'

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        form = options['form']
        if form in options['non_field_errors_included']:
            raise TemplateSyntaxError(
                'Non-field errors added multiple times for same form')
        options['non_field_errors_included'].add(form)
        return render_to_string(templates, options)


@register.tag(name='non_field_errors')
def do_non_field_errors(parser, token):
    """
    Usage::

        {% non_field_errors form [layout options...] %}
    """
    tag_name, options = parse_token_arguments(
        parser, token, ['form'], LAYOUT_OPTION_NAMES)
    return NonFieldErrorsNode(tag_name, options)


class FormNode(FormNodeBase):
    template_basename = 'form.html'
    non_field_errors = NonFieldErrorsNode(None, {})
    hidden_field = HiddenFieldNode(None, {})
    visible_field = FieldNode(None, {})

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        form = options['form']
        context.update({'_bootstrap_form_options': options})
        # NOTE: FormBaseNode instances take defaults for options from "parent"
        # by reading from context['_bootstrap_form_options'] --- this includes
        # the options that are mandatory for the tags constructing them ---
        # thus the NonFieldErrorsNode will automatically use the form specified
        # as an option to the FormNode
        rendered_non_field_errors = self.non_field_errors.render(context)
        # ... slightly more work for the FieldNode instances
        rendered_hidden_fields = []
        for field in form.hidden_fields():
            options['field'] = field
            rendered_hidden_fields.append(self.hidden_field.render(context))
        rendered_visible_fields = []
        for field in form.visible_fields():
            options['field'] = field
            rendered_visible_fields.append(self.visible_field.render(context))
        context.pop()
        options.update({
            'rendered_non_field_errors': rendered_non_field_errors,
            'rendered_hidden_fields': rendered_hidden_fields,
            'rendered_visible_fields': rendered_visible_fields,
        })
        return render_to_string(templates, options)


@register.tag(name='form')
def do_form(parser, token):
    """
    Usage::

        {% form form [layout options...] %}
    """
    tag_name, options = parse_token_arguments(
        parser, token, ['form'], LAYOUT_OPTION_NAMES)
    return FormNode(tag_name, options)


class FormButtonsNode(FormNodeBase):
    template_basename = 'form_buttons.html'
    default_options = {
        'submit_label': ugettext_lazy('Save'),
        'delete_label': ugettext_lazy('Delete'),
        'cancel_label': ugettext_lazy('Cancel'),
    }

    def get_cancel_target(self, resolved_options):
        view = resolved_options['view']
        if hasattr(view, 'get_cancel_url'):
            return view.get_cancel_url()
        return None

    def get_delete_target(self, resolved_options):
        view = resolved_options['view']
        if hasattr(view, 'get_delete_url'):
            return view.get_delete_url()
        return None

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        if options['buttons_included']:
            raise TemplateSyntaxError(
                'Form buttons added multiple times to same form')
        options['buttons_included'].append(self)
        if 'cancel_target' not in options:
            options['cancel_target'] = self.get_cancel_target(options)
        if 'delete_target' not in options:
            options['delete_target'] = self.get_delete_target(options)
        return render_to_string(templates, options)


@register.tag(name='form_buttons')
def do_form_buttons(parser, token):
    """
    Usage::

        {% form_buttons [layout options...] [button options...] %}
    """
    tag_name, options = parse_token_arguments(
        parser, token, [], LAYOUT_OPTION_NAMES + FORM_BUTTON_OPTION_NAMES)
    return FormButtonsNode(tag_name, options)


class BootstrapFormNode(BootstrapNode):
    template_basename = 'bootstrap_form.html'
    default_options = {
        'label_class': '',
        'input_class': '',
        'checkbox_class': '',
        'form_method': 'post',
    }

    csrf_token = CsrfTokenNode()
    non_field_errors = NonFieldErrorsNode(None, {})
    form_buttons = FormButtonsNode(None, {})

    def __init__(self, tag_name, options, nodelist):
        super(BootstrapFormNode, self).__init__(tag_name, options)
        self.nodelist = nodelist

    def get_default_options(self, context):
        if '_bootstrap_form_options' in context:
            raise TemplateSyntaxError(
                '{% {} %} should not be used recursively'.format(
                    self.tag_name))
        options = super(BootstrapFormNode, self).get_default_options(context)
        request = context.get('request', None)
        options.update({
            'layout': settings.BOOTSTRAP_FORM_LAYOUT,
            'label_columns': settings.BOOTSTRAP_FORM_LABEL_COLUMNS,
            'input_columns': settings.BOOTSTRAP_FORM_INPUT_COLUMNS,
            'form_action': getattr(request, 'path', ''),
            'touched_fields': [],
            'buttons_included': [],
            'non_field_errors_included': set(),
        })
        return options

    def render(self, context):
        templates = self.get_templates()
        options = self.resolve_options(context)
        context.update({'_bootstrap_form_options': options})
        rendered_csrf_token = self.csrf_token.render(context)
        rendered_content = self.nodelist.render(context)
        if options['buttons_included']:
            rendered_form_buttons = ''
        else:
            rendered_form_buttons = self.form_buttons.render(context)
        context.pop()
        form_enctype = None
        touched_form_fields = collections.defaultdict(list)
        for field in options['touched_fields']:
            touched_form_fields[field.form].append(field.name)
            # If any file fields included, we need to specify enctype...
            if isinstance(field.field, FileField):
                form_enctype = "multipart/form-data"
        for form, fields in touched_form_fields.items():
            # Sanity check: Any field included more than once for the same
            # form?
            for fieldname, count in collections.Counter(fields).items():
                if count > 1:
                    raise TemplateSyntaxError(
                        'Field {} added {} times '
                        'for a form of class {}'.format(
                            fieldname, count, form.__class__.__name__))
            # Sanity check: Any field present on form but *not* included in
            # template?
            missing = set(form.fields.keys()) - set(fields)
            if missing:
                raise TemplateSyntaxError(
                    'Fields {} missing for a form af class {}'.format(
                        list(missing), form.__class__.__name__))

        rendered_non_field_errors = []
        context.update({'_bootstrap_form_options': options})
        for form in touched_form_fields.keys():
            if form in options['non_field_errors_included']:
                continue
            options['form'] = form
            rendered_non_field_errors.append(
                self.non_field_errors.render(context))
        context.pop()

        options.update({
            'rendered_csrf_token': rendered_csrf_token,
            'rendered_non_field_errors': rendered_non_field_errors,
            'rendered_content': rendered_content,
            'rendered_form_buttons': rendered_form_buttons,
            'form_enctype': form_enctype,
        })
        return render_to_string(templates, options)


@register.tag(name='bootstrap_form')
def do_bootstrap_form(parser, token):
    """
    Usage::

        {% bootstrap_form [layout options...] [form options...] [button options...] %}  # noqa
        ...
        [{% form form [layout options...] %}...]
        [{% field formfield [layout options...] %}...]
        [{% field_label formfield [layout options...] %}...]
        [{% field_input formfield [layout options...] %}...]
        ...
        {% endbootstrap_form %}

    Layout options:

    * layout: "horizontal" | "inline" | "basic"
    * label_columns: 1..12
    * input_columns: 1..12
    * label_class: css_class_string
    * input_class: css_class_string
    * checkbox_class: css_class_string

    Form options:

    * form_action: URL
    * form_method: "post" | "get" | ...

    Button options:

    * submit_label: string
    * delete_label: string
    * cancel_label: string
    * cancel_target: URL, False/None for no "cancel"
    * delete_target: URL, False/None for no "delete"
    """
    tag_name, options = parse_token_arguments(
        parser, token, [],
        LAYOUT_OPTION_NAMES + FORM_OPTION_NAMES + FORM_BUTTON_OPTION_NAMES)
    nodelist = parser.parse(('endbootstrap_form',))
    parser.delete_first_token()
    return BootstrapFormNode(tag_name, options, nodelist)
