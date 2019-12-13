# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import unicodecsv
from datetime import datetime
from itertools import islice
from itertools import izip
from itertools import count

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from fractions import Fraction

from legacy.measurementpoints import default_unit_for_data_series
from legacy.measurementpoints.models import StoredDataSeries
from legacy.measurementpoints.models import StoredData
from legacy.measurementpoints.fields import DataRoleField
from gridplatform.utils.unitconversion import PhysicalQuantity
from gridplatform import trackuser

from .consumptionmeasurementpoint import ConsumptionMeasurementPoint


class ImportedMeasurementPoint(ConsumptionMeasurementPoint):
    """
    Measurement point for importing consumption data from a CSV file.

    @ivar uploaded_file: The CSV file containing the consumption data.

    @ivar consumption_column: Consumption values will be extracted from this
    column (0 indexed). This field is by default set to '1', but it is
    suggested to let the user choose.

    @ivar first_consumption_row: The CSV file may contain a headline along with
    other irrelevant formatting.  This integer defines where to start parsing
    consumption.  This field has a default value is set to '2' This works well
    with the example files we were given as acceptance criteria.

    @ivar column_delimiter: In Europe a semi-colon ';' is used to seperate the
    values in a CSV file , but in the US a comma ',' is used (comma separated
    values). This field default value it set to ';'

    @ivar decimal_delimiter: In some parts of the world a comma ',' is used,
    whereas in others a dot '.' is used.
    See U{http://en.wikipedia.org/wiki/Decimal_mark}, and note that this is not
    simple US vs Europe issue. This field default value is to to ','

    @ivar unit: The unit that the consumption data in the C{uploaded_file} is
    stored in.  This field is required.

    @ivar timezone: The timezone that the time stamps in the C{uploaded_file}
    are stored in. This field is required.

    @note: The time column values will be extracted from the first column
    in the oploaded file. The time column is hardcoded to '0'.
    """
    upload_file = None
    consumption_column = 1
    first_consumption_row = 2
    column_delimiter = b';'
    decimal_delimiter = ','
    parsed_csv = None
    unit = None
    timezone = None

    class Meta:
        proxy = True
        verbose_name = _('Imported measurement point')
        verbose_name_plural = _('Imported measurement points')
        app_label = 'customers'

    def __init__(self, *args, **kwargs):
        super(ImportedMeasurementPoint, self).__init__(*args, **kwargs)
        if trackuser.get_customer() is not None:
            self.timezone = trackuser.get_customer().timezone
            self.unit = trackuser.get_customer().electricity_consumption

    def save(self, *args, **kwargs):
        """
        Specialization of L{ConsumptionMeasurementPoint.save()}.

        Save uploaded CSV if not previously defined.
        """
        if not self.id:
            assert self.parsed_csv
            self.consumption = StoredDataSeries(
                utility_type=self.utility_type,
                unit=default_unit_for_data_series(
                    DataRoleField.CONSUMPTION, self.utility_type),
                role=DataRoleField.CONSUMPTION)
            super(ImportedMeasurementPoint, self).save(*args, **kwargs)
            accumulated_value = 0
            stored_data = [StoredData(timestamp=self.parsed_csv[0][0],
                                      value=0,
                                      data_series_id=self.consumption.id)]

            for from_timestamp, to_timestamp, value in self.parsed_csv:
                accumulated_value += PhysicalQuantity(
                    value, self.unit).convert(self.consumption.unit)
                stored_data.append(StoredData(
                    timestamp=to_timestamp, value=accumulated_value,
                    data_series_id=self.consumption.id))

            StoredData.objects.bulk_create(stored_data)
        else:
            super(ImportedMeasurementPoint, self).save(*args, **kwargs)

    def clean(self):
        """
        Parse C{uploaded_file} if possible.

        @raise ValidationError: When the uploaded file cannot be parsed, a
        relevant C{ValidationError} specialization is raised, explaining what
        is wrong.
        """
        if self.upload_file is not None and \
                self.timezone is not None and \
                self.unit is not None:
            self._parse_csv()

    class EmptyFileError(ValidationError):
        """
        The C{uploaded_file} did not contain any consumption data.
        """
        def __init__(self, filename):
            """
            @param filename: The name of the uploaded file that did not contain
            any consumption data.
            """
            super(ImportedMeasurementPoint.EmptyFileError, self).__init__(
                _("{filename} contains no consumption data").format(
                    filename=filename))
            self.filename = filename

    class FileValidationError(ValidationError):
        """
        Error on a particular line in the C{uploaded_file}
        """
        def __init__(self, filename, lineno, message):
            """
            @param filename: The C{uploaded_file} that contains the error.

            @param lineno: The line number that contains the error.

            @param message: A localized human readable description of the
            error.
            """
            super(ImportedMeasurementPoint.FileValidationError, self).__init__(
                u'%s:%s: %s' % (filename, lineno, message))
            self.filename = filename
            self.lineno = lineno

    class TimeValueError(FileValidationError):
        """
        A time cell could not be parsed on a particular line in the
        C{uploaded_file}
        """
        def __init__(self, filename, lineno, time_cell):
            """
            @param filename: The C{uploaded_file} that contains the error.

            @param lineno: The line number that contains the error.

            @param time_cell: The textual contents of the time cell that did
            not parse.
            """
            super(ImportedMeasurementPoint.TimeValueError, self).__init__(
                filename, lineno,
                _("Time value {time_value} did not parse").format(
                    time_value=time_cell))

    class TimeSequenceError(FileValidationError):
        def __init__(self, filename, lineno, time_cell):
            super(ImportedMeasurementPoint.TimeSequenceError, self).__init__(
                filename, lineno,
                _(
                    'Time stamps are not sequential ({time_value}), '
                    'check timezone').format(time_value=time_cell))

    class ConsumptionColumnDoesNotExist(FileValidationError):
        """
        A given consumption column does not exist at a given row on a
        particular line in the C{uploaded_file}
        """
        def __init__(self, filename, lineno, consumption_column):
            """
            @param filename: The C{uploaded_file} that contains the error.

            @param lineno: The line number that contains the error.

            @param consumption_column: The column number that was not found on
            this particular line number.
            """
            super(
                ImportedMeasurementPoint.ConsumptionColumnDoesNotExist, self).\
                __init__(
                    filename, lineno,
                    _('Column {consumption_column} does not exist').format(
                        consumption_column=consumption_column))
            self.consumption_column = consumption_column

    class ConsumptionParseError(FileValidationError):
        """
        A consumption value could not be parsed on a particular line in the
        C{uploaded_file}
        """
        def __init__(self, filename, lineno, value_cell):
            """
            @param filename: The C{uploaded_file} that contains the error.

            @param lineno: The line number that contains the error.

            @param value_cell: The textual contents of the value cell that
            could not be parsed.
            """
            super(
                ImportedMeasurementPoint.ConsumptionParseError, self).__init__(
                filename, lineno,
                _('Consumption value ({value_cell}) did not parse').format(
                    value_cell=value_cell))

    def _parse_csv(self):
        """
        Parse CSV file.  This method is intended to be called from C{clean()}

        @precondition: C{self.upload_file is not None}
        @precondition: C{self.timezone is not None}

        @postcondition: C{self.parsed_csv} is non-emtpy

        @raise EmptyFileError: When the C{uploaded_file} did not contain any
        consumption data.

        @raise TimeParseError: When a time cell could not be parsed.

        @raise ConsumptionColumnDoesNotExist: When the C{consumption_column}
        does not exist.

        @raise ConsumptionParseError: When the contents of a consumption cell
        could not be parsed.
        """
        assert self.upload_file is not None
        reader = unicodecsv.reader(
            self.upload_file,
            delimiter=self.column_delimiter,
            encoding='iso8859-1')
        self.parsed_csv = []

        row_counter = 0
        try:
            for row_counter, row in islice(izip(count(), reader),
                                           self.first_consumption_row, None):
                if len(row) == 0:
                    continue
                time_cell = row[0]
                try:
                    from_timestamp, to_timestamp = [
                        self.timezone.localize(
                            datetime.strptime(s, '%d-%m-%Y %H:%M')) for
                        s in time_cell.split(' - ')]
                    if from_timestamp > to_timestamp:
                        raise self.TimeSequenceError(
                            self.upload_file.name, row_counter, time_cell)
                    # Rows must be in a sequence of each other.
                    # Raise error if from_timestamp is not equal to_timestamp
                    # on previous row.
                    if self.parsed_csv and \
                            from_timestamp != self.parsed_csv[-1][1]:
                        raise self.TimeSequenceError(
                            self.upload_file.name,
                            row_counter,
                            '({previous_from_time} - {previous_fo_time}) '
                            '({from_timestamp} - {to_timestamp})'.format(
                                previous_from_time=self.parsed_csv[-1][0],
                                previous_fo_time=self.parsed_csv[-1][1],
                                to_timestamp=to_timestamp,
                                from_timestamp=from_timestamp))
                except ValueError:
                    raise self.TimeValueError(
                        self.upload_file.name, row_counter, time_cell)

                if self.consumption_column < len(row):
                    value_cell = row[self.consumption_column]
                else:
                    raise self.ConsumptionColumnDoesNotExist(
                        self.upload_file.name, row_counter,
                        self.consumption_column)
                try:
                    value = Fraction(
                        '.'.join(value_cell.split(self.decimal_delimiter)))
                except:
                    raise self.ConsumptionParseError(
                        self.upload_file.name,
                        row_counter, value_cell)
                self.parsed_csv.append((from_timestamp, to_timestamp, value))
        except unicodecsv.Error as e:
            raise self.FileValidationError(
                self.upload_file.name, row_counter, e)

        if not self.parsed_csv:
            raise self.EmptyFileError(self.upload_file.name)
