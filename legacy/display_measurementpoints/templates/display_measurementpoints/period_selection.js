/*jslint browser: true */
/*global $, jQuery, gettext, pgettext, get_format */
$(document).ready(function () {
    'use strict';
    var toDayStart = function (date) {
            /* midnight at start of day */
            var newDate = new Date(date);
            newDate.setHours(0);
            newDate.setMinutes(0);
            newDate.setSeconds(0);
            newDate.setMilliseconds(0);
            return newDate;
        },
        toWeekStart = function (date) {
            /* days to subtract to get monday --- getDay() counts from 0 == sunday */
            var daysOffset = (7 + date.getDay() - 1) % 7;
            return new Date(toDayStart(date).valueOf() - daysOffset * 24 * 60 * 60 * 1000);
        },
        toMonthStart = function (date) {
            var newDate = toDayStart(date);
            /* days count from 1 */
            newDate.setDate(1);
            return newDate;
        },
        incrementMonth = function (date) {
            var newDate = new Date(date);
            /* months count from 0 ... */
            if (newDate.getMonth() < 11) {
                newDate.setMonth(newDate.getMonth() + 1);
            } else {
                newDate.setFullYear(newDate.getFullYear() + 1);
                newDate.setMonth(0);
            }
            return newDate;
        },
        decrementMonth = function (date) {
            var newDate = new Date(date);
            /* months count from 0 ... */
            if (newDate.getMonth() > 0) {
                newDate.setMonth(newDate.getMonth() - 1);
            } else {
                newDate.setFullYear(newDate.getFullYear() - 1);
                newDate.setMonth(11);
            }
            return newDate;
        },
        fromdate_close = function () {
            var fromDate = $('#id_from_date').datetimepicker('getDate'),
                toDate = $('#id_to_date').datetimepicker('getDate');
            if (fromDate && toDate && fromDate > toDate) {
                /* start of day, add day, subtract minute */
                toDate = new Date(toDayStart(fromDate).valueOf() + 24 * 60 * 60 * 1000 - 60 * 1000);
                $('#id_to_date').datetimepicker('setDate', toDate);
            }
        },
        todate_close = function () {
            var fromDate = $('#id_from_date').datetimepicker('getDate'),
                toDate = $('#id_to_date').datetimepicker('getDate');
            if (fromDate && toDate && toDate < fromDate) {
                fromDate = toDayStart(toDate);
                $('#id_from_date').datetimepicker('setDate', fromDate);
            }
        };
    $('#period-day').click(function (event) {
        var now = new Date(),
            fromDate = toDayStart(now),
            /* add day, subtract minute*/
            toDate = new Date(fromDate.valueOf() + 24 * 60 * 60 * 1000 - 60 * 1000);
        event.preventDefault();
        event.stopPropagation();
        $('#id_from_date').datetimepicker('setDate', fromDate);
        $('#id_to_date').datetimepicker('setDate', toDate);
        $('#period-selection').submit();
    });
    $('#period-week').click(function (event) {
        var now = new Date(),
            fromDate = toWeekStart(now),
            /* add week, subtract minute */
            toDate = new Date(fromDate.valueOf() + 7 * 24 * 60 * 60 * 1000 - 60 * 1000);
        event.preventDefault();
        event.stopPropagation();
        $('#id_from_date').datetimepicker('setDate', fromDate);
        $('#id_to_date').datetimepicker('setDate', toDate);
        $('#period-selection').submit();
    });
    $('#period-month').click(function (event) {
        var now = new Date(),
            fromDate = toMonthStart(now),
            /* add month, subtract minute */
            toDate = new Date(incrementMonth(fromDate).valueOf() - 60 * 1000);
        event.preventDefault();
        event.stopPropagation();
        $('#id_from_date').datetimepicker('setDate', fromDate);
        $('#id_to_date').datetimepicker('setDate', toDate);
        $('#period-selection').submit();
    });
    $('.period-previous').click(function (event) {
        var fromDate =  $('#id_from_date').datetimepicker('getDate'),
            toDate = $('#id_to_date').datetimepicker('getDate'),
            period;
        event.preventDefault();
        event.stopPropagation();
        if (fromDate && toDate) {
            /* NOTE: decrement value in #id_from_date first --- as values are auto-adjusted if from > to */
            if (fromDate.valueOf() === toMonthStart(fromDate).valueOf() &&
                    toDate.valueOf() === incrementMonth(fromDate).valueOf() - 60 * 1000) {
                /* month detected */
                fromDate = decrementMonth(fromDate);
                toDate = new Date(incrementMonth(fromDate).valueOf() - 60 * 1000);
                $('#id_from_date').datetimepicker('setDate', fromDate);
                $('#id_to_date').datetimepicker('setDate', toDate);
            } else {
                /* difference + an extra minute */
                period = toDate - fromDate + 1000 * 60;
                $('#id_from_date').datetimepicker('setDate', new Date(fromDate.valueOf() - period));
                $('#id_to_date').datetimepicker('setDate', new Date(toDate.valueOf() - period));
            }
            $('#period-selection').submit();
        }
    });
    $('.period-next').click(function (event) {
        var fromDate =  $('#id_from_date').datetimepicker('getDate'),
            toDate = $('#id_to_date').datetimepicker('getDate'),
            period;
        event.preventDefault();
        event.stopPropagation();
        if (fromDate && toDate) {
            /* NOTE: increment value in #id_to_date first --- as values are auto-adjusted if from > to */
            if (fromDate.valueOf() === toMonthStart(fromDate).valueOf() &&
                    toDate.valueOf() === incrementMonth(fromDate).valueOf() - 60 * 1000) {
                /* month detected */
                fromDate = incrementMonth(fromDate);
                toDate = new Date(incrementMonth(fromDate).valueOf() - 60 * 1000);
                $('#id_to_date').datetimepicker('setDate', toDate);
                $('#id_from_date').datetimepicker('setDate', fromDate);
            } else {
                /* difference + an extra minute */
                period = toDate - fromDate + 1000 * 60;
                $('#id_to_date').datetimepicker('setDate', new Date(toDate.valueOf() + period));
                $('#id_from_date').datetimepicker('setDate', new Date(fromDate.valueOf() + period));
            }
            $('#period-selection').submit();
        }
    });
    $('#period-apply').click(function (event) {
        event.preventDefault();
        event.stopPropagation();
        $('#period-selection').submit();
    });
    

    $('#id_from_date').datetimepicker({
        timeFormat: 'HH:mm',
        showHour: true,
        showMinute: true,
        showSecond: false,
        addSliderAccess: true,
        sliderAccessArgs: { touchonly: false },
        onClose: function() {
            fromdate_close();
        }
    });
    $('#id_to_date').datetimepicker({
        timeFormat: 'HH:mm',
        showHour: true,
        showMinute: true,
        showSecond: false,
        addSliderAccess: true,
        sliderAccessArgs: { touchonly: false },
        onClose: function() {
            todate_close();
        }
    });
    (function () {
        var now, fromDate, toDate;
        if (!$('#id_from_date').val() && !$('#id_to_date').val()) {
            now = new Date();
            fromDate = toDayStart(now);
            /* add day, subtract minute*/
            toDate = new Date(fromDate.valueOf() + 24 * 60 * 60 * 1000 - 60 * 1000);
            $('#id_from_date').datetimepicker('setDate', fromDate);
            $('#id_to_date').datetimepicker('setDate', toDate);
        }
    }());
});
