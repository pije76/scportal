from django.core.management.base import BaseCommand, CommandError
from wifiagent.relay.request_handler import RequestHandler
from wifiagent.relay.models import Measurement

class Command(BaseCommand):
    help = 'Tries to send all saved measurements'

    def handle(self, *args, **options):
        measurements = Measurement.objects.all()
        request_handler = RequestHandler()
        ok = True

        for measurement in measurements:
            try:
                if request_handler.send_measurement(measurement):
                    measurement.delete()
                else:
                    ok = False
                    break
            except:
                ok = False
                break

        if ok:
            self.stdout.write(self.style.SUCCESS('Saved measurements send...'))
        else:
            self.stdout.write(self.style.ERROR("Can't reach server"))

