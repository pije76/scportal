# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from fractions import Fraction

from django.test import TestCase
from django.test.utils import override_settings
from django.core.exceptions import ValidationError
import pytz
from mock import patch
from django.test import RequestFactory

from gridplatform.customers.models import Customer
from gridplatform.providers.models import Provider
from gridplatform.tariffs.models import EnergyTariff
from gridplatform.tariffs.models import VolumeTariff
from gridplatform.tariffs.models import FixedPricePeriod
from gridplatform.tariffs.models import TariffPeriodManager
from gridplatform.utils.utilitytypes import ENERGY_UTILITY_TYPE_CHOICES
from gridplatform.utils import condense
from gridplatform.utils import sum_or_none
from gridplatform.utils.samples import RangedSample
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.datasequences.models import EnergyPerVolumeDataSequence
from gridplatform.datasequences.models import AccumulationBase
from gridplatform.cost_compensations.models import CostCompensation
from gridplatform.cost_compensations.models import FixedCompensationPeriod
from gridplatform.trackuser import replace_user
from gridplatform.users.models import User
from gridplatform.rest.serializers import HyperlinkedIdentityField
from gridplatform.rest.serializers import HyperlinkedRelatedField
from energymanager.energyuses.models import MAIN_ENERGY_USE_AREAS
from energymanager.energyuses.models import EnergyUse
from gridplatform.datasequences.models.energyconversion import VolumeToEnergyConversionPeriodManager  # noqa
from gridplatform.co2conversions.models import Co2ConversionManager

from .models import ConsumptionGroup
from .models import MainConsumption
from .models import Consumption
from .models import SingleValuePeriod
from .models import ConsumptionUnionBase
from .tasks import net_cost_sum_and_costcompensation_amount_task
from .tasks import total_cost_sum_task
from .tasks import mainconsumptions_weekly_utility_task
from .tasks import mainconsumptions_weekly_cost_sequence
from .tasks import energyuse_weekly_sequence
from .tasks import energyuse_weekly_cost_sequence
from . import viewsets


@override_settings(ENCRYPTION_TESTMODE=True)
class VolumeConsumptionTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(timezone=self.timezone)
        self.consumption = Consumption.objects.create(
            customer=self.customer,
            unit='meter^3')

        self.utility_samples = [
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1, i)),
                self.timezone.localize(datetime.datetime(2014, 1, 1, i + 1)),
                PhysicalQuantity(i * 7, 'meter^3'))
            for i in range(12)]

        self.patched_hourly_accumulated = patch.object(
            AccumulationBase, '_hourly_accumulated',
            return_value=self.utility_samples, autospec=True)

        self.conversion_samples = [
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1, i)),
                self.timezone.localize(datetime.datetime(2014, 1, 1, i + 1)),
                PhysicalQuantity(Fraction(1, 7), 'joule*meter^-3'))
            for i in range(12)]

        self.patched_conversion_sequence = patch.object(
            Consumption, '_hourly_conversion_sequence',
            return_value=self.conversion_samples, autospec=True)

        self.patched_conversion_value_sequence = patch.object(
            VolumeToEnergyConversionPeriodManager, 'value_sequence',
            return_value=self.conversion_samples, autospec=True)

    def test_clean_volumetoenergyconversion_happy(self):
        self.consumption.volumetoenergyconversion = \
            EnergyPerVolumeDataSequence.objects.create(
                customer=self.customer)
        self.consumption.clean()

    def test_hourly_conversion_sequence_no_volumetoenergyconversion(self):
        self.assertEqual(
            list(
                self.consumption._hourly_conversion_sequence(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2)))),
            [])

    def test_hourly_conversion_sequence_volumetoenergyconversion(self):
        self.consumption.volumetoenergyconversion = \
            EnergyPerVolumeDataSequence.objects.create(
                customer=self.customer)

        with self.patched_conversion_value_sequence:
            self.assertEqual(
                list(
                    self.consumption._hourly_conversion_sequence(
                        self.timezone.localize(
                            datetime.datetime(2014, 1, 1)),
                        self.timezone.localize(
                            datetime.datetime(2014, 1, 2)))),
                self.conversion_samples)

    def test_energy_sequence(self):
        energy_samples = [
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1, i)),
                self.timezone.localize(datetime.datetime(2014, 1, 1, i + 1)),
                PhysicalQuantity(i, 'joule'))
            for i in range(12)]

        with self.patched_hourly_accumulated, \
                self.patched_conversion_sequence:
            self.assertEqual(
                list(
                    self.consumption.energy_sequence(
                        self.timezone.localize(datetime.datetime(2014, 1, 1)),
                        self.timezone.localize(
                            datetime.datetime(2014, 1, 1, 12)),
                        condense.HOURS)),
                energy_samples)

    def test_utility_sequence(self):
        with self.patched_hourly_accumulated:
            self.assertEqual(
                list(
                    self.consumption.utility_sequence(
                        self.timezone.localize(datetime.datetime(2014, 1, 1)),
                        self.timezone.localize(
                            datetime.datetime(2014, 1, 1, 12)),
                        condense.HOURS)),
                self.utility_samples)

    def test_energy_sum(self):
        with self.patched_hourly_accumulated, \
                self.patched_conversion_sequence:
            self.assertEqual(
                self.consumption.energy_sum(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2))),
                PhysicalQuantity(12 * 11 / 2, 'joule'))

    def test_utility_sum(self):
        patched_development_sum = patch.object(
            AccumulationBase, 'development_sum',
            return_value=PhysicalQuantity(42, 'meter^3'), autospec=True)

        with patched_development_sum:
            self.assertEqual(
                self.consumption.utility_sum(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2))),
                PhysicalQuantity(42, 'meter^3'))


