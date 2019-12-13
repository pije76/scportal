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
        u'datasources.rawdata': {
            'Meta': {'ordering': "[u'timestamp']", 'unique_together': "((u'datasource', u'timestamp'),)", 'object_name': 'RawData'},
            'datasource': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['datasources.DataSource']", 'on_delete': 'models.PROTECT', 'db_index': 'False'}),
            'id': ('gridplatform.utils.fields.BigAutoField', [], {'primary_key': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'value': ('django.db.models.fields.BigIntegerField', [], {})
        }
    }

    complete_apps = ['datasources']