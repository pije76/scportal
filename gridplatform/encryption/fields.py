# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import base64

import django.db.models
import django.forms
from django.utils.translation import ugettext_lazy as _
from south.modelsinspector import add_introspection_rules


class Base64Field(django.db.models.TextField):
    """
    Store binary data (bytearrays) as base64-encoded text in the database.

    :note: While strings may contain binary data in Python, using strings for
        the binary data, when we also use strings for the base64-encoded data,
        would leave us unable to detect whether a string had already been
        decoded.
    """
    # trying to decode and catching the exception might be reasonably reliably
    # for current use, but would break mysteriously for decoded strings that
    # are also valid as base64-encodings of something else...

    __metaclass__ = django.db.models.SubfieldBase

    def __init__(self, *args, **kwargs):
        # not "editable" by default; intended for binary data which does not
        # make sense to use directly in forms
        defaults = {'editable': False}
        defaults.update(kwargs)
        super(Base64Field, self).__init__(*args, **defaults)

    def to_python(self, value):
        if isinstance(value, bytearray):
            return value
        return bytearray(base64.decodestring(value))

    def get_prep_value(self, value):
        return base64.encodestring(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)


add_introspection_rules([], ["^gridplatform\.encryption\.fields\.Base64Field"])


class EncryptionMembersAccessor(object):
    """
    Descriptor for accessing encrypted/plaintext values on an object.

    This is used for some simple business logic: Modifying the plaintext
    invalidates the ciphertext, modifying the ciphertext invalidates the
    plaintext.

    Parameterised on the object member names to read/write --- the logic for
    the plaintext and ciphertext is the same, just with the member names
    swapped.

    We assume that the members are accessible directly; in particular, this
    will not work to wrap a field with the same name as itself.  For the
    current use, those members will need to be accessible for
    encryption/decryption anyway, as in that case, we *do* add a value for one
    field without invalidating the other, i.e. it should not go through this
    descriptor.
    """

    def __init__(self, name, other_name):
        self.name = name
        self.other_name = other_name

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')
        return getattr(obj, self.name)

    def __set__(self, obj, value):
        setattr(obj, self.name, value)
        setattr(obj, self.other_name, None)


