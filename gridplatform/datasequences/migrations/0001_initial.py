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
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'customers.collection': {
            'Meta': {'object_name': 'Collection'},
            'billing_installation_number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'billing_meter_number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'comment': ('gridplatform.encryption.fields.EncryptedTextField', [], {'blank': 'True'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['customers.Customer']", 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'encryption_data_initialization_vector': ('gridplatform.encryption.fields.Base64Field', [], {}),
            'gauge_colours': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'gauge_lower_threshold': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'gauge_max': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'gauge_min': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'gauge_preferred_unit': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'gauge_upper_threshold': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'hidden_on_details_page': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hidden_on_reports_page': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('imagekit.models.fields.ProcessedImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "u'children'", 'null': 'True', 'to': u"orm['customers.Collection']"}),
            'relay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['devices.Meter']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'role': ('django.db.models.fields.IntegerField', [], {}),
            'subclass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.PROTECT', 'to': u"orm['contenttypes.ContentType']"}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'utility_type': ('django.db.models.fields.IntegerField', [], {})
        },
        u'customers.customer': {
            'Meta': {'ordering': "[u'id']", 'object_name': 'Customer'},
            'address': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'city': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '30', 'blank': 'True'}),
            'contact_email': ('gridplatform.encryption.fields.EncryptedEmailField', [], {'max_length': '50', 'blank': 'True'}),
            'contact_name': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'contact_phone': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'country_code': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '3', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'null': 'True', 'to': u"orm['users.User']"}),
            'currency_unit': ('gridplatform.utils.fields.BuckinghamField', [], {'default': "u'currency_dkk'", 'max_length': '100'}),
            'electricity_consumption': ('django.db.models.fields.CharField', [], {'default': "u'kilowatt*hour'", 'max_length': '50'}),
            'electricity_instantaneous': ('django.db.models.fields.CharField', [], {'default': "u'kilowatt'", 'max_length': '50'}),
            'electricity_tariff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'electricity_tariff_set'", 'null': 'True', 'to': u"orm['measurementpoints.DataSeries']"}),
            'encryption_data_initialization_vector': ('gridplatform.encryption.fields.Base64Field', [], {}),
            'gas_consumption': ('django.db.models.fields.CharField', [], {'default': "u'meter*meter*meter'", 'max_length': '50'}),
            'gas_instantaneous': ('django.db.models.fields.CharField', [], {'default': "u'meter*meter*meter*hour^-1'", 'max_length': '50'}),
            'gas_tariff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'gas_tariff_set'", 'null': 'True', 'to': u"orm['measurementpoints.DataSeries']"}),
            'heat_consumption': ('django.db.models.fields.CharField', [], {'default': "u'kilowatt*hour'", 'max_length': '50'}),
            'heat_instantaneous': ('django.db.models.fields.CharField', [], {'default': "u'kilowatt'", 'max_length': '50'}),
            'heat_tariff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'heat_tariff_set'", 'null': 'True', 'to': u"orm['measurementpoints.DataSeries']"}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'industry_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['salesopportunities.IndustryType']", 'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50'}),
            'oil_consumption': ('django.db.models.fields.CharField', [], {'default': "u'meter*meter*meter'", 'max_length': '50'}),
            'oil_instantaneous': ('django.db.models.fields.CharField', [], {'default': "u'meter*meter*meter*hour^-1'", 'max_length': '50'}),
            'oil_tariff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'oil_tariff_set'", 'null': 'True', 'to': u"orm['measurementpoints.DataSeries']"}),
            'phone': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'postal_code': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '10', 'blank': 'True'}),
            'production_a_unit': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'production_b_unit': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'production_c_unit': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'production_d_unit': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'production_e_unit': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['providers.Provider']"}),
            'temperature': ('django.db.models.fields.CharField', [], {'default': "u'celsius'", 'max_length': '50'}),
            'timezone': ('timezones2.models.TimeZoneField', [], {'max_length': '64'}),
            'vat': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '20', 'blank': 'True'}),
            'water_consumption': ('django.db.models.fields.CharField', [], {'default': "u'meter*meter*meter'", 'max_length': '50'}),
            'water_instantaneous': ('django.db.models.fields.CharField', [], {'default': "u'meter*meter*meter*hour^-1'", 'max_length': '50'}),
            'water_tariff': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'water_tariff_set'", 'null': 'True', 'to': u"orm['measurementpoints.DataSeries']"})
        },
        u'customers.location': {
            'Meta': {'object_name': 'Location'},
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['customers.Customer']", 'blank': 'True'}),
            'encryption_data_initialization_vector': ('gridplatform.encryption.fields.Base64Field', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "u'children'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': u"orm['customers.Location']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        u'datasequences.energypervolumedatasequence': {
            'Meta': {'object_name': 'EnergyPerVolumeDataSequence'},
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['customers.Customer']"}),
            'encryption_data_initialization_vector': ('gridplatform.encryption.fields.Base64Field', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '200'}),
            'subclass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.PROTECT', 'to': u"orm['contenttypes.ContentType']"})
        },
        u'datasequences.energypervolumeperiod': {
            'Meta': {'object_name': 'EnergyPerVolumePeriod'},
            'datasequence': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'period_set'", 'to': u"orm['datasequences.EnergyPerVolumeDataSequence']"}),
            'datasource': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['datasources.DataSource']", 'on_delete': 'models.PROTECT'}),
            'from_timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'datasequences.nonaccumulationdatasequence': {
            'Meta': {'object_name': 'NonaccumulationDataSequence'},
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['customers.Customer']"}),
            'encryption_data_initialization_vector': ('gridplatform.encryption.fields.Base64Field', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '200'}),
            'subclass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.PROTECT', 'to': u"orm['contenttypes.ContentType']"}),
            'unit': ('gridplatform.utils.fields.BuckinghamField', [], {'max_length': '100'})
        },
        u'datasequences.nonaccumulationofflinetolerance': {
            'Meta': {'object_name': 'NonaccumulationOfflineTolerance'},
            'datasequence': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "u'offlinetolerance'", 'unique': 'True', 'to': u"orm['datasequences.NonaccumulationDataSequence']"}),
            'hours': ('django.db.models.fields.PositiveIntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'datasequences.nonaccumulationperiod': {
            'Meta': {'object_name': 'NonaccumulationPeriod'},
            'datasequence': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'period_set'", 'to': u"orm['datasequences.NonaccumulationDataSequence']"}),
            'datasource': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['datasources.DataSource']", 'on_delete': 'models.PROTECT'}),
            'from_timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'datasources.datasource': {
            'Meta': {'object_name': 'DataSource'},
            'hardware_id': ('django.db.models.fields.CharField', [], {'max_length': '120', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subclass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.PROTECT', 'to': u"orm['contenttypes.ContentType']"}),
            'unit': ('gridplatform.utils.fields.BuckinghamField', [], {'max_length': '100'})
        },
        u'devices.agent': {
            'Meta': {'ordering': "[u'location', u'mac']", 'object_name': 'Agent'},
            'add_mode': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['customers.Customer']", 'on_delete': 'models.PROTECT'}),
            'device_serial': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'device_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hw_major': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'hw_minor': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'hw_revision': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'hw_subrevision': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['customers.Location']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'mac': ('gridplatform.utils.fields.MacAddressField', [], {'unique': 'True'}),
            'no_longer_in_use': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'online': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'online_since': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'sw_major': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'sw_minor': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'sw_revision': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'sw_subrevision': ('django.db.models.fields.CharField', [], {'max_length': '12'})
        },
        u'devices.meter': {
            'Meta': {'ordering': "[u'connection_type', u'manufactoring_id', u'id']", 'object_name': 'Meter'},
            'agent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['devices.Agent']", 'on_delete': 'models.PROTECT'}),
            'connection_type': ('django.db.models.fields.IntegerField', [], {}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['customers.Customer']", 'on_delete': 'models.PROTECT'}),
            'device_serial': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'device_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'encryption_data_initialization_vector': ('gridplatform.encryption.fields.Base64Field', [], {}),
            'hw_major': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'hw_minor': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'hw_revision': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'hw_subrevision': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'joined': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['customers.Location']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'manual_mode': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'manufactoring_id': ('django.db.models.fields.BigIntegerField', [], {}),
            'name': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '50', 'blank': 'True'}),
            'online': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'online_since': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'relay_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'relay_on': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sw_major': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'sw_minor': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'sw_revision': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'sw_subrevision': ('django.db.models.fields.CharField', [], {'max_length': '12'})
        },
        u'measurementpoints.dataseries': {
            'Meta': {'ordering': "[u'role', u'id']", 'object_name': 'DataSeries'},
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['customers.Customer']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'graph': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['measurementpoints.Graph']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('legacy.measurementpoints.fields.DataRoleField', [], {}),
            'subclass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.PROTECT', 'to': u"orm['contenttypes.ContentType']"}),
            'unit': ('gridplatform.utils.fields.BuckinghamField', [], {'max_length': '100', 'blank': 'True'}),
            'utility_type': ('django.db.models.fields.IntegerField', [], {})
        },
        u'measurementpoints.graph': {
            'Meta': {'ordering': "[u'role', u'id']", 'unique_together': "((u'collection', u'role'),)", 'object_name': 'Graph'},
            'collection': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['customers.Collection']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('legacy.measurementpoints.fields.DataRoleField', [], {})
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
        },
        u'salesopportunities.industrytype': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'IndustryType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'users.user': {
            'Meta': {'ordering': "[u'user_type', u'name', u'id']", 'object_name': 'User', '_ormbases': [u'auth.User']},
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['customers.Customer']", 'null': 'True', 'blank': 'True'}),
            'e_mail': ('gridplatform.encryption.fields.EncryptedEmailField', [], {'max_length': '75'}),
            'encryption_data_initialization_vector': ('gridplatform.encryption.fields.Base64Field', [], {}),
            'encryption_key_initialization_vector': ('gridplatform.encryption.fields.Base64Field', [], {}),
            'encryption_private_key': ('gridplatform.encryption.fields.Base64Field', [], {}),
            'encryption_public_key': ('gridplatform.encryption.fields.Base64Field', [], {}),
            'mobile': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '20', 'blank': 'True'}),
            'name': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '60'}),
            'phone': ('gridplatform.encryption.fields.EncryptedCharField', [], {'max_length': '20'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['providers.Provider']", 'null': 'True', 'blank': 'True'}),
            u'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'user_type': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['datasequences']