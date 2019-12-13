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
        u'global_datasources.globaldatasource': {
            'Meta': {'unique_together': "((u'app_label', u'codename', u'country'),)", 'object_name': 'GlobalDataSource', '_ormbases': [u'datasources.DataSource']},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'country': ('django_countries.fields.CountryField', [], {'max_length': '2'}),
            u'datasource_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['datasources.DataSource']", 'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '120'})
        }
    }

    complete_apps = ['global_datasources']