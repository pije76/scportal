# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from legacy.measurementpoints import default_unit_for_data_series
from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import Co2Calculation
from legacy.measurementpoints.models import DataSeries
from legacy.measurementpoints.models import DegreeDayCorrection
from legacy.measurementpoints.models import Graph
from legacy.measurementpoints.models import Link
from legacy.measurementpoints.models import RateConversion
from legacy.measurementpoints.models import Utilization
from gridplatform.utils.models import raise_if_none
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform.utils import utilitytypes

from legacy.measurementpoints.models import Collection
from .measurementpoint import MeasurementPoint


class cached_lookup_property(object):
    """
    Like C{django.utils.functional.cached_property} with short-circuit to
    return C{None} on missing C{self.id} and on C{ObjectDoesNotExist}
    exceptions.  While this might not be useful in general, it can be used to
    remove a lot of boilerplate in this file...
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, type):
        res = None
        if instance.id:
            try:
                res = self.func(instance)
            except ObjectDoesNotExist:
                pass
        instance.__dict__[self.func.__name__] = res
        return res


class ConsumptionMeasurementPoint(MeasurementPoint):
    """
    ConsumptionMeasurementPoint
    ===========================

        A C{ConsumptionMeasurementPoint} is a L{MeasurementPoint} that measures
        consumptions, i.e. has a C{consumption} L{DataSeries}.

        Rate
        ----

            From C{consumption} a C{rate} can be derived. To do this, just set
            the C{enable_rate} to C{True}.  The rate may also be set explicitly
            through the C{rate} property, but that is deprecated since the
            C{enable_rate} property was introduced.

        Heating Degree Days Corrected Consumption
        -----------------------------------------

            When the C{standard_heating_degree_days} and C{heating_degree_days}
            properties are both set, a heating degree days corrected
            consumption graph will be defined for this
            C{ConsumptionMeasurementPoint}. Setting both to C{None} will remove
            the heating degree days corrected graph again.  L{clean()} will
            complain if these are not either both set or both C{None}.

        Consumption Utilization According to Area
        -----------------------------------------

            When C{area} is set, a consumption utilization according to area
            graph will be defined for this C{ConsumptionMeasurementPoint}.

        Consumption Utilization According to Number of Employees
        --------------------------------------------------------

            When C{employees} is set, a consumption utilization according to
            the number of employees graph will be defined for this
            C{ConsumptionMeasurementPoint}.


    @ivar consumption_graph: The consumption graph of this C{MeasurementPoint}.
    The C{consumption_graph} is a read-only property, and is implicitly created
    upon setting the C{consumption} property.

    @ivar consumption: The consumption data series, typically a
    L{LogicalInput}, visualized in the consumption graph.

    @ivar rate_graph: The rate graph of this C{MeasurementPoint}.  The
    C{rate_graph} is a read-only property, and is implicitly created upon
    setting the C{rate} property.

    @ivar rate: The rate data series, typically a L{LogicalInput}, visualized
    in the rate graph.

    @ivar cost: The cost data series.

    @ivar enable_rate: When true, C{rate} is automatically derived from
    C{consumption}.

    @bug: not explicitly setting C{enable_rate} causes existing rate graphs to
    be deleted.

    @ivar standard_heating_degree_days: A DataSeries that defines the standard
    heating degree days used in heating degree days corrected consumption.

    @ivar heating_degree_days: A DataSeries that defines the actual heating
    degree days used in heating degree days corrected consumption.
    """

    UTILITY_TYPE_TO_CONSUMPTION_RATE_ROLE = {
        utilitytypes.METER_CHOICES.electricity: DataRoleField.POWER,
        utilitytypes.METER_CHOICES.district_heating: DataRoleField.POWER,
        utilitytypes.METER_CHOICES.gas: DataRoleField.VOLUME_FLOW,
        utilitytypes.METER_CHOICES.water: DataRoleField.VOLUME_FLOW,
        utilitytypes.METER_CHOICES.oil: DataRoleField.VOLUME_FLOW
    }

    def __init__(self, *args, **kwargs):
        super(ConsumptionMeasurementPoint, self).__init__(*args, **kwargs)
        self._rate_conversion = None
        self.enable_rate = True

    class Meta:
        proxy = True
        verbose_name = _('Consumption measurement point')
        verbose_name_plural = _('Consumption measurement points')
        app_label = 'customers'

    def save(self, *args, **kwargs):
        """
        Save the various components of this C{MeasurementPoint}
        """
        assert self.consumption, \
            "A MeasurementPoint must have a consumption DataSeries"
        assert self.consumption_graph, \
            "A MeasurementPoint must have a consumption Graph"

        if self.role is None:
            self.role = Collection.CONSUMPTION_MEASUREMENT_POINT

        super(ConsumptionMeasurementPoint, self).save(*args, **kwargs)
        assert self is self.consumption_graph.collection

        # Django bug
        self.consumption_graph.collection = self.consumption_graph.collection
        assert self.consumption_graph.collection_id

        self.consumption_graph.save()

        # Django bug:
        self.consumption.graph = self._consumption.graph
        assert self.consumption.graph_id

        self.consumption.save()

        if self.enable_rate and self.rate is None:
            self.rate = RateConversion(
                role=self.UTILITY_TYPE_TO_CONSUMPTION_RATE_ROLE[
                    self.consumption.utility_type],
                unit=default_unit_for_data_series(
                    self.UTILITY_TYPE_TO_CONSUMPTION_RATE_ROLE[
                        self.consumption.utility_type],
                    self.consumption.utility_type),
                utility_type=self.consumption.utility_type,
                consumption=self.consumption,
                customer=self.customer)
        elif not self.enable_rate and self.rate is not None:
            if self.rate_graph.id:
                self.rate_graph.delete()
                from legacy.display_widgets.models import DashboardWidget
                widgets = DashboardWidget.objects.filter(
                    collection=self.id,
                    widget_type__in=[
                        DashboardWidget.GAUGE, DashboardWidget.RATE_GRAPH])
                widgets.delete()
            self._rate = None
            self.rate_graph = None

        if self.co2 and not self.co2_graph.dataseries_set.exists():
            self._co2_graph = Graph.objects.create(
                collection=self,
                role=DataRoleField.CO2)
            self.co2calculation = Co2Calculation.objects.create(
                role=DataRoleField.CO2,
                utility_type=self.consumption.utility_type,
                unit='gram',
                index=self.co2,
                consumption=self.consumption,
                graph=self._co2_graph)
        elif self.co2 and self.co2calculation.index != self.co2:
            self.co2calculation.index = self.co2
            self.co2calculation.save()

        if not self.__dict__.get('co2', None) and \
                self.co2_graph.dataseries_set.exists():
            self.co2_graph.delete()

        if self.rate_graph and self.rate:
            if self._rate_conversion:
                self._rate_conversion.save()

            # Django bug:
            self.rate_graph.collection = self.rate_graph.collection
            assert self.rate_graph.collection_id

            self.rate_graph.save()

            # Django bug:
            self.rate.graph = self.rate.graph
            assert self.rate.graph_id

            self.rate.save()

        ##
        # heating degree days corrected consumption
        ##
        if self.standard_heating_degree_days is not None and\
                self.heating_degree_days is not None:
            # enable heating degree days corrected consumption
            if self.heating_degree_days_corrected_consumption is None:
                # construct if missing
                heating_degree_days_graph = self.graph_set.create(
                    role=DataRoleField.
                    HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION)
                assert heating_degree_days_graph.id
                self.heating_degree_days_corrected_consumption = \
                    DegreeDayCorrection(
                        graph=heating_degree_days_graph,
                        role=DataRoleField.
                        HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION,
                        utility_type=self.utility_type)
            # delegate properties
            assert self.heating_degree_days_corrected_consumption is not None
            self.heating_degree_days_corrected_consumption.\
                consumption = self.consumption
            self.heating_degree_days_corrected_consumption.\
                standarddegreedays = self.standard_heating_degree_days
            self.heating_degree_days_corrected_consumption.\
                degreedays = self.heating_degree_days
            self.heating_degree_days_corrected_consumption.\
                unit = self.consumption.unit
            self.heating_degree_days_corrected_consumption.save()
        elif self.heating_degree_days_corrected_consumption:
            # disable heating degree days corrected consumption: remove if
            # exists
            assert self.heating_degree_days_corrected_consumption.graph.id
            self.heating_degree_days_corrected_consumption.graph.delete()
            self.heating_degree_days_corrected_consumption = None

        ##
        # consumption utilization according to number of employees and
        # consumption utilization according to area
        ##
        for attribute_name, role, unit_extension in \
                [('employees',
                  DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES,
                  'person^-1*hour^-1'),
                 ('area',
                  DataRoleField.CONSUMPTION_UTILIZATION_AREA,
                  'meter^-2*hour^-1')]:
            if getattr(self, attribute_name):
                assert (1 / PhysicalQuantity(1, unit_extension)).\
                    compatible_unit(
                        getattr(self, attribute_name).unit + '*hour'), \
                    'unit_extension: %s, unit: %s' % (
                        unit_extension,
                        getattr(self, attribute_name).unit + '*hour')
                utilization_unit = '{}*{}'.format(
                    self.consumption.unit,
                    unit_extension)
                graph = Graph.objects.get_or_create(
                    role=role,
                    collection=self)[0]
                utilization, created = Utilization.objects.get_or_create(
                    customer=self.customer, role=role, graph=graph,
                    defaults={
                        'unit': utilization_unit,
                        'consumption': self.consumption,
                        'needs': getattr(self, attribute_name),
                        'utility_type': self.utility_type})
                if not created:
                    utilization.unit = utilization_unit
                    utilization.consumption = self.consumption
                    utilization.needs = getattr(self, attribute_name)
                    utilization.utility_type = self.utility_type
                    utilization.save()
            else:
                Graph.objects.filter(role=role, collection=self).delete()

    def clean(self):
        """
        Check heating degree days corrected consumption: either both are
        C{None} or neither can be C{None}.
        """
        super(ConsumptionMeasurementPoint, self).clean()

        if self.hidden_on_reports_page and self.used_in_report():
            raise ValidationError(
                _(u'You are not allowed to to hide this measurement point '
                  'from reports while it is used in a report'))

        if self.consumption:
            self.consumption.subclass_instance.clean()

        if bool(self.standard_heating_degree_days is None) ^ \
                bool(self.heating_degree_days is None):
            raise ValidationError(
                _(u'Both standard heating degree days and heating degree days '
                  'must be set for heating degree days corrected consumption '
                  'to be enabled.  To disable, deselect both.'))

    @cached_lookup_property
    def area(self):
        utilization = Utilization.objects.get(
            graph__collection=self.id,
            role=DataRoleField.CONSUMPTION_UTILIZATION_AREA)
        return utilization.needs.subclass_instance

    @cached_property
    def co2_graph(self):
        try:
            raise_if_none(self.id, Graph.DoesNotExist)
            return self.graph_set.get(role=DataRoleField.CO2)
        except Graph.DoesNotExist:
            return Graph(collection=self, role=DataRoleField.CO2)

    @cached_property
    def co2calculation(self):
        try:
            return DataSeries.objects.get(
                graph=self.co2_graph).subclass_instance
        except DataSeries.DoesNotExist:
            return None

    @cached_lookup_property
    def co2(self):
        return Co2Calculation.objects.get(
            graph__collection=self.id,
            role=DataRoleField.CO2).index.subclass_instance

    @cached_lookup_property
    def employees(self):
        utilization = Utilization.objects.get(
            graph__collection=self.id,
            role=DataRoleField.CONSUMPTION_UTILIZATION_EMPLOYEES)
        return utilization.needs.subclass_instance

    @cached_property
    def consumption_graph(self):
        try:
            raise_if_none(self.id, Graph.DoesNotExist)
            return self.graph_set.get(
                hidden=False,
                role=DataRoleField.CONSUMPTION)
        except Graph.DoesNotExist:
            return Graph(collection=self, role=DataRoleField.CONSUMPTION)

    _consumption = None

    def _get_consumption(self):
        # ... this property may make sense to use when not a logical input...?
        if not self._consumption and self.consumption_graph.id:
            try:
                self._consumption = self.consumption_graph.\
                    dataseries_set.get().subclass_instance
            except DataSeries.DoesNotExist:
                pass
        return self._consumption

    def _set_consumption(self, consumption):
        if self.consumption_graph.id:
            self.consumption_graph.dataseries_set.delete()
        consumption.graph = self.consumption_graph
        self._consumption = consumption

    consumption = property(_get_consumption, _set_consumption)

    def _get_consumption_input(self):
        if self.consumption is None:
            return None
        return self.consumption.target.subclass_instance

    def _set_consumption_input(self, consumption_input):
        if consumption_input is None:
            return
        if not self.consumption:
            self.consumption = Link(
                utility_type=self.utility_type,
                role=DataRoleField.CONSUMPTION,
                unit=consumption_input.unit)
        self._consumption.target = consumption_input

    consumption_input = property(
        _get_consumption_input, _set_consumption_input)

    @cached_property
    def rate_graph(self):
        try:
            raise_if_none(self.id, Graph.DoesNotExist)
            return self.graph_set.get(
                role__in=self.UTILITY_TYPE_TO_CONSUMPTION_RATE_ROLE.values())
        except Graph.DoesNotExist:
            return Graph(collection=self)

    _rate = None

    def _get_rate(self):
        if not self._rate and self.rate_graph.id:
            try:
                self._rate = \
                    self.rate_graph.dataseries_set.get().subclass_instance
            except DataSeries.DoesNotExist:
                pass
        return self._rate

    def _set_rate(self, data_series):
        assert data_series.role in \
            self.UTILITY_TYPE_TO_CONSUMPTION_RATE_ROLE.values()
        if self.rate_graph.id:
            self.rate_graph.dataseries_set.all().delete()
        self.rate_graph.role = data_series.role
        data_series.graph = self.rate_graph
        self._rate = data_series

    rate = property(_get_rate, _set_rate)

    def get_gauge_data_series(self):
        """
        This method defines which L{DataSeries} (if any) should be displayed in
        a gauge widget, if any.
        """
        return self.rate

    @property
    def cost(self):
        try:
            return DataSeries.objects.get(
                graph__collection=self,
                role=DataRoleField.COST).subclass_instance
        except DataSeries.DoesNotExist:
            return None

    @cached_property
    def standard_heating_degree_days(self):
        if self.heating_degree_days_corrected_consumption:
            return self.heating_degree_days_corrected_consumption.\
                standarddegreedays
        else:
            return None

    @cached_property
    def heating_degree_days(self):
        if self.heating_degree_days_corrected_consumption:
            return self.heating_degree_days_corrected_consumption.degreedays
        else:
            return None

    @cached_lookup_property
    def heating_degree_days_corrected_consumption(self):
        """
        Helper property for implementing C{standard_heating_degree_days} and
        C{heating_degree_days} properties.
        """
        return DegreeDayCorrection.objects.get(
            graph__collection_id=self.id,
            role=DataRoleField.
            HEATING_DEGREE_DAYS_CORRECTED_CONSUMPTION)
