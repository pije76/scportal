from rest_framework.response import Response
from rest_framework import viewsets

from energymanager.price_relay_site import serializers
from .models import PriceRelayProject


class RelaySettingsViewSet(viewsets.ReadOnlyModelViewSet):
    model = PriceRelayProject
    serializer_class = serializers.PriceRelayProjectSerializer