@override_settings(ENCRYPTION_TESTMODE=True)
class EnergyConsumptionTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.consumption = Consumption.objects.create(
            customer=self.customer,
            unit='joule')

    def test_clean_volumetoenergyconversion_unhappy(self):
        self.consumption.volumetoenergyconversion = \
            EnergyPerVolumeDataSequence.objects.create(
                customer=self.customer)
        with self.assertRaises(ValidationError):
            self.consumption.clean()

    def test_energy_sequence(self):
        energy_samples = [
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1, i)),
                self.timezone.localize(datetime.datetime(2014, 1, 1, i + 1)),
                PhysicalQuantity(i, 'joule'))
            for i in range(12)]

        patched_hourly_accumulated = patch.object(
            AccumulationBase, '_hourly_accumulated',
            return_value=energy_samples, autospec=True)

        with patched_hourly_accumulated:
            self.assertEqual(
                list(
                    self.consumption.energy_sequence(
                        self.timezone.localize(datetime.datetime(2014, 1, 1)),
                        self.timezone.localize(
                            datetime.datetime(2014, 1, 1, 12)),
                        condense.HOURS)),
                energy_samples)

    def test_utility_sequence(self):
        energy_samples = [
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1, i)),
                self.timezone.localize(datetime.datetime(2014, 1, 1, i + 1)),
                PhysicalQuantity(i, 'joule'))
            for i in range(12)]

        patched_hourly_accumulated = patch.object(
            AccumulationBase, '_hourly_accumulated',
            return_value=energy_samples, autospec=True)

        with patched_hourly_accumulated:
            self.assertEqual(
                list(
                    self.consumption.energy_sequence(
                        self.timezone.localize(datetime.datetime(2014, 1, 1)),
                        self.timezone.localize(
                            datetime.datetime(2014, 1, 1, 12)),
                        condense.HOURS)),
                energy_samples)

    def test_energy_sum(self):
        patched_development_sum = patch.object(
            AccumulationBase, 'development_sum',
            return_value=PhysicalQuantity(42, 'joule'), autospec=True)

        with patched_development_sum:
            self.assertEqual(
                self.consumption.energy_sum(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2))),
                PhysicalQuantity(42, 'joule'))

    def test_utility_sum(self):
        patched_development_sum = patch.object(
            AccumulationBase, 'development_sum',
            return_value=PhysicalQuantity(42, 'joule'), autospec=True)

        with patched_development_sum:
            self.assertEqual(
                self.consumption.utility_sum(
                    self.timezone.localize(datetime.datetime(2014, 1, 1)),
                    self.timezone.localize(datetime.datetime(2014, 1, 2))),
                PhysicalQuantity(42, 'joule'))


class TestConsumptionUnion(ConsumptionUnionBase):
    pass


@override_settings(ENCRYPTION_TESTMODE=True)
class ConsumptionUnionBaseTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(timezone=self.timezone)
        self.consumption = Consumption.objects.create(
            customer=self.customer,
            unit='meter^3')

    def test_utility_sum_delegation(self):
        subject = TestConsumptionUnion.objects.create(
            customer=self.customer,
            from_date=datetime.date(2014, 1, 1))
        subject.consumptions = [self.consumption]
        with patch.object(
                Consumption, 'utility_sum', autospec=True,
                return_value=PhysicalQuantity(1, 'meter^3')) as mock:
            subject.utility_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)))

        mock.assert_called_with(
            self.consumption,
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 2)))

    def test_utility_sum_delegation_none_quantity(self):
        subject = TestConsumptionUnion.objects.create(
            customer=self.customer,
            from_date=datetime.date(2014, 1, 1))
        subject.consumptions = [self.consumption]
        with patch.object(
                Consumption, 'utility_sum', autospec=True,
                side_effect=Consumption.utility_sum) as mock:
            subject.utility_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)))

        mock.assert_called_with(
            self.consumption,
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 2)))

    def test_utility_sum_no_consumptions(self):
        subject = TestConsumptionUnion.objects.create(
            customer=self.customer,
            from_date=datetime.date(2014, 1, 1))
        self.assertIsNone(
            subject.utility_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))))

    def test_co2_emission_sequence_no_consumptions(self):
        subject = TestConsumptionUnion.objects.create(
            customer=self.customer,
            from_date=datetime.date(2014, 1, 1))

        patched_co2conversion = patch.object(
            TestConsumptionUnion, 'fiveminute_co2conversion_sequence',
            autospec=True,
            return_value=[])

        with patched_co2conversion:
            self.assertEqual(
                [],
                list(
                    subject.co2_emissions_sequence(
                        self.timezone.localize(datetime.datetime(2014, 1, 1)),
                        self.timezone.localize(datetime.datetime(2014, 1, 2)),
                        condense.HOURS)))

    def test_fiveminute_co2conversion_sequence_abstract(self):
        subject = TestConsumptionUnion.objects.create(
            customer=self.customer,
            from_date=datetime.date(2014, 1, 1))
        with self.assertRaises(NotImplementedError):
            subject.fiveminute_co2conversion_sequence(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)))

    def test_co2_emission_sequence(self):
        subject = TestConsumptionUnion.objects.create(
            customer=self.customer,
            from_date=datetime.date(2014, 1, 1))

        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))

        patched_co2conversion = patch.object(
            TestConsumptionUnion, 'fiveminute_co2conversion_sequence',
            autospec=True,
            return_value=[
                RangedSample(
                    from_timestamp + datetime.timedelta(minutes=5 * i),
                    from_timestamp + datetime.timedelta(minutes=5 * (i + 1)),
                    PhysicalQuantity(i % 7, 'kilogram*kilowatt^-1*hour^-1'))
                for i in range(24 * 60 / 5)
            ])

        patched_utility_consumption = patch.object(
            TestConsumptionUnion, 'utility_sequence', autospec=True,
            return_value=[
                RangedSample(
                    from_timestamp + datetime.timedelta(minutes=5 * i),
                    from_timestamp + datetime.timedelta(minutes=5 * (i + 1)),
                    PhysicalQuantity(i % 11, 'kilowatt*hour'))
                for i in range(24 * 60 / 5)
            ])

        with patched_co2conversion, patched_utility_consumption:
            self.assertEqual(
                [
                    RangedSample(
                        from_timestamp + datetime.timedelta(hours=h),
                        from_timestamp + datetime.timedelta(hours=h + 1),
                        sum_or_none(
                            PhysicalQuantity((i % 7) * (i % 11), 'kilogram')
                            for i in range(h * 60 / 5, (h + 1) * 60 / 5)))
                    for h in range(24)
                ],
                list(
                    subject.co2_emissions_sequence(
                        self.timezone.localize(datetime.datetime(2014, 1, 1)),
                        self.timezone.localize(datetime.datetime(2014, 1, 2)),
                        condense.HOURS)))


