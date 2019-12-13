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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'datasources.datasource': {
            'Meta': {'object_name': 'DataSource'},
            'hardware_id': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subclass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.PROTECT', 'to': u"orm['contenttypes.ContentType']"}),
            'unit': ('gridplatform.utils.fields.BuckinghamField', [], {'max_length': '100'})
        },
        u'provider_datasources.providerdatasource': {
            'Meta': {'object_name': 'ProviderDataSource'},
            u'datasource_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['datasources.DataSource']", 'unique': 'True', 'primary_key': 'True'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['providers.Provider']"})
        },
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

    complete_apps = ['provider_datasources']