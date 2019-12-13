# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        u'providers.provider': {
            'Meta': {'object_name': 'Provider'},
            'address': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '100'}),
            'city': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '100'}),
            'cvr': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '100'}),
            'encryption_data_initialization_vector': ('gridplatform.encryption.fields.Base64Field', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50'}),
            'zipcode': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['providers']