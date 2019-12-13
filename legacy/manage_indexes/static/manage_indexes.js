/*jslint browser: true, devel: true */
/*global $, jQuery, gettext */

var gridportal = gridportal || {};
gridportal.indexes = gridportal.indexes || {};

gridportal.indexes.setTariff = function (setTariffUrl, setTariffMpListURL) {
    'use strict';
    $('.list-block').on('submit', '.indexlistform', function () {
        var form = $(this),
            dialog,
            buttons,
            message = gettext("This tariff is going to be applyed on the following measurement points:<br>");
        jQuery.post(setTariffMpListURL, form.serialize(), function (data) {
            if (data.measurementpoints.length > 0) {
                jQuery.each(data.measurementpoints, function (key, value) {
                    message += value + "<br>";
                });
                dialog = $('<div>').attr('id', 'formDialog').html(message);
                $('body').append(dialog);
                dialog.dialog({
                    title: gettext("Apply tariff"),
                    modal: true,
                    buttons: [
                        {
                            text: gettext("Ok"),
                            click: function () {
                                var this_dialog = $(this);
                                jQuery.post(setTariffUrl, form.serialize(), function (data) {
                                    if (data.success) {
                                        gridportal.website.notify('success', gettext("The tariff is set"));
                                        form.find('.notice-field').remove();
                                    } else {
                                        form.append($('<div class="notice-field"></div>').html(gettext("The tariff was not set")));
                                    }
                                    this_dialog.dialog('close');
                                });
                            }
                        },
                        {
                            text: gettext("Cancel"),
                            click: function () {
                                $(this).dialog('close');
                            }
                        }
                    ],
                    close: function () {$(this).remove(); },
                    width: 'auto',
                    open: function (event) {
                        dialog = $(event.target).parents(".ui-dialog.ui-widget");
                        buttons = dialog.find(".ui-dialog-buttonpane").find("button");
                        buttons.each(function () {
                            $(this).addClass('btn').removeClass('ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only ui-state-hover');
                        });
                    }
                });
            } else {
                dialog = $('<div>').attr('id', 'formDialog').html(gettext("There's no measurement points of this type without a tariff"));
                $('body').append(dialog);
                dialog.dialog({
                    title: gettext("Apply tariff"),
                    modal: true,
                    buttons: [
                        {
                            text: gettext("Ok"),
                            click: function () {
                                $(this).dialog('close');
                            }
                        }
                    ],
                    close: function () {$(this).remove(); },
                    width: 'auto',
                    open: function (event) {
                        dialog = $(event.target).parents(".ui-dialog.ui-widget");
                        buttons = dialog.find(".ui-dialog-buttonpane").find("button");
                        buttons.each(function () {
                            $(this).addClass('btn').removeClass('ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only ui-state-hover');
                        });
                    }
                });
            }
        });
        return false;
    });
};