@override_settings(ENCRYPTION_TESTMODE=True)
class ConsumptionGroupTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=pytz.timezone('Europe/Copenhagen'))
        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))
        self.consumptiongroup = ConsumptionGroup.objects.create(
            mainconsumption=self.mainconsumption,
            customer=self.customer,
            from_date=datetime.date(2014, 1, 1))
        self.timezone = self.customer.timezone

    def test_energy_sequence_integration(self):
        self.consumptiongroup.consumptions.add(
            Consumption.objects.create(
                unit='milliwatt*hour',
                customer=self.customer))
        self.consumptiongroup.consumptions.add(
            Consumption.objects.create(
                unit='milliwatt*hour',
                customer=self.customer))

        consumptions = list(self.consumptiongroup.consumptions.all())
        self.assertEqual(len(consumptions), 2)

        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        patched_development_sequence = patch.object(
            Consumption,
            'development_sequence',
            return_value=[
                RangedSample(
                    from_timestamp, to_timestamp,
                    PhysicalQuantity(42, 'joule'))],
            autospec=True)

        with patched_development_sequence as mock:
            result = list(
                self.consumptiongroup.energy_sequence(
                    from_timestamp, to_timestamp, condense.DAYS))

        mock.assert_any_call(
            consumptions[0], from_timestamp, to_timestamp, condense.DAYS)
        mock.assert_any_call(
            consumptions[1], from_timestamp, to_timestamp, condense.DAYS)

        self.assertEqual(mock.call_count, 2)

        self.assertEqual(
            [
                RangedSample(
                    from_timestamp, to_timestamp,
                    PhysicalQuantity(84, 'joule'))],
            result)

    def test_save_no_mainconsumption_change(self):
        mainconsumption2 = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))
        self.consumptiongroup.mainconsumption = mainconsumption2

        with self.assertRaises(AssertionError):
            self.consumptiongroup.save()

    def test_energy_sum_integration(self):
        self.assertIsNone(
            self.consumptiongroup.energy_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))))

    def test_net_cost_sum_no_tariff_and_no_consumptions(self):
        self.assertIsNone(self.consumptiongroup.net_cost_sum(
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 2))))

    def test_net_cost_sum_energy_tariff(self):
        self.consumptiongroup.mainconsumption = \
            MainConsumption.objects.create(
                customer=self.customer,
                utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
                from_date=datetime.date(2014, 1, 1))
        self.consumptiongroup.mainconsumption.tariff = \
            EnergyTariff.objects.create(customer=self.customer)
        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=self.consumptiongroup.mainconsumption.tariff,
            subscription_fee=100,
            subscription_period=FixedPricePeriod.SUBSCRIPTION_PERIODS.monthly)

        consumption = Consumption.objects.create(
            unit='milliwatt*hour',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            datasequence=consumption,
            value=42,
            unit='kilowatt*hour')
        self.consumptiongroup.consumptions.add(consumption)

        self.assertEqual(
            self.consumptiongroup.net_cost_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))),
            PhysicalQuantity(42 * 10, 'currency_dkk'))

    def test_net_cost_sum_volume_tariff(self):
        self.consumptiongroup.mainconsumption = \
            MainConsumption.objects.create(
                customer=self.customer,
                utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
                from_date=datetime.date(2014, 1, 1))
        self.consumptiongroup.mainconsumption.tariff = \
            VolumeTariff.objects.create(customer=self.customer)
        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            value=10,
            unit='currency_dkk*meter^-3',
            datasequence=self.consumptiongroup.mainconsumption.tariff,
            subscription_fee=100,
            subscription_period=FixedPricePeriod.SUBSCRIPTION_PERIODS.monthly)

        utility_consumption = Consumption.objects.create(
            unit='meter^3',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            datasequence=utility_consumption,
            value=42,
            unit='meter^3')

        self.consumptiongroup.consumptions.add(utility_consumption)

        energy_pr_volume = EnergyPerVolumeDataSequence.objects.create(
            customer=self.customer)

        utility_consumption.volumetoenergyconversion = energy_pr_volume
        utility_consumption.save()

        self.assertEqual(
            self.consumptiongroup.net_cost_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))),
            PhysicalQuantity(42 * 10, 'currency_dkk'))

    def test_costcompensation_amount_sum_no_costcompensation_nor_consumptions(self):  # noqa
        self.assertIsNone(self.consumptiongroup.costcompensation_amount_sum(
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 2))))

    def test_costcompensation_amount_sum(self):
        self.consumptiongroup.cost_compensation = \
            CostCompensation.objects.create(customer=self.customer)
        FixedCompensationPeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=self.consumptiongroup.cost_compensation)

        consumption = Consumption.objects.create(
            unit='milliwatt*hour',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            datasequence=consumption,
            value=42,
            unit='kilowatt*hour')
        self.consumptiongroup.consumptions.add(consumption)

        self.assertEqual(
            self.consumptiongroup.costcompensation_amount_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))),
            PhysicalQuantity(42 * 10, 'currency_dkk'))

    def test_mainconsumption_costcompensation_amount_sum(self):
        self.mainconsumption.cost_compensation = \
            CostCompensation.objects.create(customer=self.customer)
        FixedCompensationPeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=self.mainconsumption.cost_compensation)

        consumption = Consumption.objects.create(
            unit='milliwatt*hour',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            datasequence=consumption,
            value=42,
            unit='kilowatt*hour')
        self.consumptiongroup.consumptions.add(consumption)

        self.assertEqual(
            self.consumptiongroup.costcompensation_amount_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))),
            PhysicalQuantity(42 * 10, 'currency_dkk'))

    def test_variable_cost_sum_integration(self):
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))
        self.assertIsNone(
            self.consumptiongroup.variable_cost_sum(
                from_timestamp, to_timestamp))

    def test_fiveminute_co2conversion_sequence_integration(self):
        patched_co2conversion = patch.object(
            MainConsumption, 'fiveminute_co2conversion_sequence',
            autospec=True,
            return_value=[])
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))
        with patched_co2conversion as mock:
            self.consumptiongroup.fiveminute_co2conversion_sequence(
                from_timestamp, to_timestamp)

        mock.assert_called_with(
            self.mainconsumption, from_timestamp, to_timestamp)


@override_settings(
    ENCRYPTION_TESTMODE=True,
    CELERY_ALWAYS_EAGER=True)
