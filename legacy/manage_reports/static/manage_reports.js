/*jslint browser: true */
/*global $, jQuery, gettext */


var gridportal = window.gridportal || {};
gridportal.manageReports = gridportal.manageReports || {};


gridportal.manageReports.requestReport = function (data, container, startUrl, finalizeUrl, resultElem, statusUrl, spinnerUrl, progressBar, noticeField) {
    // This function now requires a progressbar.
    // Pass on a <div> container with width and height set
    // to 0 pixels, if a progressbar is unwanted.
    'use strict';

    var requestStatus,
        startSpinner = function () {
            resultElem.html('<img src="' + spinnerUrl + '">');
        },
        stopSpinner = function () {
            resultElem.empty();
        },
        hideNoticeField = function () {
            if (typeof(noticeField) !== 'undefined') {
                noticeField.hide();
            }
        },
        showNoticeField = function () {
            if (typeof(noticeField) !== 'undefined') {
                noticeField.show();
            }
        },
        disableCancel = function () {
            container.find('input, checkbox, button:not(.cancel)').removeAttr('disabled');
            container.find('.cancel').attr('disabled', 'disabled');
        },
        startFail = function (xhr) {
            container.find('.errorlist').remove();
            var errorDict = JSON.parse(xhr.responseText);
            jQuery.each(errorDict, function (key, val) {
                container.find('.reportErrors').append('<ul class="errorlist"><li>' + val[0] + '</li></ul>');
            });
            stopSpinner();
            hideNoticeField();
            disableCancel();
        },
        statusFail = function (jqXHR, textStatus) {
            stopSpinner();
            hideNoticeField();
            if (textStatus === 'timeout') {
                gridportal.website.notify(
                    'error',
                    gettext("Lost contact to the server. Please check your internet connetion."),
                    false);
            } else {
                gridportal.website.notify('error', gettext("Background task failed"), false);
            }
            disableCancel();
        },
        downloadFile = function (data) {
            var link = $('<a href="' + data.url + '"></a>');
            link.text(data.title);
            stopSpinner();
            hideNoticeField();
            disableCancel();
            window.open(data.url, '_blank');
        },
        finalize = function (taskId) {
            jQuery.post(finalizeUrl, {task_id: taskId}).done(downloadFile).fail(statusFail);
            progressBar.progressbar("value", 100);
            container.find('.cancel').attr('disabled', 'disabled');
        },
        running = function (data) {
            var taskId = data.task_id,
                status = data.status,
                result = data.result,
                procent = 0,
                task_id_element = container.find('.task_id');
            if (task_id_element.val() !== taskId) {
                task_id_element.val(taskId);
            }

            progressBar.progressbar({ value: 0 });
            container.find('.errorlist').remove();
            if (taskId) {
                if (status === 'SUCCESS') {
                    progressBar.progressbar("value", 80);
                    finalize(taskId);
                } else if (status === 'PENDING' || status === 'STARTED' ||
                           status === 'RETRY' || (status === 'PROGRESS' && result === undefined)) {
                    container.find('input, checkbox, button:not(.cancel)').attr('disabled', 'disabled');
                    container.find('.cancel').removeAttr('disabled');

                    window.setTimeout(jQuery.proxy(requestStatus, {}, data.task_id), 1000);
                } else if (status === 'PROGRESS') {
                    procent = result.current / result.total * 100 * 0.8;
                    progressBar.progressbar("value", procent);
                    window.setTimeout(jQuery.proxy(requestStatus, {}, data.task_id), 1000);
                } else if (status === 'FAILURE') {
                    statusFail();
                } else if (status === 'REVOKED') {
                    stopSpinner();
                    progressBar.progressbar("destroy");
                    hideNoticeField();
                    disableCancel();
                } else {
                    // unknown status
                    statusFail();
                }
            } else {
                // no task id
                statusFail();
            }
        };
    requestStatus = function (taskId) {
        jQuery.ajax({
            url: statusUrl,
            data: {task_id: taskId},
            type: 'POST',
            timeout: 30000
        }).done(running).fail(statusFail);
    };
    startSpinner();
    showNoticeField();
    jQuery.post(startUrl, data).done(running).fail(startFail);
};
