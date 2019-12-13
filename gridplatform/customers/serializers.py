# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from gridplatform.rest import serializers
from .models import Customer


class CustomerSerializer(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')
    vat = serializers.CharField(source='vat_plain', required=False)
    address = serializers.CharField(source='address_plain', required=False)
    postal_code = serializers.CharField(source='postal_code_plain', required=False)
    city = serializers.CharField(source='city_plain', required=False)
    phone = serializers.CharField(source='phone_plain', required=False)
    production_a_unit = serializers.CharField(source='production_a_unit_plain', required=False)
    production_b_unit = serializers.CharField(source='production_b_unit_plain', required=False)
    production_c_unit = serializers.CharField(source='production_c_unit_plain', required=False)
    production_d_unit = serializers.CharField(source='production_d_unit_plain', required=False)
    production_e_unit = serializers.CharField(source='production_e_unit_plain', required=False)

    class Meta:
        model = Customer
        fields = ('url', 'id', 'name', 'vat', 'address', 'postal_code', 'city',
                  'phone', 'timezone', 'production_a_unit',
                  'production_b_unit', 'production_c_unit',
                  'production_d_unit', 'production_e_unit')