class NetCostSumAndCostCompensationAmountTaskTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))
        self.consumptiongroup = ConsumptionGroup.objects.create(
            mainconsumption=self.mainconsumption,
            customer=self.customer,
            from_date=datetime.date(2014, 1, 1))
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.user = User.objects.create_user(
            'test user', 'secret', User.ADMIN, provider=self.provider)

    def test_no_consumptiongroups(self):
        with replace_user(self.user):
            eager = net_cost_sum_and_costcompensation_amount_task.delay(
                [],
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)))

        self.assertEqual({}, eager.result)

    def test_unknown_net_cost_and_unknown_costcompensation_amount(self):
        with replace_user(self.user):
            eager = net_cost_sum_and_costcompensation_amount_task.delay(
                [self.consumptiongroup.id],
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)))

        self.assertEqual(
            {
                self.consumptiongroup.id: {
                    'net_cost_sum': None,
                    'costcompensation_amount_sum': None,
                },
            },
            eager.result)

    def test_unknown_net_cost(self):
        costcompensation_amount_sum = PhysicalQuantity(17, 'currency_dkk')

        with replace_user(self.user), patch.object(
                ConsumptionGroup, 'costcompensation_amount_sum',
                return_value=costcompensation_amount_sum):

            eager = net_cost_sum_and_costcompensation_amount_task.delay(
                [self.consumptiongroup.id],
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)))

        self.assertEqual(
            {
                self.consumptiongroup.id: {
                    'net_cost_sum': None,
                    'costcompensation_amount_sum': costcompensation_amount_sum,
                },
            },
            eager.result)

    def test_unknown_costcompensation_amount(self):
        net_cost_sum = PhysicalQuantity(42, 'currency_dkk')

        with replace_user(self.user), patch.object(
                ConsumptionGroup, 'net_cost_sum', return_value=net_cost_sum):

            eager = net_cost_sum_and_costcompensation_amount_task.delay(
                [self.consumptiongroup.id],
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2)))

        self.assertEqual(
            {
                self.consumptiongroup.id: {
                    'net_cost_sum': net_cost_sum,
                    'costcompensation_amount_sum': None,
                },
            },
            eager.result)


