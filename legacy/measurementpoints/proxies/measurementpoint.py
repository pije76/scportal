# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _

from legacy.measurementpoints.fields import DataRoleField
from legacy.measurementpoints.models import Link
from legacy.measurementpoints.models import Multiplication
from legacy.measurementpoints.models import Summation
from legacy.datasequence_adapters.models import ConsumptionAccumulationAdapter
from legacy.datasequence_adapters.models import ProductionAccumulationAdapter
from legacy.datasequence_adapters.models import NonaccumulationAdapter

from legacy.measurementpoints.models import Collection
from legacy.measurementpoints.models import CollectionConstraint


class MeasurementPoint(Collection):
    """
    A C{MeasurementPoint} is a special application of a L{Collection}.

    This class is a proxy model of L{Collection}. The idea is to make it easier
    to create and modify measurement point L{Collection}s through relevant
    property methods for retrieving and modifying the entities which, when
    combined, form an actual measurement point.
    """
    class Meta:
        proxy = True
        verbose_name = _('Measurement point')
        verbose_name_plural = _('Measurement points')
        app_label = 'customers'

    def save(self, *args, **kwargs):
        """
        C{MeasurementPoint} override of C{Collection.save()}.

        Create a hidden graph related to this C{MeasurementPoint} and add
        hidden data series to it.  The idea is that these data series are
        automatically deleted when this C{MeasurementPoint} is.
        """

        super(MeasurementPoint, self).save(*args, **kwargs)

        if self._hidden:
            hidden_graph, created = self.graph_set.get_or_create(
                role=DataRoleField.HIDDEN, hidden=True)
            for ds in self._hidden:
                ds.graph = hidden_graph
                ds.save()

    def clean(self):
        super(MeasurementPoint, self).clean()
        # If Gauge widget is present on the Dashboard, verify that
        # that values are not corrupted by the user.
        from legacy.display_widgets.models import DashboardWidget
        widget = DashboardWidget.objects.filter(
            collection=self.id,
            widget_type=DashboardWidget.GAUGE)
        if widget and (self.gauge_lower_threshold is None or
                       self.gauge_upper_threshold is None or
                       self.gauge_min is None or
                       self.gauge_max is None or
                       self.gauge_colours is None):
                raise ValidationError(
                    _('Gauge widget is present on the dashboard; \
                        corrupting these values are not allowed'))
        else:
            if self.gauge_max is not None and \
                self.gauge_min is not None and \
                    self.gauge_max <= self.gauge_min:
                raise ValidationError(
                    _('Maximum value must be above minumum value'))
            if self.gauge_lower_threshold is not None and \
                self.gauge_lower_threshold is not None and \
                    self.gauge_lower_threshold < self.gauge_min:
                raise ValidationError(
                    _('Lower threshold must be above minumum value'))
            if self.gauge_upper_threshold is not None and \
                self.gauge_max is not None \
                    and self.gauge_upper_threshold > self.gauge_max:
                raise ValidationError(
                    _('Upper threshold must be below maximum value'))
            if self.gauge_upper_threshold is not None and \
                self.gauge_lower_threshold is not None \
                    and self.gauge_upper_threshold <= \
                    self.gauge_lower_threshold:
                raise ValidationError(
                    _('Upper threshold must be above lower threshold'))

    def get_verbose_name_display(self):
        return self.subclass_instance._meta.verbose_name

    def get_gauge_data_series(self):
        """
        This abstract method defines which L{DataSeries} (if any) should be
        displayed in a gauge widget, if any.
        """
        return None

    def get_input_configurations(self):
        return \
            list(ConsumptionAccumulationAdapter.objects.filter(
                link_derivative_set__graph__collection=self)) + \
            list(ProductionAccumulationAdapter.objects.filter(
                link_derivative_set__graph__collection=self)) + \
            list(NonaccumulationAdapter.objects.filter(
                link_derivative_set__graph__collection=self))

    def has_gauge(self):
        """
        Check if this MeasurementPoint has a gauge that can be displayed.

        @return: C{True} if a gauge can be displayed, false otherwise.
        """

        return self.get_gauge_data_series() is not None and \
            self.gauge_lower_threshold is not None and \
            self.gauge_upper_threshold is not None and \
            self.gauge_min is not None and \
            self.gauge_max is not None and \
            self.gauge_colours is not None and \
            self.gauge_preferred_unit is not None

    def has_consumption(self):
        """
        Check if this MeasurementPoint has a consumption data_series
        that can be displayed.

        @return: C{True} if consumption widget can be displayed, false
        otherwise.
        """
        return bool(self.consumption)

    def has_rate(self):
        """
        Check if this MeasurementPoint has a rate data_series
        that can be displayed.

        @return: C{True} if rate widget can be displayed, false
        otherwise.
        """
        return bool(self.rate)

    def has_cooldown(self):
        """
        Check if this MeasurementPoint has a cooldown data_series
        that can be displayed

        @return: C{True} if cooldown widgets can be displayed. false
        otherwise
        """

        return self.graph_set.filter(
            role=DataRoleField.MEAN_COOLDOWN_TEMPERATURE).exists()

    def has_widgets(self):
        """
        Check if this MeasurementPoint has anything that
        can be displayed as a widget.

        @return: C{True} if widgets can be displayed, false otherwise.
        """
        return bool(
            self.has_consumption or
            self.has_gauge or self.has_rate or
            self.has_cooldown or self.has_production)

    def has_production(self):
        return self.graph_set.filter(
            role=DataRoleField.PRODUCTION).exists()

    @cached_property
    def _hidden(self):
        # "lazy" initialisation of self._hidden; put here to be close to use in
        # add_hidden and completely remove __init__()
        return []

    def add_hidden(self, data_series):
        """
        Add a hidden L{DataSeries} to this C{MeasurementPoint}.

        The idea is that these data series are automatically deleted when this
        C{MeasurementPoint} is.
        """
        self._hidden.append(data_series)

    def get_gauge_unit_display(self):
        """
        Returns a humam readable gauge preferred unit string.
        Using customers preferred unit for the rate dataseries,
        if gauge preferred unit has not yet been saved.
        """
        if self.gauge_preferred_unit:
            return self.get_gauge_preferred_unit_display()
        elif self.rate:
            return self.rate.get_preferred_unit_converter().get_display_unit()
        else:
            return None

    def get_delete_prevention_reason(self):
        """
        Returns a HTML formated string with a description of why
        this measurement point cannot be deleted.
        Returning None, if no reason exist, meaning the measurement point can
        be deleted without breaking anything.
        """
        from legacy.projects.models import BenchmarkProject
        from legacy.energy_use_reports.models import EnergyUseReport

        if self.is_deletable():
            return None

        dependents = []
        projects = set(BenchmarkProject.objects.filter(
            baseline_measurement_points__id=self.id)) | \
            set(BenchmarkProject.objects.filter(
                result_measurement_points__id=self.id))
        if projects:
            dependents.append(unicode(_("Projects:")))
            dependents.append('<ul>')
            for project in projects:
                dependents.append('<li>%s</li>' % (escape(unicode(project)),))
            dependents.append('</ul>')

        summations = Summation.objects.filter(
            terms__data_series=self.consumption).prefetch_related(
            'graph__collection').distinct()
        if summations:
            dependents.append(unicode(_("Summation Measurement Points:")))
            dependents.append('<ul>')
            for summation in summations:
                dependents.append(
                    '<li>%s</li>' % (
                        escape(unicode(summation.graph.collection)), ))
            dependents.append('</ul>')

        multiplications = Multiplication.objects.filter(
            source_data_series=self.consumption).prefetch_related(
            'graph__collection').distinct()
        if multiplications:
            dependents.append(unicode(_("Multiplication Measurement Points:")))
            dependents.append('<ul>')
            for multiplication in multiplications:
                dependents.append(
                    '<li>%s</li>' % (
                        escape(unicode(multiplication.graph.collection)),))
            dependents.append('</ul>')

        links = Link.objects.filter(
            target=self.consumption).prefetch_related(
            'graph__collection').distinct()
        if links:
            dependents.append(
                unicode(_("District Heating Measurement Points:")))
            dependents.append('<ul>')
            for link in links:
                dependents.append(
                    '<li>%s</li>' % (escape(unicode(link.graph.collection)),))
            dependents.append('</ul>')

        energy_use_reports = EnergyUseReport.objects.filter(
            energyusearea__measurement_points=self)
        if energy_use_reports:
            dependents.append(unicode(_("Energy Use Reports:")))
            dependents.append('<ul>')
            for report in energy_use_reports:
                dependents.append('<li>%s</li>' % (escape(unicode(report)),))
            dependents.append('</ul>')

        constraints = CollectionConstraint.objects.filter(
            collection=self)
        if constraints:
            dependents.append(unicode(_("Users:")))
            dependents.append('<ul>')
            for constraint in constraints:
                dependents.append('<li>%s</li>' % (
                    escape(unicode(constraint.userprofile.user)),))
            dependents.append('</ul>')

        if dependents:
            return _(
                'This measurement point cannot be deleted '
                'because the following depends on it:') + "<br />" + \
                "".join(dependents)

    def used_in_report(self):
        """Checks if this measurementpoint is used in an energy use report"""
        from legacy.energy_use_reports.models import EnergyUseReport
        energy_use_reports = EnergyUseReport.objects.filter(
            energyusearea__measurement_points=self)

        return len(energy_use_reports) > 0

    def is_deletable(self):
        """
        Returns true or false whether
        this measurement point can be deleted or not.
        """
        # Importing inline because
        from legacy.energy_use_reports.models import EnergyUseReport

        links = Link.objects.filter(target=self.consumption).count()
        multiplication = Multiplication.objects.filter(
            source_data_series=self.consumption).count()
        from legacy.projects.models import BenchmarkProject
        baselineinclusion = BenchmarkProject.objects.filter(
            baseline_measurement_points__id=self.id).exists()
        resultinclusion = BenchmarkProject.objects.filter(
            result_measurement_points__id=self.id).exists()
        summation = Summation.objects.filter(
            terms__data_series=self.consumption).count()
        energy_use_reports = EnergyUseReport.objects.filter(
            energyusearea__measurement_points=self)
        constraints = CollectionConstraint.objects.filter(
            collection=self).count()

        return not any([
            links, multiplication,
            baselineinclusion, resultinclusion,
            summation, energy_use_reports, constraints
        ])
