/*jslint browser: true, devel: true */
/*global $, jQuery, gettext, */

var gridportal = gridportal || {};
gridportal.measurementpoints = gridportal.measurementpoints || {};

// What is the purpose of this function. Please document!
gridportal.measurementpoints.formEvents = function () {
    'use strict';
    $('#measurementpoints').on('click', '.add-form', function () {
        var parent = $(this).closest('div'),
            emptyBlock = parent.find('div.empty-form'),
            emptyForm = emptyBlock.children(),
            newForm = emptyForm.clone(),
            totalForms = parent.find('input[name$="TOTAL_FORMS"]'),
            newId = totalForms.val(),
            firstDiv = parent.closest('li').find(':first');

        newForm.find('input, select, textarea').each(function () {
            var input = $(this),
                name = input.attr('name');

            input.attr('name', input.attr('name').replace('__prefix__', newId));
            input.attr('id', input.attr('id').replace('__prefix__', newId));

        });

        totalForms.val(parseInt(totalForms.val(), 10) + 1);
        newForm.insertBefore(emptyBlock);
        newForm.find('select').chosen({enable_split_word_search: true, search_contains: true});
        firstDiv.animate({height: firstDiv.next().height()});
        event.preventDefault();
    });
};
$(function() {
    $('#measurementpoints').on('click', '[name=show_rate]', function () {
        var checkbox = $(this);
        if (!checkbox.is(':checked') && checkbox.closest('form').find('[name=item_id]').length > 0) {
            dialog = $('<div>').attr('id', 'formDialog').html(gettext("Are you sure you want to disable the rate graph?<br>Disabling the rate graph will delete all rate and gauge widgets assosiated with this measurement point!"));
            dialog.dialog({
                title: gettext("Warning"),
                modal: true,
                width: 350,
                buttons: [
                    {
                        text: gettext('Ok'),
                        click: function () {
                            $(this).dialog('close');
                        }
                    },
                    {
                        text: gettext('Cancel'),
                        click: function () {
                            checkbox.prop('checked', true);
                            $(this).dialog('close');
                        }
                    }
                ]
            });
        }
    });
    $('#measurementpoints').on('click', '[name=hidden_on_reports_page]', function () {
        var checkbox = $(this);
        if (checkbox.is(':checked') && checkbox.closest('form').find('[name=used_in_report]').length > 0) {
            dialog = $('<div>').attr('id', 'formDialog').html(gettext("You are not allowed to to hide this measurement point from reports while it is used in a report"));
            dialog.dialog({
                title: gettext("Warning"),
                modal: true,
                width: 350,
                buttons: [
                    {
                        text: gettext('Ok'),
                        click: function () {
                            checkbox.prop('checked', false);
                            $(this).dialog('close');
                        }
                    }
                ]
            });
        }
    });
});