@override_settings(ENCRYPTION_TESTMODE=True)
class MainConsumptionTest(TestCase):
    def setUp(self):
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create(
            timezone=self.timezone,
            currency_unit='currency_dkk')

    def test_save_no_utility_type_change(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            from_date=datetime.date(2014, 1, 1))
        mainconsumption.utility_type = ENERGY_UTILITY_TYPE_CHOICES.electricity
        with self.assertRaises(AssertionError):
            mainconsumption.save()

    def test_clean_happy(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            cost_compensation=CostCompensation.objects.create(
                customer=self.customer),
            tariff=VolumeTariff.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        mainconsumption.clean()

    def test_clean_no_tariff_change_once_set(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            tariff=VolumeTariff.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        mainconsumption.tariff = VolumeTariff.objects.create(
            customer=self.customer)
        with self.assertRaises(ValidationError):
            mainconsumption.clean()

    def test_clean_no_clearing_tariff_once_set(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            tariff=VolumeTariff.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        mainconsumption.tariff = None
        with self.assertRaises(ValidationError):
            mainconsumption.clean()

    def test_clean_no_costcompensation_change_once_set(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            cost_compensation=CostCompensation.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        mainconsumption.cost_compensation = CostCompensation.objects.create(
            customer=self.customer)
        with self.assertRaises(ValidationError):
            mainconsumption.clean()

    def test_clean_no_clearing_costcompensation_once_set(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            cost_compensation=CostCompensation.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        mainconsumption.cost_compensation = None

        with self.assertRaises(ValidationError):
            mainconsumption.clean()

    def test_energy_sum_integration(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            from_date=datetime.date(2014, 1, 1))

        self.assertIsNone(
            mainconsumption.energy_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))))

    def test_net_cost_sum_no_tariff_and_no_consumptions(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))

        self.assertIsNone(mainconsumption.net_cost_sum(
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 2))))

    def test_energy_sequence_integration(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))

        mainconsumption.consumptions.add(
            Consumption.objects.create(
                unit='milliwatt*hour',
                customer=self.customer))
        mainconsumption.consumptions.add(
            Consumption.objects.create(
                unit='milliwatt*hour',
                customer=self.customer))

        consumptions = list(mainconsumption.consumptions.all())
        self.assertEqual(len(consumptions), 3)  # the above + historical

        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        patched_development_sequence = patch.object(
            Consumption,
            'development_sequence',
            return_value=[
                RangedSample(
                    from_timestamp, to_timestamp,
                    PhysicalQuantity(42, 'joule'))],
            autospec=True)

        with patched_development_sequence as mock:
            result = list(
                mainconsumption.energy_sequence(
                    from_timestamp, to_timestamp, condense.DAYS))

        mock.assert_any_call(
            consumptions[0], from_timestamp, to_timestamp, condense.DAYS)
        mock.assert_any_call(
            consumptions[1], from_timestamp, to_timestamp, condense.DAYS)
        mock.assert_any_call(
            consumptions[2], from_timestamp, to_timestamp, condense.DAYS)

        self.assertEqual(mock.call_count, 3)

        self.assertEqual(
            [
                RangedSample(
                    from_timestamp, to_timestamp,
                    PhysicalQuantity(126, 'joule'))],
            result)

    def test_net_cost_sum_energy_tariff(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            tariff=EnergyTariff.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))

        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=mainconsumption.tariff,
            subscription_fee=100,
            subscription_period=FixedPricePeriod.SUBSCRIPTION_PERIODS.monthly)

        consumption = Consumption.objects.create(
            unit='milliwatt*hour',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            datasequence=consumption,
            value=42,
            unit='kilowatt*hour')
        mainconsumption.consumptions.add(consumption)

        self.assertEqual(
            mainconsumption.net_cost_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))),
            PhysicalQuantity(42 * 10, 'currency_dkk'))

    def test_net_cost_sum_volume_tariff(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            tariff=VolumeTariff.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))

        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            value=10,
            unit='currency_dkk*meter^-3',
            datasequence=mainconsumption.tariff,
            subscription_fee=100,
            subscription_period=FixedPricePeriod.SUBSCRIPTION_PERIODS.monthly)

        utility = Consumption.objects.create(
            unit='meter^3',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(2014, 1, 2)),
            datasequence=utility,
            value=42,
            unit='meter^3')

        mainconsumption.consumptions.add(utility)

        energy_pr_volume = EnergyPerVolumeDataSequence.objects.create(
            customer=self.customer)

        utility.volumetoenergyconversion = energy_pr_volume
        utility.save()

        self.assertEqual(
            mainconsumption.net_cost_sum(
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 2))),
            PhysicalQuantity(42 * 10, 'currency_dkk'))

    def test_costcompensation_amount_sum_no_costcompensation_nor_consumptions(self):  # noqa
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            from_date=datetime.date(2014, 1, 1))

        self.assertIsNone(mainconsumption.costcompensation_amount_sum(
            self.timezone.localize(datetime.datetime(2014, 1, 1)),
            self.timezone.localize(datetime.datetime(2014, 1, 2))))

    def test_costcompensation_amount_sum_both(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            cost_compensation=CostCompensation.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        FixedCompensationPeriod.objects.create(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=mainconsumption.cost_compensation)

        consumption = Consumption.objects.create(
            unit='milliwatt*hour',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            datasequence=consumption,
            value=42,
            unit='kilowatt*hour')
        mainconsumption.consumptions.add(consumption)

        consumptiongroup = ConsumptionGroup.objects.create(
            mainconsumption=mainconsumption,
            customer=self.customer,
            cost_compensation=CostCompensation.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))

        FixedCompensationPeriod.objects.create(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            value=7,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=consumptiongroup.cost_compensation)

        consumption_part = Consumption.objects.create(
            unit='milliwatt*hour',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            datasequence=consumption_part,
            value=17,
            unit='kilowatt*hour')
        consumptiongroup.consumptions.add(consumption_part)

        self.assertEqual(
            mainconsumption.costcompensation_amount_sum(
                from_timestamp, to_timestamp),
            PhysicalQuantity((42 - 17) * 10 + 17 * 7, 'currency_dkk'))

    def test_costcompensation_amount_sum_tainted(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        consumptiongroup = ConsumptionGroup.objects.create(
            mainconsumption=mainconsumption,
            customer=self.customer,
            cost_compensation=CostCompensation.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))

        FixedCompensationPeriod.objects.create(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            value=7,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=consumptiongroup.cost_compensation)

        consumption_part = Consumption.objects.create(
            unit='milliwatt*hour',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            datasequence=consumption_part,
            value=17,
            unit='kilowatt*hour')
        consumptiongroup.consumptions.add(consumption_part)

        self.assertEqual(
            mainconsumption.costcompensation_amount_sum(
                from_timestamp, to_timestamp),
            PhysicalQuantity(17 * 7, 'currency_dkk'))

    def test_costcompensation_amount_sum_untainted(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            cost_compensation=CostCompensation.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        FixedCompensationPeriod.objects.create(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=mainconsumption.cost_compensation)

        consumption = Consumption.objects.create(
            unit='milliwatt*hour',
            customer=self.customer)
        SingleValuePeriod.objects.create(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            datasequence=consumption,
            value=42,
            unit='kilowatt*hour')
        mainconsumption.consumptions.add(consumption)

        self.assertEqual(
            mainconsumption.costcompensation_amount_sum(
                from_timestamp, to_timestamp),
            PhysicalQuantity(42 * 10, 'currency_dkk'))

    def test_variable_cost_sum_integration(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            cost_compensation=CostCompensation.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))
        self.assertIsNone(
            mainconsumption.variable_cost_sum(from_timestamp, to_timestamp))

    def test_fixed_cost_sum_delegation(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            tariff=VolumeTariff.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        patched_subscription_cost = patch.object(
            TariffPeriodManager, 'subscription_cost_sum', autospec=True,
            return_value=PhysicalQuantity(11, 'currency_dkk'))

        mainconsumption.fixed_cost_sum(from_timestamp, to_timestamp)

        with patched_subscription_cost:
            self.assertEqual(
                PhysicalQuantity(11, 'currency_dkk'),
                mainconsumption.fixed_cost_sum(from_timestamp, to_timestamp))

    def test_total_cost_sum(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            tariff=VolumeTariff.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        patched_variable_cost = patch.object(
            MainConsumption, 'variable_cost_sum', autospec=True,
            return_value=PhysicalQuantity(7, 'currency_dkk'))
        patched_fixed_cost = patch.object(
            MainConsumption, 'fixed_cost_sum', autospec=True,
            return_value=PhysicalQuantity(11, 'currency_dkk'))

        with patched_variable_cost, patched_fixed_cost:
            self.assertEqual(
                PhysicalQuantity(7 + 11, 'currency_dkk'),
                mainconsumption.total_cost_sum(from_timestamp, to_timestamp))

    def test_total_cost_sum_no_variable_cost(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            tariff=VolumeTariff.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        patched_fixed_cost = patch.object(
            MainConsumption, 'fixed_cost_sum', autospec=True,
            return_value=PhysicalQuantity(11, 'currency_dkk'))

        with patched_fixed_cost:
            self.assertEqual(
                PhysicalQuantity(11, 'currency_dkk'),
                mainconsumption.total_cost_sum(from_timestamp, to_timestamp))

    def test_total_cost_sum_no_fixed_cost(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            tariff=VolumeTariff.objects.create(
                customer=self.customer),
            from_date=datetime.date(2014, 1, 1))
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        patched_variable_cost = patch.object(
            MainConsumption, 'variable_cost_sum', autospec=True,
            return_value=PhysicalQuantity(7, 'currency_dkk'))

        with patched_variable_cost:
            self.assertEqual(
                PhysicalQuantity(7, 'currency_dkk'),
                mainconsumption.total_cost_sum(from_timestamp, to_timestamp))

    def test_clean_good_tariff(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            tariff=EnergyTariff.objects.create(customer=self.customer),
            from_date=datetime.date(2014, 1, 1))

        mainconsumption.clean()

    def test_clean_bad_unit_tariff(self):
        mainconsumption = MainConsumption(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            tariff=VolumeTariff.objects.create(customer=self.customer))

        with self.assertRaises(ValidationError):
            mainconsumption.clean()

    def test_fiveminute_co2conversion_sequence_integration(self):
        mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))

        patched_co2conversion = patch.object(
            Co2ConversionManager, 'value_sequence',
            autospec=True,
            return_value=[])
        from_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(datetime.datetime(2014, 1, 2))

        with patched_co2conversion as mock:
            mainconsumption.fiveminute_co2conversion_sequence(
                from_timestamp, to_timestamp)

        # First argument of value_sequence() is a new instance of some subclass
        # of Co2ConversionManager upon every access.  We are happy if the call
        # just got there.  Otherwise mock.assert_called_with() should have been
        # used.
        args = mock.call_args[0][1:]
        self.assertEqual(args, (from_timestamp, to_timestamp))


@override_settings(ENCRYPTION_TESTMODE=True)
class VariableCostSumTest(TestCase):
    def setUp(self):
        self.consumptionunion = TestConsumptionUnion()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))
        self.to_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 2))

    def test_no_costcompensation(self):
        patched_net_cost_sum = patch.object(
            TestConsumptionUnion, 'net_cost_sum', autospec=True,
            return_value=PhysicalQuantity(42, 'currency_dkk'))
        patched_costcompensation_amount_sum = patch.object(
            TestConsumptionUnion, 'costcompensation_amount_sum',
            autospec=True, return_value=None)

        with patched_net_cost_sum, patched_costcompensation_amount_sum:
            self.assertEqual(
                PhysicalQuantity(42, 'currency_dkk'),
                self.consumptionunion.variable_cost_sum(
                    self.from_timestamp, self.to_timestamp))

    def test_no_net_cost(self):
        patched_net_cost_sum = patch.object(
            TestConsumptionUnion, 'net_cost_sum', autospec=True,
            return_value=None)
        patched_costcompensation_amount_sum = patch.object(
            TestConsumptionUnion, 'costcompensation_amount_sum',
            autospec=True, return_value=PhysicalQuantity(42, 'currency_dkk'))

        with patched_net_cost_sum, patched_costcompensation_amount_sum:
            self.assertIsNone(
                self.consumptionunion.variable_cost_sum(
                    self.from_timestamp, self.to_timestamp))

    def test_net_cost_and_costcompensation(self):
        patched_net_cost_sum = patch.object(
            TestConsumptionUnion, 'net_cost_sum', autospec=True,
            return_value=PhysicalQuantity(42, 'currency_dkk'))
        patched_costcompensation_amount_sum = patch.object(
            TestConsumptionUnion, 'costcompensation_amount_sum',
            autospec=True,
            return_value=PhysicalQuantity(17, 'currency_dkk'))

        with patched_net_cost_sum, patched_costcompensation_amount_sum:
            self.assertEqual(
                PhysicalQuantity(42 - 17, 'currency_dkk'),
                self.consumptionunion.variable_cost_sum(
                    self.from_timestamp, self.to_timestamp))


