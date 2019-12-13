# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.template import Context
from django.template import Template
from django.template.base import TemplateSyntaxError
from django.test import RequestFactory
from django.test import SimpleTestCase
from django.test.utils import override_settings


@override_settings(BOOTSTRAP_THEME='base')
class IconTemplatetagTest(SimpleTestCase):
    def test_icon_normal(self):
        template = Template('{% load bootstrap_tags %}{% icon "compass" %}')
        self.assertInHTML(
            '<i class="fa fa-compass"></i>',
            template.render(Context({})))

    def test_icon_2x(self):
        template = Template(
            '{% load bootstrap_tags %}{% icon "eur" size="2x" %}')
        self.assertInHTML(
            '<i class="fa fa-eur fa-2x"></i>',
            template.render(Context({})))

    def test_icon_doesnotexist(self):
        template = Template(
            '{% load bootstrap_tags %}{% icon "doesnotexist" %}')
        with self.assertRaises(TemplateSyntaxError):
            template.render(Context({}))

    def test_icon_invalidsize(self):
        template = Template(
            '{% load bootstrap_tags %}{% icon "compass" size="invalid" %}')
        with self.assertRaises(TemplateSyntaxError):
            template.render(Context({}))


@override_settings(BOOTSTRAP_THEME='base')
class PanelTemplateTagTest(SimpleTestCase):
    def test_simple(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% panel "MyPanelTitle" %}'
            '<p class="some-class">text</p>'
            '{% endpanel %}')
        context = Context({})
        result = template.render(context)
        self.assertIn("MyPanelTitle", result)
        self.assertInHTML('<p class="some-class">text</p>', result)

    def test_var_title(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% with title="Hello" %}'
            '{% panel title %}'
            '<p class="some-class">text</p>'
            '{% endpanel %}'
            '{% endwith %}')
        context = Context({})
        result = template.render(context)
        self.assertIn("Hello", result)
        self.assertInHTML('<p class="some-class">text</p>', result)

    def test_buttons(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% panel "MyPanelTitle" %}'
            '<a href="http://example.com/"><i class="icon-stuff"></i></a>'
            '{% endpanelbuttons %}'
            '<p class="some-class">text</p>'
            '{% endpanel %}')
        context = Context({})
        result = template.render(context)
        self.assertIn("MyPanelTitle", result)
        self.assertInHTML(
            '<a href="http://example.com/"><i class="icon-stuff"></i></a>',
            result)
        self.assertInHTML('<p class="some-class">text</p>', result)

    def test_vars_inside(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% with foo="hello" %}'
            '{% panel "MyPanelTitle" %}'
            '{% with bar="world" %}'
            '{{ foo }} {{ bar }}'
            '{% endwith %}'
            '{% endpanelbuttons %}'
            '{% with bar="x" %}'
            '{{ foo }} {{ bar }}'
            '{% endwith %}'
            '{% endpanel %}'
            '{% endwith %}')
        context = Context({})
        result = template.render(context)
        self.assertIn("MyPanelTitle", result)
        self.assertIn("hello world", result)
        self.assertIn("hello x", result)


class TestForm(forms.Form):
    name = forms.CharField(max_length=50)
    is_admin = forms.BooleanField(
        label='Is admin', help_text='User is administrator')

    def clean(self):
        # silly check to introduce non-field errors
        cleaned_data = super(TestForm, self).clean()
        name = cleaned_data.get('name')
        is_admin = cleaned_data.get('is_admin')
        if name and name.startswith('_') and not is_admin:
            raise forms.ValidationError(
                b'Invalid name for non-admin user: {}'.format(name))
        return cleaned_data