class EncryptedField(object):
    """
    Base class for encrypted fields; wraps its data values in EncryptedData
    objects --- the ciphertext used towards the database; the plaintext used as
    the 'string representation' otherwise.

    Rules for conversion between plaintext and ciphertext are implemented by
    the EncryptedData class.

    :note: ``field.attname`` and ``field.name`` should be equal; that they *can* be
        set to different values is only relevant for foreign keys; as Django code
        assumes them to be equivalent otherwise.

    Interface towards forms:

    * form field name is taken from ``field.name``
    * data is read with ``field.value_from_object(obj)``
    * data is written with ``field.save_form_data(obj, val)``

    Interface towards serialisation:

    * on serialisation, field._get_val_from_obj(obj) is checked for "primitives"
      --- the relevant part being that None here means that the result is None
    * if not a "primitive", the serialised form is ``field.value_to_string(obj)``
    * data is deserialised with ``field.to_python(val)``
    * deserialised data will be stored/set with ``setattr(obj, field.attname, val)``

    For :class:`.EncryptedField`, ``field.name``/``field.attname`` is the name of a
    property which gives the encrypted data in base64-encoded form; so the methods
    inherited from :class:`models.Field` do the right thing.
    """
    def __init__(self, *args, **kwargs):
        super(EncryptedField, self).__init__(*args, **kwargs)

        if kwargs.get('null', False):
            # We can't have that EncryptedFields are created with null=True.
            # However, that does not apply to south.
            import traceback
            stack = traceback.extract_stack()
            via_south = any([
                filename.endswith("site-packages/south/migration/migrators.py")
                for (filename, line_number, function_name, text)
                in stack])
            assert via_south

    def contribute_to_class(self, cls, name):
        """
        An ecrypted field, ``field``, will attach to its owning
        L{EncryptedModel} class the following members:

          - ``field``: holding the encrypted field value.
          - ``field_plain``: holding the decrypted field value.
          - ``_field_decrypt()``: a field specific private decryption method.
          - ``_field_encrypt()``: a field specific private encryption method.

        The ``field`` and ``field_plain`` members are designed so that
        when setting either, the other will be set to ``None``.
        """
        if not cls._meta.abstract:
            from .models import EncryptedModel
            # Should only be used on EncryptedModel instances --- this is a
            # sanity check/detector of broken code during development.
            if not issubclass(cls, EncryptedModel):
                # Somewhat complicated check; model classes generated by South
                # should be allowed to work...
                import traceback
                stack = traceback.extract_stack()
                via_south = any([
                    filename.endswith("site-packages/south/orm.py")
                    for (filename, line_number, function_name, text)
                    in stack])
                if not via_south:
                    assert issubclass(cls, EncryptedModel), \
                        'EncryptedField requires a subclass of EncryptedModel'
            # Only act on concrete classes (on abstract base classes, we get
            # called both on the base and on the concrete subclass).
            #
            # The one field becomes 4 members of the model class:
            # * 2 member variables, holding the plaintext and ciphertext.
            # * 2 descriptors, giving access to the member variables with the
            #   appropriate business logic --- setting one clears the other,
            #   reading a cleared value is an error.
            #
            cipher_member = '_{}_ciphertext'.format(name)
            plain_member = '_{}_plaintext'.format(name)
            # NOTE: Intentionally unwieldy names to discourage use...
            self._ciphertext_attribute = cipher_member
            self._plaintext_attribute = plain_member
            # NOTE: _cipher_property will become the "real" name --- using the
            # plain name here means that form fields will get the plain name,
            # but also means that accessing model_obj.name in code gives the
            # encrypted version...
            self._cipher_property = name
            self._plain_property = '{}_plain'.format(name)
            #
            # Set up the descriptors for wrapping the actual data members.
            setattr(cls, self._plain_property,
                    EncryptionMembersAccessor(plain_member, cipher_member))
            setattr(cls, self._cipher_property,
                    EncryptionMembersAccessor(cipher_member, plain_member))
            # Ensure that we use the business logic for access to the encrypted
            # field towards the database and serialisation.  When set,
            # self.name overrides the name parameter to contribute_to_class.
            self.name = self._cipher_property
        super(EncryptedField, self).contribute_to_class(cls, name)

    def save_form_data(self, instance, data):
        """
        Forms access the "plaintext" property, with the same business logic
        as when accessing the specified member name on the model object.
        """
        setattr(instance, self._plain_property, data)

    def value_from_object(self, instance):
        """
        Read "plaintext" for use in form.
        """
        return getattr(instance, self._plain_property)

    def get_internal_type(self):
        """
        Always store as "arbitrary length" text; trying to give a sensible
        "max_length" towards the database becomes too messy with
        base64-encoding and when would entail some hacks to use different
        max_lengths for input-validation and database field length.
        """
        return "TextField"


# Does *not* use the SubfieldBase metaclass --- we need our own magic
# instead...
class EncryptedTextField(EncryptedField, django.db.models.TextField):
    """
    TextField with encrypted data via EncryptedField.
    """
    description = _('Encrypted text')


# Does *not* use the SubfieldBase metaclass --- we need our own magic
# instead...
class EncryptedCharField(EncryptedField, django.db.models.CharField):
    """
    CharField with encrypted data via EncryptedField.
    """
    description = _("Encrypted string (up to %(max_length)s)")


# Does *not* use the SubfieldBase metaclass --- we need our own magic
# instead...
class EncryptedEmailField(EncryptedField, django.db.models.EmailField):
    """
    EmailField with encrypted data via EncryptedField.
    """
    description = _("encrypted E-mail address")


add_introspection_rules([], [
    "^gridplatform\.encryption\.fields\.EncryptedTextField",
    "^gridplatform\.encryption\.fields\.EncryptedCharField",
    "^gridplatform\.encryption\.fields\.EncryptedEmailField",
])
