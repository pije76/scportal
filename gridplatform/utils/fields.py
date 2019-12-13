# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from decimal import Decimal
import json
import numbers
import re
import sys
import datetime
from io import BytesIO

from PIL import Image

from django import forms
from django.utils import six
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from durationfield.db.models.fields import duration
from south.modelsinspector import add_introspection_rules

from gridplatform.utils import unitconversion
from .format_id import format_mac

# supported input formats for MAC addresses:
# 6 groups of two hex digits, separated by ":", "-" or "."
# 12 hex digits
MAC_FORMATS = [
    '^' + ':'.join(['([0-9A-F]{2})'] * 6) + '$',
    '^' + '-'.join(['([0-9A-F]{2})'] * 6) + '$',
    '^' + '.'.join(['([0-9A-F]{2})'] * 6) + '$',
    '^([0-9A-F]{12})$',
]

HEXDIGITS = re.compile('[0-9A-F]+', re.IGNORECASE)

MAC_RE = re.compile('|'.join(MAC_FORMATS), re.IGNORECASE)


def parse_mac(val):
    """
    :return: The integer value that correspond to the MAC address given.
    :param val:  The given MAC address (many representations supported)

    :see: :func:`gridplatform.utils.format_id.format_mac`.
    """
    if isinstance(val, MacAddress):
        return int(val)
    elif isinstance(val, numbers.Integral):
        return val
    elif isinstance(val, basestring) and MAC_RE.match(val):
        return int(''.join(HEXDIGITS.findall(val)), 16)
    elif isinstance(val, tuple) and len(val) == 1:
        return int(val[0])
    else:
        raise ValueError('Invalid MAC address: %s' % val)


class MacAddress(tuple):
    """
    An immutable MAC address supporting conversion to string and int.
    Can be instantiated from many representations (as supported by
    :func:`.parse_mac`).
    """
    def __new__(cls, addr):
        num_addr = parse_mac(addr)
        return super(MacAddress, cls).__new__(cls, (num_addr,))

    def __repr__(self):
        return '<MacAddress {!s}>'.format(self)

    def __str__(self):
        return format_mac(*self)

    def __int__(self):
        val, = self
        return val


class MacAddressFormField(forms.fields.RegexField):
    """
    A form field for MAC addresses.
    """
    default_error_messages = {
        'invalid': _(u'Invalid MAC address.'),
    }

    def __init__(self, *args, **kwargs):
        defaults = {
            # 6 groups of 2 chars + 5 separators
            'max_length': 17,
        }
        defaults.update(kwargs)
        super(MacAddressFormField, self).__init__(MAC_RE, *args, **defaults)


class MacAddressField(models.Field):
    """
    A model field for MAC addresses.
    """
    description = 'Simple MAC address field'
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        """
        :return: A :class:`.MacAddress`, ``None`` or the empty string.
        """
        if value is None or value == "":
            return value
        else:
            try:
                return MacAddress(value)
            except ValueError:
                raise ValidationError(
                    _(u'not a valid MAC address: %s') % (value,))

    def get_internal_type(self):
        """
        A MAC address is stored in database as a BigIntegerField.
        """
        return 'BigIntegerField'

    def get_prep_lookup(self, lookup_type, value):
        mac = self.to_python(value)
        return super(MacAddressField, self).get_prep_lookup(lookup_type, mac)

    def get_prep_value(self, value):
        if value is None:
            return None
        return int(value)

    def formfield(self, **kwargs):
        """
        The form field of a MacAddressField is by default a
        MacAddressFormField.
        """
        defaults = {
            'form_class': MacAddressFormField,
        }
        defaults.update(kwargs)
        return super(MacAddressField, self).formfield(**defaults)


add_introspection_rules([], [r'^gridplatform.utils.fields.MacAddressField$'])


class JSONEncoder(DjangoJSONEncoder):
    """
    JSON encoder that in addition to what :class:`.DjangoJSONEncoder`
    supports also have limited support (HH:MM:SS) for
    :class:`datetime.timedelta`.
    """

    def default(self, value):
        """
        Adds support for encoding :class:`datetime.timedelta`.
        """
        if isinstance(value, datetime.timedelta):
            assert(value.days == 0)
            assert(value.microseconds == 0)
            hours = value.seconds / (60 * 60)
            minutes = value.seconds / 60 % 60
            seconds = value.seconds % (60 * 60)
            return u"%d:%d:%d" % (hours, minutes, seconds)
        return super(JSONEncoder, self).default(value)


