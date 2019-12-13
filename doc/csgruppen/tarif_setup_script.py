"""
    Don't run directly... C/P into ./manage.py shell. ONLY ONCE, AND ONLY AFTER NORD POOL FETCH!!!
"""
import datetime

from pytz import timezone

from gridplatform.tariffs.models import EnergyTariff
from gridplatform.tariffs.models import SpotPricePeriod
from gridplatform.global_datasources.models import GlobalDataSource

dk1 = GlobalDataSource.objects.get(
    name="dk1", app_label="nordpool", codename="nordpool_dk1",
    country="DK", unit="currency_dkk*gigawatt^-1*hour^-1")
dk2 = GlobalDataSource.objects.get(
    name="dk2", app_label="nordpool", codename="nordpool_dk2",
    country="DK", unit="currency_dkk*gigawatt^-1*hour^-1")

tariff = EnergyTariff.objects.get(pk=1)

period = SpotPricePeriod.objects.create(
    datasequence=tariff,
    spotprice=dk1,
    coefficient=1,
    unit_for_constant_and_ceiling="currency_dkk*kilowatt^-1*hour^-1",
    constant=0,
    from_timestamp=datetime.datetime.now().replace(tzinfo=timezone('Europe/Copenhagen')),
    subscription_fee=0,
    subscription_period=3
)
