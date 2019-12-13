Utillities
==========

The ``utils`` app contains various utility abstractions.  The primary
purpose is to contain the clutter.

Miscelaneous Functions
----------------------

.. autofunction:: gridplatform.utils.unix_timestamp

.. autofunction:: gridplatform.utils.first_last

.. autofunction:: gridplatform.utils.fraction_to_decimal

.. autofunction:: gridplatform.utils.choices_extract_python_identifier

.. autofunction:: gridplatform.utils.development_sum

.. autofunction:: gridplatform.utils.sum_or_none

Breadcrumbs
-----------

Breadcrumbs are somewhat easier to work with given the following two
classes:

.. autoclass:: gridplatform.utils.breadcrumbs.Breadcrumb

.. autoclass:: gridplatform.utils.breadcrumbs.Breadcrumbs
   :members: __add__


ID Formatters
-------------

.. autofunction:: gridplatform.utils.format_id.format_mac
.. autofunction:: gridplatform.utils.format_id.format_mbus_manufacturer
.. autofunction:: gridplatform.utils.format_id.format_mbus_enhanced


FTP client
----------

.. autofunction:: gridplatform.utils.ftpclient.ftpconnection

Iterator Extensions
-------------------

.. automodule:: gridplatform.utils.iter_ext
   :members: nwise, triplewise, pairwise, pairwise_extended, flatten,
             tee_lookahead, count_extended

API
---

Utility functions for previous and next links in REST API for
resources that are defined in terms of data sequences.

.. autofunction:: gridplatform.utils.api.next_valid_date_for_datasequence
.. autofunction:: gridplatform.utils.api.previous_valid_date_for_datasequence


Context Managers
----------------

.. autofunction:: gridplatform.utils.contextmanagers.global_context


Condense
--------

.. automodule:: gridplatform.utils.condense
   :members: next_resolution, is_finer_resolution,
             is_coarser_resolution, floor, ceil, get_date_formatter

Decorators
----------

.. autofunction:: gridplatform.utils.decorators.deprecated
.. autofunction:: gridplatform.utils.decorators.virtual
.. autofunction:: gridplatform.utils.decorators.permission_required


Fields
------

.. autofunction:: gridplatform.utils.fields.parse_mac

.. autoclass:: gridplatform.utils.fields.MacAddress
.. autoclass:: gridplatform.utils.fields.MacAddressFormField
.. autoclass:: gridplatform.utils.fields.MacAddressField
   :members: to_python, get_internal_type, formfield

.. autoclass:: gridplatform.utils.fields.JSONEncoder
   :members: default

.. autoclass:: gridplatform.utils.fields.JSONField
   :members: __init__, to_python, get_prep_value, value_to_string,
             value_from_object

.. autoclass:: gridplatform.utils.fields.SplitHourMinuteWidget
   :members: decompress

.. autoclass:: gridplatform.utils.fields.SplitHiddenHourMinuteWidget

.. autoclass:: gridplatform.utils.fields.DurationFormField
   :members: compress

.. autoclass:: gridplatform.utils.fields.DurationField
   :members: formfield

.. autoclass:: gridplatform.utils.fields.PercentField
   :members: __init__

.. autoclass:: gridplatform.utils.fields.ImageFieldWithLoadCheck
   :members: to_python

.. autoclass:: gridplatform.utils.fields.ImageModelFieldWithLoadCheck
   :members: formfield

.. autoclass:: gridplatform.utils.fields.BigAutoField

.. autoclass:: gridplatform.utils.fields.BuckinghamField
   :members: validate, get_prep_value


Forms
-----

.. autoclass:: gridplatform.utils.forms.TimePeriodFormMixin
   :members: __init__, clean

.. autoclass:: gridplatform.utils.forms.TimePeriodForm

.. autoclass:: gridplatform.utils.forms.TimePeriodModelForm
   :members: __init__, clean

.. autoclass:: gridplatform.utils.forms.HalfOpenTimePeriodModelForm
   :members: clean

.. autofunction:: gridplatform.utils.forms.previous_month_initial_values

.. autofunction:: gridplatform.utils.forms.this_week_initial_values

.. autoclass:: gridplatform.utils.forms.YearWeekPeriodForm
   :members: __init__, clean, get_timestamps


Formsets
--------

.. autoclass:: gridplatform.utils.formsets.SurvivingFormsModelFormSetMixin
   :members: surviving_forms


Generic Views
-------------

.. automodule:: gridplatform.utils.generic_views
   :members: ListView, DetailView, CreateView, DeleteView, UpdateView,
             InlineFormSet, ModelFormSetView, InlineFormSetView,
             CreateWithInlinesView, UpdateWithInlinesView, View,
             TemplateView, SearchableListMixin, FormView

Access Control
^^^^^^^^^^^^^^

.. autoclass:: gridplatform.utils.generic_views.access_control.CheckAJAXMixin

.. autoclass:: gridplatform.utils.generic_views.access_control.LoginRequiredMixin

.. autoclass:: gridplatform.utils.generic_views.access_control.ModelPermissionRequiredMixin

.. autoclass:: gridplatform.utils.generic_views.access_control.MultipleModelPermissionsRequiredMixin

.. autoclass:: gridplatform.utils.generic_views.access_control.CustomerBoundMixin


Localized
^^^^^^^^^

.. autoclass:: gridplatform.utils.generic_views.localized.LocalizedModelFormMixin
   :members: get_form_class

.. autoclass:: gridplatform.utils.generic_views.localized.LocalizedModelFormSetMixin
   :members: get_factory_kwargs

