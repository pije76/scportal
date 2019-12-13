import json

from gridplatform.rest import serializers

from energymanager.price_relay_site.models import PriceRelayProject


class PriceRelayProjectSerializer(serializers.DefaultSerializer):
    name = serializers.CharField(source='name_plain')

    class Meta:
        model = PriceRelayProject
        fields = ('name', )
        read_only = True

    def to_native(self, obj):
        native = super(PriceRelayProjectSerializer, self).to_native(obj)
        if obj:
            settings = []
            for setting in obj.calculate_relay_settings():
                settings.append({'timestamp': setting['sample'].from_timestamp.isoformat(), 'relay': setting['relay']})

            native['relay_settings'] = settings

        return native