class JSONField(models.TextField):
    """
    Stores the Python representation of JSON in a TextField.  The
    member made available is equivalent with that of C{json.loads()}
    evaluated on the text field.
    """

    description = "JSON field (stored as a string)"

    __metaclass__ = models.SubfieldBase

    def __init__(self, object_hook=None, *args, **kwargs):
        """
        Construct a JSONField.

        All arguments except ``object_hook`` are forwarded directly to
        :class:`django.models.TextField`.

        :param object_hook: An ``object_hook`` that will be forwarded
            to :func:`json.dumps`.  Object hooks are used to convert
            named members to more useful types than the default.
            I.e. if you want anything other than dictionaries, lists,
            unicode strings, integers, float, booleans and None, this
            is where to go.

        :warning: When giving the ``object_hook`` parameter, make sure
            to unittest serialization and deserialization of the
            containing Django model thoroughly.  There is a risk that
            your object hook will output an object that either cannot
            be reserialized, or when reserialized, cannot be
            recognized by your object hook.  Serialization and
            deserialization must be each others inverse.
        """
        self.json_object_hook = object_hook
        super(JSONField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Convert JSON string fetched from wherever (e.g. database or
        the browser) to Python object.
        """
        if value is None or value == "":
            return None

        if isinstance(value, basestring):
            return json.loads(value, object_hook=self.json_object_hook)

        return value

    def get_prep_value(self, value):
        """
        Convert Python object to a JSON string.
        """
        if value == "" or value is None:
            return ""

        return json.dumps(value, cls=JSONEncoder)

    def value_to_string(self, obj):
        """
        Convert field from Python object to a JSON string.
        """
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

    def value_from_object(self, obj):
        """
        Convert object to value, suitable for a Form. In this case the
        JSON string.
        """
        return self.value_to_string(obj)


class SplitHourMinuteWidget(forms.MultiWidget):
    """
    Widget for hour/minute choice.
    """
    def __init__(self, hour_choices=(), minute_choices=(), attrs=None):
        widgets = (forms.Select(attrs=attrs, choices=hour_choices),
                   forms.Select(attrs=attrs, choices=minute_choices))
        super(SplitHourMinuteWidget, self).__init__(widgets, attrs)
        self.hour_choices = hour_choices
        self.minute_choices = minute_choices

    def decompress(self, value):
        if value:
            assert value.total_seconds() >= 0
            hours = int(value.total_seconds() / 60 / 60)
            minutes = int(value.total_seconds() / 60 % 60)
            return [hours, minutes]
        return [None, None]

    def _get_hour_choices(self):
        return self._hour_choices

    def _set_hour_choices(self, value):
        self._hour_choices = self.widgets[0].choices = value

    hour_choices = property(_get_hour_choices, _set_hour_choices)

    def _get_minute_choices(self):
        return self._minute_choices

    def _set_minute_choices(self, value):
        self._minute_choices = self.widgets[1].choices = value

    minute_choices = property(_get_minute_choices, _set_minute_choices)


class SplitHiddenHourMinuteWidget(SplitHourMinuteWidget):
    """
    Hidden widget for hour/minute choice.
    """
    is_hidden = True

    def __init__(self, attrs=None):
        super(SplitHiddenHourMinuteWidget, self).__init__(attrs)
        for widget in self.widgets:
            widget.input_type = 'hidden'
            widget.is_hidden = True


class DurationFormField(forms.MultiValueField):
    """
    Form field for hour/minute choice.

    :ivar hour_choices: A property that makes sure to set hour choices
        correctly.
    :ivar minute_choices: A property that makes sure to set minute
        choices correctly.
    """
    widget = SplitHourMinuteWidget
    hidden_widget = SplitHiddenHourMinuteWidget
    default_error_messages = {
        'invalid_hour': _(u'Select a valid hour.'),
        'invalid_minute': _(u'Select a valid minute.'),
    }

    def __init__(self, hour_choices=None, minute_choices=None,
                 *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        localize = kwargs.get('localize', False)
        if hour_choices is None:
            hour_choices = [
                (n, ungettext_lazy('%d hour', '%d hours', n) % n)
                for n in range(24)]
        if minute_choices is None:
            minute_choices = [
                (n, ungettext_lazy('%02d minute', '%02d minutes', n) % n)
                for n in range(60)]
        fields = (
            forms.TypedChoiceField(
                error_messages={'invalid': errors['invalid_hour']},
                localize=localize, choices=hour_choices,
                coerce=int),
            forms.TypedChoiceField(
                error_messages={'invalid': errors['invalid_minute']},
                localize=localize, choices=minute_choices,
                coerce=int),
        )
        super(DurationFormField, self).__init__(fields, *args, **kwargs)
        self.hour_choices = hour_choices
        self.minute_choices = minute_choices

    def compress(self, data_list):
        if data_list:
            if data_list[0] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_hour'])
            if data_list[1] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_minute'])
            return datetime.timedelta(hours=data_list[0], minutes=data_list[1])
        return None

    def _get_hour_choices(self):
        return self._hour_choices

    def _set_hour_choices(self, value):
        self._hour_choices = self.widget.hour_choices = value

    hour_choices = property(_get_hour_choices, _set_hour_choices)

    def _get_minute_choices(self):
        return self._minute_choices

    def _set_minute_choices(self, value):
        self._minute_choices = self.widget.minute_choices = value

    minute_choices = property(_get_minute_choices, _set_minute_choices)


class DurationField(duration.DurationField):
    """
    Model field for duration with hour/minute choice form.
    """
    def formfield(self, **kwargs):
        """
        The default form field of a :class:`.DurationField` is a
        :class:`.DurationFormField`.
        """
        defaults = {'form_class': DurationFormField}
        defaults.update(kwargs)
        return super(DurationField, self).formfield(**defaults)


add_introspection_rules([], [r'^gridplatform.utils.fields.DurationField$'])


class PercentField(models.DecimalField):
    """
    A :class:`~django.db.models.DecimalField` with three digits before
    decimal marker, to include special case of 100%.
    """
    DEFAULT_VALIDATORS = [
        validators.MaxValueValidator(Decimal('100.0')),
        validators.MinValueValidator(Decimal('0.0')),
    ]

    def __init__(self, *args, **kwargs):
        """
        :keyword default: Default value is 0%.
        :keyword validators: Default validators allow values in the range
            0% ... 100%.
        """
        defaults = {
            'max_digits': 4,
            'decimal_places': 1,
            'default': Decimal('0.0'),
            'validators': self.DEFAULT_VALIDATORS,
        }
        defaults.update(kwargs)
        return super(PercentField, self).__init__(*args, **defaults)

add_introspection_rules([], [r'^gridplatform.utils.fields.PercentField$'])


class ImageFieldWithLoadCheck(forms.ImageField):
    """
    Image Form field with check for corrupted image
    """
    def to_python(self, data):
        """
        :raise ValidationError: If ``data`` is a corrupted image.
        """
        f = super(ImageFieldWithLoadCheck, self).to_python(data)
        if f is None:
            return None
        # We need to get a file object for Pillow. We might have a path or
        # we might have to read the data into memory.
        if hasattr(data, 'temporary_file_path'):
            file = data.temporary_file_path()
        else:
            if hasattr(data, 'read'):
                file = BytesIO(data.read())
            else:
                file = BytesIO(data['content'])
        try:
            Image.open(file).load()
        except Exception:
            # Pillow doesn't recognize it as an image.
            six.reraise(ValidationError, ValidationError(
                _('The image you have uploaded is corrupted'),
                code='invalid_image',
            ), sys.exc_info()[2])

        if hasattr(f, 'seek') and callable(f.seek):
            f.seek(0)
        return f


class ImageModelFieldWithLoadCheck(models.ImageField):
    """
    Image model field to set ImageFieldWithLoadCheck as default formfield
    """
    def formfield(self, **kwargs):
        """
        The form field of an :class:`.ImageModelFieldWithLoadCheck` is a
        :class:`.ImageFieldWithLoadCheck`.
        """
        defaults = {'form_class': ImageFieldWithLoadCheck}
        defaults.update(kwargs)
        return super(ImageModelFieldWithLoadCheck, self).formfield(**defaults)


add_introspection_rules([], [
    r'^gridplatform.utils.fields.ImageModelFieldWithLoadCheck$'])


class BigAutoField(models.AutoField):
    """
    from https://djangosnippets.org/snippets/1244/

    Updated to work with present version of Python and Django, at the expense
    of losing support for other database backends than postgresql.
    """

    def db_type(self, connection):
        # only support for postgres
        return 'bigserial'

    def get_internal_type(self):
        return "BigAutoField"

    def to_python(self, value):
        if value is None:
            return value
        try:
            return long(value)
        except (TypeError, ValueError):
            raise ValidationError(
                _("This value must be a long integer."))


add_introspection_rules([], [
    r'^gridplatform.utils.fields.BigAutoField$'])


class BuckinghamField(models.CharField):
    """
    Field for strings representing Buckingham units and validated as
    such.
    """
    def __init__(self, *args, **kwargs):
        defaults = {'max_length': 100}
        defaults.update(kwargs)
        super(BuckinghamField, self).__init__(*args, **defaults)

    def validate(self, value, model_instance):
        """
        :raise ValidationError: If given value is not a valid Buckingham
            unit.
        """
        if value:
            try:
                unitconversion.PhysicalQuantity(1, value)
            except:
                raise ValidationError('invalid unit %s' % value)
        super(BuckinghamField, self).validate(value, model_instance)

    def get_prep_value(self, value):
        """
        Overload of :meth:`django.db.models.CharField.get_prep_value` to
        make sure that no invalid buckingham unit is saved ever.
        """
        unitconversion.PhysicalQuantity(1, value)
        return super(BuckinghamField, self).get_prep_value(value)


add_introspection_rules([], [
    r"^gridplatform\.utils\.fields\.BuckinghamField"])