.. autoclass:: gridplatform.utils.generic_views.localized.LocalizedInlineFormSetMixin
   :members: get_factory_kwargs

Commands
--------

.. automodule:: gridplatform.utils.management.commands.check_db_connection

.. automodule:: gridplatform.utils.management.commands.fix_contenttypes_and_permissions


Managers
--------

.. autoclass:: gridplatform.utils.managers.DateRangeManagerMixin
   :members: in_range

.. autoclass:: gridplatform.utils.managers.TimestampRangeManagerMixin
   :members: in_range


Middleware
----------

.. autoclass:: gridplatform.utils.middleware.ExceptionRemoveInfoMiddleware
.. autoclass:: gridplatform.utils.middleware.ExceptionAddInfoMiddleware
.. autoclass:: gridplatform.utils.middleware.TimezoneMiddleware

Models
------

.. autoclass:: gridplatform.utils.models.StoredSubclassManager
   :members: get_query_set, subclass_only, _model_subclasses

.. autoclass:: gridplatform.utils.models.StoreSubclass
   :members: clean

.. autoclass:: gridplatform.utils.models.DateRangeModelMixin
   :members: clean, timestamp_range_intersection

.. autoclass:: gridplatform.utils.models.TimestampRangeModelMixin
   :members: clean, format_timestamp_range_unicode, overlapping

Paginator
---------

.. automodule:: gridplatform.utils.paginator
   :members: parse_date, Http404ApiException, parse_date_or_404

Unit Converters
---------------

.. automodule:: gridplatform.utils.preferredunits
   :members: UnitConverter, PhysicalUnitConverter, KvarUnitConverter,
             KvarhUnitConverter, PowerFactorUnitConverter,
             DisplayCelsiusMixin, RelativeCelsiusUnitConverter,
             AbsoluteCelsiusUnitConverter, DisplayFahrenheitMixin,
             RelativeFahrenheitUnitConverter,
             AbsoluteFahrenheitUnitConverter,
             AbstractENPIUnitConverter, PersonsENPIUnitConverter,
             AreaENPIUnitConverter,
             AbstractProductionENPIUnitConverter,
             ProductionAENPIUnitConverter,
             ProductionBENPIUnitConverter,
             ProductionCENPIUnitConverter,
             ProductionDENPIUnitConverter,
             ProductionEENPIUnitConverter, ProductionUnitConverter,
             EfficiencyUnitConverter

Relative Time Delta
-------------------

.. automodule:: gridplatform.utils.relativetimedelta
   :members: wrap, RelativeTimeDelta

Samples
-------

.. automodule:: gridplatform.utils.samples
   :members: Sample, wrap_ranged_sample, wrap_ranged_sample_sequence

Serializers
-----------

.. autoclass:: gridplatform.utils.serializers.SampleBase
   :members: get_unit, get_display_unit, get_value

.. autoclass:: gridplatform.utils.serializers.PointSampleSerializer
.. autoclass:: gridplatform.utils.serializers.RangedSampleSerializer

Template Tags
-------------

.. autofunction:: gridplatform.utils.templatetags.utils.insertnbsp
.. autofunction:: gridplatform.utils.templatetags.utils.jsonify
.. autofunction:: gridplatform.utils.templatetags.utils.buckingham_display

Unit Conversion
---------------

.. automodule:: gridplatform.utils.unitconversion
   :members: PhysicalQuantity, simple_convert

Units
-----

.. automodule:: gridplatform.utils.units

Utility Types
-------------

.. automodule:: gridplatform.utils.utilitytypes


Validators
----------

.. autofunction:: gridplatform.utils.validators.nonzero_validator
.. autofunction:: gridplatform.utils.validators.in_the_past_validator
.. autofunction:: gridplatform.utils.validators.clean_overlapping


Views
-----

.. autofunction:: gridplatform.utils.views.json_response
.. autofunction:: gridplatform.utils.views.json_list_response

.. autoclass:: gridplatform.utils.views.JsonResponse
   :members: data

.. autoclass:: gridplatform.utils.views.JsonResponseBadRequest

.. autoclass:: gridplatform.utils.views.DateLocalEpoch
   :members: default

.. autofunction:: gridplatform.utils.views.date_epoch_json_response

.. autofunction:: gridplatform.utils.views.render_to

.. autofunction:: gridplatform.utils.views.json_list_options

.. autoclass:: gridplatform.utils.views.FileView
   :members: get

.. autoclass:: gridplatform.utils.views.NoCustomerMixin

.. autoclass:: gridplatform.utils.views.CustomerContextMixin
   :members: get_context_data

.. autoclass:: gridplatform.utils.views.CustomerInKwargsMixin

.. autoclass:: gridplatform.utils.views.CustomersContextMixin
   :members: get_context_data

.. autoclass:: gridplatform.utils.views.CustomerListMixin
   :members: _customer

.. autofunction:: gridplatform.utils.views.task_status

.. autoclass:: gridplatform.utils.views.StartTaskView
   :members: get_task_kwargs, get_task, get_status_url,
             get_finalize_url, start_task, form_valid, form_invalid

.. autoclass:: gridplatform.utils.views.TaskForm

.. autoclass:: gridplatform.utils.views.FinalizeTaskView
   :members: finalize_task, form_valid, form_invalid

.. autoclass:: gridplatform.utils.views.HomeViewBase
   :members: get_redirect_url

.. autoclass:: gridplatform.utils.views.ChooseCustomerBase
   :members: get_context_data

.. autoclass:: gridplatform.utils.views.CustomerViewBase
   :members: get_redirect_url, get_redirect_with_customer_url