@override_settings(
    BOOTSTRAP_THEME='base',
    BOOTSTRAP_FORM_LAYOUT='horizontal',
    BOOTSTRAP_FORM_LABEL_COLUMNS=2,
    BOOTSTRAP_FORM_INPUT_COLUMNS=10,
)
class FormTagsTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

    def test_no_form(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% endbootstrap_form %}'
        )
        context = Context({'request': self.request})
        result = template.render(context)
        self.assertIn('<form', result)
        self.assertIn('<button type="submit"', result)
        self.assertIn('</form>', result)

    def test_form(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% form form %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        result = template.render(context)
        self.assertIn('type="text"', result)
        self.assertIn('name="name"', result)
        self.assertIn('type="checkbox"', result)
        self.assertIn('name="is_admin"', result)
        self.assertIn('Is admin', result)
        self.assertIn('User is administrator', result)

    def test_form_wrong_nesting(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% form form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        with self.assertRaises(TemplateSyntaxError):
            template.render(context)

    def test_field(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% field form.name %}'
            '{% field form.is_admin %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        result = template.render(context)
        self.assertIn('type="text"', result)
        self.assertIn('name="name"', result)
        self.assertIn('type="checkbox"', result)
        self.assertIn('name="is_admin"', result)
        self.assertIn('Is admin', result)
        self.assertIn('User is administrator', result)

    def test_field_wrong_nesting(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% field form.name %}'
            '{% field form.is_admin %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        with self.assertRaises(TemplateSyntaxError):
            template.render(context)

    def test_field_missing(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% field form.name %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        with self.assertRaises(TemplateSyntaxError):
            template.render(context)

    def test_field_repeated(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% field form.name %}'
            '{% field form.is_admin %}'
            '{% field form.is_admin %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        with self.assertRaises(TemplateSyntaxError):
            template.render(context)

    def test_form_field_repeated(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% field form.name %}'
            '{% form form %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        with self.assertRaises(TemplateSyntaxError):
            template.render(context)

    def test_buttons(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% form_buttons %}'
            '{% endbootstrap_form %}'
        )
        context = Context({
            'request': self.request,
        })
        result = template.render(context)
        self.assertIn('<button type="submit"', result)

    def test_buttons_repeated(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% form_buttons %}'
            '{% form_buttons %}'
            '{% endbootstrap_form %}'
        )
        context = Context({
            'request': self.request,
        })
        with self.assertRaises(TemplateSyntaxError):
            template.render(context)

    def test_input(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% field_input form.name %}'
            '{% field_input form.is_admin %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        result = template.render(context)
        self.assertIn('type="text"', result)
        self.assertIn('name="name"', result)
        self.assertIn('type="checkbox"', result)
        self.assertIn('name="is_admin"', result)
        self.assertNotIn('Is admin', result)
        self.assertIn('User is administrator', result)
        pass

    def test_label(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% field_label form.name %}'
            '{% field_label form.is_admin %}'
            '{% field_input form.name %}'
            '{% field_input form.is_admin %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        result = template.render(context)
        self.assertIn('type="text"', result)
        self.assertIn('name="name"', result)
        self.assertIn('type="checkbox"', result)
        self.assertIn('name="is_admin"', result)
        self.assertIn('Is admin', result)
        self.assertIn('User is administrator', result)

    def test_hidden(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% hidden_field form.name %}'
            '{% hidden_field form.is_admin %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        result = template.render(context)
        self.assertNotIn('type="text"', result)
        self.assertIn('name="name"', result)
        self.assertNotIn('type="checkbox"', result)
        self.assertIn('name="is_admin"', result)
        self.assertNotIn('Is admin', result)
        self.assertNotIn('User is administrator', result)

    def test_outer_arguments(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form label_columns=7 '
            'input_columns=3 form_action="/hello/" form_method="get" %}'
            '{% form form %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        result = template.render(context)
        self.assertIn('7', result)
        self.assertIn('3', result)
        self.assertIn('action="/hello/"', result)
        self.assertIn('method="get"', result)

    def test_form_arguments(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form label_columns=7 input_columns=3 %}'
            '{% form form label_columns=2 input_columns=4 %}'
            '{% form_buttons label_columns=1 input_columns=6 %}'
            '{% endbootstrap_form %}'
        )
        form = TestForm()
        context = Context({
            'request': self.request,
            'form': form,
        })
        result = template.render(context)
        self.assertNotIn('7', result)
        self.assertNotIn('3', result)
        self.assertIn('2', result)
        self.assertIn('4', result)
        self.assertIn('1', result)
        self.assertIn('6', result)

    def test_autoinsert_several_non_field_errors(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% field form_a.name %}'
            '{% field form_a.is_admin %}'
            '{% field form_b.name %}'
            '{% field form_b.is_admin %}'
            '{% endbootstrap_form %}'
        )
        form_a = TestForm({'name': '_invalid_a', 'is_admin': False})
        form_b = TestForm({'name': '_invalid_b', 'is_admin': False})
        context = Context({
            'request': self.request,
            'form_a': form_a,
            'form_b': form_b,
        })
        result = template.render(context)
        self.assertIn('Invalid name for non-admin user: _invalid_a', result)
        self.assertIn('Invalid name for non-admin user: _invalid_b', result)

    def test_autoinsert_single_non_field_errors(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% non_field_errors form_a %}'
            '{% field form_a.name %}'
            '{% field form_a.is_admin %}'
            '{% field form_b.name %}'
            '{% field form_b.is_admin %}'
            '{% endbootstrap_form %}'
        )
        form_a = TestForm({'name': '_invalid_a', 'is_admin': False})
        form_b = TestForm({'name': '_invalid_b', 'is_admin': False})
        context = Context({
            'request': self.request,
            'form_a': form_a,
            'form_b': form_b,
        })
        result = template.render(context)
        self.assertIn('Invalid name for non-admin user: _invalid_a', result)
        self.assertIn('Invalid name for non-admin user: _invalid_b', result)
        self.assertEqual(
            result.find('Invalid name for non-admin user: _invalid_a'),
            result.rfind('Invalid name for non-admin user: _invalid_a'))

    def test_non_field_errors_match_failing(self):
        template = Template(
            '{% load bootstrap_tags %}'
            '{% bootstrap_form %}'
            '{% non_field_errors form_a %}'
            '{% field form_a.name %}'
            '{% field form_a.is_admin %}'
            '{% field form_b.name %}'
            '{% field form_b.is_admin %}'
            '{% endbootstrap_form %}'
        )
        form_a = TestForm({'name': 'valid_a', 'is_admin': False})
        form_b = TestForm({'name': '_invalid_b', 'is_admin': False})
        context = Context({
            'request': self.request,
            'form_a': form_a,
            'form_b': form_b,
        })
        result = template.render(context)
        self.assertNotIn('Invalid name for non-admin user: _invalid_a', result)
        self.assertNotIn('Invalid name for non-admin user: valid_a', result)
        self.assertIn('Invalid name for non-admin user: _invalid_b', result)