@override_settings(ENCRYPTION_TESTMODE=True)
class VariableCostSequenceTest(TestCase):
    def setUp(self):
        self.consumptionunion = TestConsumptionUnion()
        self.consumptionunion.customer = Customer(
            currency_unit='currency_dkk',
            timezone=pytz.timezone('Europe/Copenhagen'))
        self.timezone = self.consumptionunion.customer.timezone
        self.from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))
        self.to_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1, 12))

        self.net_cost_samples = [
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1, i)),
                self.timezone.localize(datetime.datetime(2014, 1, 1, i + 1)),
                PhysicalQuantity(i * 7, 'currency_dkk'))
            for i in range(12)]

        self.costcompensation_amount_samples = [
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1, i)),
                self.timezone.localize(datetime.datetime(2014, 1, 1, i + 1)),
                PhysicalQuantity(i * 3, 'currency_dkk'))
            for i in range(12)]

        self.variable_cost_samples = [
            RangedSample(
                self.timezone.localize(datetime.datetime(2014, 1, 1, i)),
                self.timezone.localize(datetime.datetime(2014, 1, 1, i + 1)),
                PhysicalQuantity(i * (7 - 3), 'currency_dkk'))
            for i in range(12)]

    def test_no_costcompensation_and_no_net_cost(self):
        patched_net_cost_sequence = patch.object(
            TestConsumptionUnion, 'net_cost_sequence', autospec=True,
            return_value=[])
        patched_costcompensation_amount_sequence = patch.object(
            TestConsumptionUnion, 'costcompensation_amount_sequence',
            autospec=True, return_value=[])

        with patched_net_cost_sequence, \
                patched_costcompensation_amount_sequence:
            self.assertListEqual(
                [],
                list(
                    self.consumptionunion.variable_cost_sequence(
                        self.from_timestamp, self.to_timestamp,
                        condense.HOURS)))

    def test_no_costcompensation(self):
        patched_net_cost_sequence = patch.object(
            TestConsumptionUnion, 'net_cost_sequence', autospec=True,
            return_value=self.net_cost_samples)
        patched_costcompensation_amount_sequence = patch.object(
            TestConsumptionUnion, 'costcompensation_amount_sequence',
            autospec=True, return_value=[])

        with patched_net_cost_sequence, \
                patched_costcompensation_amount_sequence:
            self.assertListEqual(
                self.net_cost_samples,
                list(
                    self.consumptionunion.variable_cost_sequence(
                        self.from_timestamp, self.to_timestamp,
                        condense.HOURS)))

    def test_no_net_cost(self):
        patched_net_cost_sequence = patch.object(
            TestConsumptionUnion, 'net_cost_sequence', autospec=True,
            return_value=[])
        patched_costcompensation_amount_sequence = patch.object(
            TestConsumptionUnion, 'costcompensation_amount_sequence',
            autospec=True, return_value=self.costcompensation_amount_samples)

        with patched_net_cost_sequence, \
                patched_costcompensation_amount_sequence:
            self.assertListEqual(
                [
                    RangedSample(
                        sample.from_timestamp, sample.to_timestamp,
                        -sample.physical_quantity)
                    for sample in self.costcompensation_amount_samples],
                list(
                    self.consumptionunion.variable_cost_sequence(
                        self.from_timestamp, self.to_timestamp,
                        condense.HOURS)))

    def test_net_cost_and_costcompensation(self):
        patched_net_cost_sequence = patch.object(
            TestConsumptionUnion, 'net_cost_sequence', autospec=True,
            return_value=self.net_cost_samples)
        patched_costcompensation_amount_sequence = patch.object(
            TestConsumptionUnion, 'costcompensation_amount_sequence',
            autospec=True, return_value=self.costcompensation_amount_samples)

        with patched_net_cost_sequence, \
                patched_costcompensation_amount_sequence:
            self.assertListEqual(
                self.variable_cost_samples,
                list(
                    self.consumptionunion.variable_cost_sequence(
                        self.from_timestamp, self.to_timestamp,
                        condense.HOURS)))


@override_settings(
    ENCRYPTION_TESTMODE=True,
    CELERY_ALWAYS_EAGER=True)
class TotalCostSumTaskTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.customer = Customer.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.user = User.objects.create_user(
            'test user', 'secret', User.ADMIN, provider=self.provider)

    def test_empty(self):
        from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 2))

        with replace_user(self.user):
            eager = total_cost_sum_task.delay([], from_timestamp, to_timestamp)

        self.assertEqual({}, eager.result)

    def test_some(self):
        electricity = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))
        gas = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.gas,
            from_date=datetime.date(2014, 1, 1))

        from_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 1))
        to_timestamp = self.timezone.localize(
            datetime.datetime(2014, 1, 2))

        total_cost_quantity = PhysicalQuantity(42, 'currency_dkk')
        patched_total_cost_sum = patch.object(
            MainConsumption, 'total_cost_sum',
            return_value=total_cost_quantity)

        with replace_user(self.user), patched_total_cost_sum:
            eager = total_cost_sum_task.delay(
                [electricity.id, gas.id], from_timestamp, to_timestamp)

        self.assertEqual(
            {
                electricity.id: total_cost_quantity,
                gas.id: total_cost_quantity},
            eager.result)


