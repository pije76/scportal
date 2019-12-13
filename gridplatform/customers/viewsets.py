# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from rest_framework import viewsets

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    model = Customer
    serializer_class = CustomerSerializer
    filter_fields = ('name', 'postal_code', 'city')