def get_url_mock(self, obj, view_name, request, format):
    """Mock used to render HyperlinkedModelSerializer"""
    return "/%s" % view_name


@override_settings(
    ENCRYPTION_TESTMODE=True)
class MainConsumptionViewSetTest(TestCase):

    def setUp(self):
        self.provider = Provider.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.customer = Customer.objects.create(timezone=self.timezone)

        self.factory = RequestFactory()

        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            name_plain='Dat main meter',
            from_date=datetime.date(2014, 1, 1))

        consumption = Consumption.objects.create(
            unit='kilowatt*hour', customer=self.customer)
        self.mainconsumption.consumptions.add(consumption)

        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 10, 1)),
            datasequence=consumption,
            value=1024,
            unit='kilowatt*hour')

    def test_get(self):
        request = self.factory.get('/', content_type='application/json')
        request.user = User(name_plain='test user')
        view = viewsets.MainConsumption.as_view(actions={'get': 'list'})
        with patch.object(HyperlinkedIdentityField, 'get_url', get_url_mock), \
                patch.object(HyperlinkedRelatedField, 'get_url', get_url_mock):
            response = view(request, pk=self.mainconsumption.id)
            self.assertContains(response, 'Dat main meter')

    def test_get_hourly(self):
        request = self.factory.get(
            '/?date=2014-08-19', content_type='application/json')
        request.user = User(name_plain='test user')

        view = viewsets.MainConsumption.as_view(actions={'get': 'hourly'})
        with patch.object(HyperlinkedIdentityField, 'get_url', get_url_mock), \
                patch.object(HyperlinkedRelatedField, 'get_url', get_url_mock):
            response = view(request, pk=self.mainconsumption.id)
            self.assertContains(response, '2014-08-19T00:00:00+02:00')


@override_settings(
    ENCRYPTION_TESTMODE=True)
class ConsumptionGroupViewSetTest(TestCase):

    def setUp(self):
        self.provider = Provider.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.customer = Customer.objects.create(timezone=self.timezone)

        self.factory = RequestFactory()

        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            name_plain='Dat main meter',
            from_date=datetime.date(2014, 1, 1))

        self.consumptiongroup = ConsumptionGroup.objects.create(
            mainconsumption=self.mainconsumption,
            customer=self.customer,
            name_plain='Der Verbrauch Gruppe',
            from_date=datetime.date(2014, 1, 1))

        consumption = Consumption.objects.create(
            unit='kilowatt*hour', customer=self.customer)
        self.consumptiongroup.consumptions.add(consumption)

        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 10, 1)),
            datasequence=consumption,
            value=1024,
            unit='kilowatt*hour')

    def test_get(self):
        request = self.factory.get('/', content_type='application/json')
        request.user = User(name_plain='test user')
        view = viewsets.ConsumptionGroup.as_view(actions={'get': 'list'})
        with patch.object(HyperlinkedIdentityField, 'get_url', get_url_mock), \
                patch.object(HyperlinkedRelatedField, 'get_url', get_url_mock):
            response = view(request, pk=self.consumptiongroup.id)
            self.assertContains(response, 'Der Verbrauch Gruppe')

    def test_get_hourly(self):
        request = self.factory.get(
            '/?date=2014-08-19', content_type='application/json')
        request.user = User(name_plain='test user')

        view = viewsets.ConsumptionGroup.as_view(actions={'get': 'hourly'})
        with patch.object(HyperlinkedIdentityField, 'get_url', get_url_mock), \
                patch.object(HyperlinkedRelatedField, 'get_url', get_url_mock):
            response = view(request, pk=self.consumptiongroup.id)
            self.assertContains(response, '2014-08-19T00:00:00+02:00')


@override_settings(
    ENCRYPTION_TESTMODE=True,
    CELERY_ALWAYS_EAGER=True)
class MainConsumptionsWeeklyCostSequenceTaskTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.customer = Customer.objects.create(timezone=self.timezone)
        self.tariff = EnergyTariff.objects.create(
            customer=self.customer, name_plain='Tariff test')
        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            tariff=self.tariff,
            from_date=datetime.date(2014, 1, 1))
        self.user = User.objects.create_user(
            'test user', 'secret', User.ADMIN, provider=self.provider)
        self.consumption = Consumption.objects.create(
            unit='kilowatt*hour', customer=self.customer)
        self.mainconsumption.consumptions.add(self.consumption)

    def test_no_data(self):
        with replace_user(self.user):
            sequence = mainconsumptions_weekly_cost_sequence.delay(
                [self.mainconsumption.id],
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 7)))

        self.assertEqual(list(sequence.result['week_selected']), [])
        self.assertEqual(list(sequence.result['week_before']), [])

    def test_with_data(self):
        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(
                2014, 10, 1)),
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=self.tariff,
            subscription_fee=100,
            subscription_period=FixedPricePeriod.SUBSCRIPTION_PERIODS.monthly)

        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 10, 1)),
            datasequence=self.consumption,
            value=1024,
            unit='kilowatt*hour')

        with replace_user(self.user):
            sequence = mainconsumptions_weekly_cost_sequence.delay(
                [self.mainconsumption.id],
                self.timezone.localize(datetime.datetime(2014, 1, 26)),
                self.timezone.localize(datetime.datetime(2014, 2, 2)))

        week_selected = list(sequence.result['week_selected'])
        week_before = list(sequence.result['week_before'])

        self.assertEqual(
            min(week_selected).from_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 26)))
        self.assertEqual(
            max(week_selected).to_timestamp, self.timezone.localize(
                datetime.datetime(2014, 2, 2)))

        self.assertEqual(
            min(week_before).from_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 19)))
        self.assertEqual(
            max(week_before).to_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 26)))


@override_settings(
    ENCRYPTION_TESTMODE=True,
    CELERY_ALWAYS_EAGER=True)
class EnergyUseWeeklySequenceTaskTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.customer = Customer.objects.create(timezone=self.timezone)
        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1)
        )
        self.energyuse = EnergyUse.objects.create(
            mainconsumption=self.mainconsumption,
            customer=self.customer,
            main_energy_use_area=MAIN_ENERGY_USE_AREAS.lighting,
            from_date=datetime.date(2000, 1, 1))

        self.user = User.objects.create_user(
            'test user', 'secret', User.ADMIN, provider=self.provider)
        self.consumption = Consumption.objects.create(
            unit='kilowatt*hour', customer=self.customer)
        self.energyuse.consumptions.add(self.consumption)

    def test_no_data(self):
        with replace_user(self.user):
            sequence = energyuse_weekly_sequence.delay(
                self.energyuse.id,
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 7)))

        self.assertEqual(list(sequence.result['week_selected']), [])
        self.assertEqual(list(sequence.result['week_before']), [])
        self.assertEqual(
            sequence.result['utility_type'],
            self.energyuse.mainconsumption.utility_type)

    def test_with_data(self):
        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 10, 1)),
            datasequence=self.consumption,
            value=1024,
            unit='kilowatt*hour')

        with replace_user(self.user):
            sequence = energyuse_weekly_sequence.delay(
                self.energyuse.id,
                self.timezone.localize(datetime.datetime(2014, 1, 26)),
                self.timezone.localize(datetime.datetime(2014, 2, 2)))

        week_selected = list(sequence.result['week_selected'])
        week_before = list(sequence.result['week_before'])

        self.assertEqual(
            min(week_selected).from_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 26)))
        self.assertEqual(
            max(week_selected).to_timestamp, self.timezone.localize(
                datetime.datetime(2014, 2, 2)))

        self.assertEqual(
            min(week_before).from_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 19)))
        self.assertEqual(
            max(week_before).to_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 26)))


@override_settings(
    ENCRYPTION_TESTMODE=True,
    CELERY_ALWAYS_EAGER=True)
class EnergyUseWeeklyCostSequenceTaskTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.customer = Customer.objects.create(timezone=self.timezone)
        self.tariff = EnergyTariff.objects.create(
            customer=self.customer, name_plain='Tariff test')
        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            tariff=self.tariff,
            from_date=datetime.date(2014, 1, 1))
        self.energyuse = EnergyUse.objects.create(
            mainconsumption=self.mainconsumption,
            customer=self.customer,
            main_energy_use_area=MAIN_ENERGY_USE_AREAS.lighting,
            from_date=datetime.date(2000, 1, 1))

        self.user = User.objects.create_user(
            'test user', 'secret', User.ADMIN, provider=self.provider)
        self.consumption = Consumption.objects.create(
            unit='kilowatt*hour', customer=self.customer)
        self.energyuse.consumptions.add(self.consumption)

    def test_no_data(self):
        with replace_user(self.user):
            sequence = energyuse_weekly_cost_sequence.delay(
                self.energyuse.id,
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 7)))

        self.assertEqual(list(sequence.result['week_selected']), [])
        self.assertEqual(list(sequence.result['week_before']), [])
        self.assertEqual(sequence.result['energyuse_id'], self.energyuse.id)

    def test_withdata_data(self):
        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 10, 1)),
            datasequence=self.consumption,
            value=1024,
            unit='kilowatt*hour')

        FixedPricePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(datetime.datetime(
                2014, 10, 1)),
            value=10,
            unit='currency_dkk*kilowatt^-1*hour^-1',
            datasequence=self.tariff,
            subscription_fee=100,
            subscription_period=FixedPricePeriod.SUBSCRIPTION_PERIODS.monthly)

        with replace_user(self.user):
            sequence = energyuse_weekly_cost_sequence.delay(
                self.energyuse.id,
                self.timezone.localize(datetime.datetime(2014, 1, 26)),
                self.timezone.localize(datetime.datetime(2014, 2, 2)))

        week_selected = list(sequence.result['week_selected'])
        week_before = list(sequence.result['week_before'])

        self.assertEqual(
            min(week_selected).from_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 26)))
        self.assertEqual(
            max(week_selected).to_timestamp, self.timezone.localize(
                datetime.datetime(2014, 2, 2)))

        self.assertEqual(
            min(week_before).from_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 19)))
        self.assertEqual(
            max(week_before).to_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 26)))


@override_settings(
    ENCRYPTION_TESTMODE=True,
    CELERY_ALWAYS_EAGER=True)
class MainconsumptionsWeeklyUtilityTaskTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create()
        self.timezone = pytz.timezone('Europe/Copenhagen')
        self.customer = Customer.objects.create(timezone=self.timezone)
        self.mainconsumption = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))
        self.mainconsumption2 = MainConsumption.objects.create(
            customer=self.customer,
            utility_type=ENERGY_UTILITY_TYPE_CHOICES.electricity,
            from_date=datetime.date(2014, 1, 1))
        self.user = User.objects.create_user(
            'test user', 'secret', User.ADMIN, provider=self.provider)
        self.consumption = Consumption.objects.create(
            unit='kilowatt*hour', customer=self.customer)
        self.mainconsumption.consumptions.add(self.consumption)

        self.consumption2 = Consumption.objects.create(
            unit='kilowatt*hour', customer=self.customer)
        self.mainconsumption2.consumptions.add(self.consumption2)

    def test_no_data(self):
        with replace_user(self.user):
            sequence = mainconsumptions_weekly_utility_task.delay(
                [self.mainconsumption.id, self.mainconsumption2.id],
                self.timezone.localize(datetime.datetime(2014, 1, 1)),
                self.timezone.localize(datetime.datetime(2014, 1, 7)),
                ENERGY_UTILITY_TYPE_CHOICES.electricity)

        self.assertEqual(list(
            sequence.result['week_selected']), [])
        self.assertEqual(list(
            sequence.result['week_before']), [])

    def test_with_data(self):
        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 10, 1)),
            datasequence=self.consumption,
            value=1024,
            unit='kilowatt*hour')

        SingleValuePeriod.objects.create(
            from_timestamp=self.timezone.localize(
                datetime.datetime(2014, 1, 1)),
            to_timestamp=self.timezone.localize(
                datetime.datetime(2014, 10, 1)),
            datasequence=self.consumption2,
            value=1024,
            unit='kilowatt*hour')

        with replace_user(self.user):
            sequence = mainconsumptions_weekly_utility_task.delay(
                [self.mainconsumption.id, self.mainconsumption2.id],
                self.timezone.localize(datetime.datetime(2014, 1, 26)),
                self.timezone.localize(datetime.datetime(2014, 2, 2)),
                ENERGY_UTILITY_TYPE_CHOICES.electricity)

        week_selected = sequence.result['week_selected']
        week_before = sequence.result['week_before']

        self.assertEqual(
            min(week_selected).from_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 26)))
        self.assertEqual(
            max(week_selected).to_timestamp, self.timezone.localize(
                datetime.datetime(2014, 2, 2)))

        self.assertEqual(
            min(week_before).from_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 19)))
        self.assertEqual(
            max(week_before).to_timestamp, self.timezone.localize(
                datetime.datetime(2014, 1, 26)))
