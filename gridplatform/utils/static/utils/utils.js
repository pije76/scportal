/*jslint browser: true */
/*global $, jQuery, Flotr, gettext, pgettext, get_format, ui */

var utils = window.utils || {};


utils.asyncTask = function (url, parameters) {
    'use strict';
    // NOTE: Cleaning up wrt. old API: Response to initial request should
    // provide status URL and finalize/result URL.
    // (Ideally, status should include finalize URL when done, but with the
    // limited "metadata"-concept with Celery, that would imply writing
    // separate status-views for every task type...)
    // Attach event handlers to Deferred with done(), fail(), progress().
    var deferred = new jQuery.Deferred(),
        handleInitial,
        handleStatus,
        handleError,
        handleSuccess,
        recheckStatus,
        recheckStatusAfterDelay,
        statusUrl,
        finalizeUrl,
        taskId;
    handleInitial = function (data) {
        statusUrl = data.status_url;
        finalizeUrl = data.finalize_url;
        taskId = data.task_id;
        recheckStatusAfterDelay();
    };
    handleStatus = function (data) {
        if (data.status === 'PENDING' || data.status === 'RECEIVED' || data.status === 'STARTED' || data.status === 'RETRY') {
            // Do nothing...?
            // NOTE: "PENDING" means that no worker has observed the task ---
            // but Celery trusts your word in that it's a valid task ID, hence
            // it would be expected to be in a broker input queue.  (Might
            // warrant extra handling; might behave strangely on server
            // restart...)
            recheckStatusAfterDelay();
        } else if (data.status === 'PROGRESS') {
            deferred.notify.apply(this, arguments);
            recheckStatusAfterDelay();
        } else if (data.status === 'SUCCESS') {
            jQuery.post(finalizeUrl, {task_id: taskId}).done(handleSuccess).fail(handleError);
        } else if (data.status === 'FAILURE' || data.status === 'REVOKED') {
            deferred.reject.apply(this, arguments);
        }
    };
    handleError = function () {
        deferred.reject.apply(this, arguments);
    };
    handleSuccess = function () {
        deferred.resolve.apply(this, arguments);
    };
    recheckStatus = function () {
        jQuery.post(statusUrl, {task_id: taskId}).done(handleStatus).fail(handleError);
    };
    recheckStatusAfterDelay = function () {
        window.setTimeout(recheckStatus, 500);
    };
    jQuery.post(url, parameters).done(handleInitial).fail(handleError);
    // Caller should attach event handlers with done(), fail(), progress()...
    return deferred.promise();
};


utils.loadGraph = function (container, url, urlParameters, graphOptions) {
    'use strict';
    var deferred,
        contains_data = false;
    container.html('<p class="text-center"><i class="fa fa-spinner fa-spin"></i></p><p class="text-center graph-progress"></p>');
    deferred = utils.asyncTask(url, urlParameters);
    deferred.done(function (data) {
        container.empty();
        //Hack to prevent Flotr2 from printing NaN% when all values are 0
        if (graphOptions['bars'] === undefined) {
            jQuery.each(data, function(key, value) {
                if (!contains_data) {
                    jQuery.each(this.data[0], function(key, value) {
                        if (value !== 0) {
                            contains_data = true;
                            return false;
                        }
                    });
                } else {
                    return false;
                }
            });
        } else {
            contains_data = true;
        }
        if (contains_data) {
            Flotr.draw(container[0], data, graphOptions);
            $(window).off('resize.graph');
            $(window).on('resize.graph', _.debounce(function () {
                Flotr.draw(container[0], data, graphOptions);
            }, 100));
        } else {
            container.text(gettext('No data for this period'));
        }
    });
    deferred.fail(function () {
        container.html('<p class="text-center"><i class="fa fa-ban"></i></p>');
    });
    deferred.progress(function (data) {
        var result = data.result,
            current,
            total,
            percent;
        if (result) {
            current = result.current;
            total = result.total;
            if (current && total) {
                percent = Math.round(100 * current / total);
                container.find('.graph-progress').text(percent + '%');
            }
        }
    });
};

utils.loadGraphJs = function (container, url, urlParameters, graphOptions) {
    'use strict';
    var deferred,
        contains_data = false,
        canvas = $('<canvas height="400"></canvas>'),
        ctx,
        graphData,
        barChart,
        colors = graphOptions.colors,
        datasets;
    delete graphOptions.colors;
    container.html('<p class="text-center"><i class="fa fa-spinner fa-spin"></i></p><p class="text-center graph-progress"></p>');
    deferred = utils.asyncTask(url, urlParameters);
    deferred.done(function (data) {
        container.empty();
        container.append(canvas);
        ctx = container.find('canvas').get(0).getContext("2d");

        datasets = [
            {
                label: "Baseline",
                backgroundColor: colors[1].fillColor,
                borderColor: colors[1].strokeColor,
                hoverBackgroundColor: colors[1].highlightFill,
                hoverBorderColor: colors[1].highlightStroke,
                data: data.week_selected
            }
        ]
        graphData = {
            labels: data.labels,
            datasets: datasets
        };
        barChart = new Chart(ctx, {type: 'bar', data: graphData, options: graphOptions});
    });
    deferred.fail(function () {
        container.html('<p class="text-center"><i class="fa fa-ban"></i></p>');
    });
    deferred.progress(function (data) {
        var result = data.result,
            current,
            total,
            percent;
        if (result) {
            current = result.current;
            total = result.total;
            if (current && total) {
                percent = Math.round(100 * current / total);
                container.find('.graph-progress').text(percent + '%');
            }
        }
    });
};

utils.genericLoadGraphJs = function (container, url, urlParameters, graphOptions, type) {
    'use strict';
    var deferred,
        contains_data = false,
        canvas = $('<canvas height="400"></canvas>'),
        ctx,
        graphData,
        barChart,
        colors = graphOptions.colors,
        datasets;
    delete graphOptions.colors;
    container.html('<p class="text-center"><i class="fa fa-spinner fa-spin"></i></p><p class="text-center graph-progress"></p>');
    deferred = utils.asyncTask(url, urlParameters);
    deferred.done(function (data) {
        container.empty();
        container.append(canvas);
        ctx = container.find('canvas').get(0).getContext("2d");

        datasets = [
            {
                label: "Forecast",
                backgroundColor: colors[1].fillColor,
                borderColor: colors[1].strokeColor,
                hoverBackgroundColor: colors[1].highlightFill,
                hoverBorderColor: colors[1].highlightStroke,
                data: data.data,
                tension: 0
            }
        ]
        _.forEach(data.set_points, function(setPoint, key) {
                    console.log(key);
            if (key != 9) {
                var setPointPoints = [];
                for (var i = 0; i < data.labels.length; i++) {
                    setPointPoints.push(setPoint);
                }
                datasets.unshift({
                    label: "Set point " + key,
                    backgroundColor: "rgba(220,220,220,0)",
                    radius: 1.2,
                    borderColor: '#000000',
                    data: setPointPoints,
                    tension: 0,
                    pointHoverRadius: 3,
                })
            }
        });

        graphData = {
            labels: data.labels,
            datasets: datasets
        };
        barChart = new Chart(ctx, {type: type, data: graphData, options: graphOptions});
        console.log(barChart);
    });
    deferred.fail(function () {
        container.html('<p class="text-center"><i class="fa fa-ban"></i></p>');
    });
    deferred.progress(function (data) {
        var result = data.result,
            current,
            total,
            percent;
        if (result) {
            current = result.current;
            total = result.total;
            if (current && total) {
                percent = Math.round(100 * current / total);
                container.find('.graph-progress').text(percent + '%');
            }
        }
    });
};

utils.barChart = function (container, form, url, unit, colors, showLegend) {
    'use strict';
    var legend = "";//"<ul class=\"<%=name.toLowerCase()%>-legend\"><% for (var i=0; i<datasets.length; i++){%><li><span style=\"background-color:<%=datasets[i].fillColor%>\"><%if(datasets[i].label){%><%=datasets[i].label%><%}%></span></li><%}%></ul>";
    utils.loadGraphJs(
        container,
        url,
        form.serialize(),
        {
            colors: colors,
            responsive: true,
            maintainAspectRatio: false,
            multiTooltipTemplate:
                "<%if (datasetLabel){%><%=datasetLabel%>: <%}%><%= value %> " + unit,
            legend: {
                display: false
            },
            scales: {

                yAxes: [{
                    ticks: {
                        beginAtZero: true
                    }
                }]
            }

        }
    );
};

utils.lineChart = function (container, form, url, unit, colors, showLegend) {
    'use strict';
    var legend = "";//"<ul class=\"<%=name.toLowerCase()%>-legend\"><% for (var i=0; i<datasets.length; i++){%><li><span style=\"background-color:<%=datasets[i].fillColor%>\"><%if(datasets[i].label){%><%=datasets[i].label%><%}%></span></li><%}%></ul>";
    utils.genericLoadGraphJs(
        container,
        url,
        form.serialize(),
        {
            colors: colors,
            responsive: true,
            maintainAspectRatio: false,
            multiTooltipTemplate:
                "<%if (datasetLabel){%><%=datasetLabel%>: <%}%><%= value %> " + unit,
            legend: {
                display: false
            },
            scales: {

                xAxes: [{
                    type: 'time',
                    time: {
                            displayFormats: {
                                'minute': 'HH:mm:ss'
                            }
							//format: 'MM/DD/YYYY HH:mm'
							// round: 'day'
						}
                }]
            }

        },
        'line'
    );
};

utils.pieChart = function (container, form, url, unit) {
    'use strict';
    utils.loadGraph(
        container,
        url,
        form.serialize(),
        {
            HtmlText: true,
            grid: {
                outline: "",
                verticalLines: false,
                horizontalLines: false
            },
            xaxis: { showLabels: false },
            yaxis: { showLabels: false },
            pie: {
                show: true,
                explode: 0,
                labelFormatter: function (total, value) {
                    if (value * 100 / total >= 2) {
                        return (100 * value / total).toFixed(1)+'%';
                    }
                    return '';
                }
            },
            mouse: {
                track: true,
                relative: true,
                trackFormatter: function (obj) {
                    var roundedPercent = (obj.fraction * 100).toFixed(1);
                    return obj.series.label + ': ' + obj.y + ' ' + unit + ' (' + roundedPercent + '%)';
                }
            },
            legend: {
                position: 'ne',
                backgroundColor: '#FFFFFF',
                labelBoxBorderColor: '#FFFFFF'
            }
        }
    );
};

utils.html = function (container, form, url) {
    'use strict';
    var deferred;
    container.html('<p class="text-center"><i class="fa fa-spinner fa-spin"></i></p>');
    deferred = utils.asyncTask(url, form.serialize());
    deferred.done(function (data) {
        container.html(data);
    });
    deferred.fail(function () {
        container.html('<p class="text-center"><i class="fa fa-ban"></i></p>');
    });
};

utils.hashHelpers = utils.hashHelpers || {};

utils.hashHelpers.updateLocation = function (id, form) {
    'use strict';
    var hashObject = {};
    var formFields = form.find('input[type=text], select');
    hashObject[id] = {};
    formFields.each(function () {
        if (this.id !== "") {
            hashObject[id][this.name] = $(this).val();
        }
    });
    ui.updateLocationHash(hashObject);
};

utils.hashHelpers.setFormValues = function (formValues, form) {
    'use strict';
    if (formValues) {
        $.each(formValues, function(key, value) {
            form.find('[name=' + key + ']').val(value);
        });
        form.find('select').trigger("chosen:updated");
    }
};

utils.hashHelpers.loadFromUrlHash = function (hashId, form, callback) {
    'use strict';
    var formValues = ui.getHashValueFromKey(hashId);

    if (formValues !== "") {
        utils.hashHelpers.setFormValues(formValues, form);
        if (callback) {
            callback();
        }
    } else {
        utils.hashHelpers.updateLocation(hashId, form);
        callback();
    }
};
// Include CSRF token in AJAX requests made via jQuery.  Django CSRF protection
// is described at https://docs.djangoproject.com/en/1.5/ref/contrib/csrf/
// NOTE: Per the HTTP specification, some methods are considered "safe".
// Django does not apply CSRF protection to these.  (Including the header for
// these --- when it is meaningless to the server --- would be misleading...)
$(document).ready(function () {
    'use strict';
    var csrftoken = jQuery.cookie('csrftoken'),
        safeMethods = /^(GET|HEAD|OPTIONS|TRACE)$/;
    jQuery.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function (xhr, settings) {
            if (!safeMethods.test(settings.type)) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            }
        }
    });

    $('.load-chart-line').each(function (index) {
        var container = $(this),
            form = $(container.data('form')),
            url = container.data('url'),
            unit = container.data('unit'),
            hashId = 'barchart' + index,
            color = container.data('color'),
            colors = [];

        if (color === undefined || color === 'normal') {
            colors = [
                {
                    fillColor: "rgba(151,187,205,0.5)",
                    strokeColor: "rgba(151,187,205,0.8)",
                    highlightFill: "rgba(151,187,205,0.75)",
                    highlightStroke: "rgba(151,187,205,1)",
                },
                {
                    fillColor: "#dce5a9",
                    strokeColor: "#92c36c",
                    highlightFill: "#92c36c",
                    highlightStroke: "#4c8b4b",
                }
            ]
        } else if (color === 'cost') {
            colors = [
                {
                    fillColor: "#9e67ab",
                    strokeColor: "#662c91",
                    highlightFill: "#662c91",
                    highlightStroke: "#4a2069",
                },
                {
                    fillColor: "#d77fb4",
                    strokeColor: "#b43894",
                    highlightFill: "#b43894",
                    highlightStroke: "#97307c",
                }
            ]

        }

        utils.hashHelpers.loadFromUrlHash(hashId, form, function () {
            utils.lineChart(container, form, url, unit, colors);

        });

        form.find('button').click(function (event) {
            event.preventDefault();
            utils.hashHelpers.updateLocation(hashId, form);
            utils.lineChart(container, form, url, unit, colors);
        });

    });

    $('.load-chart-bar').each(function (index) {
        var container = $(this),
            form = $(container.data('form')),
            url = container.data('url'),
            unit = container.data('unit'),
            hashId = 'barchart' + index,
            color = container.data('color'),
            colors = [],
            showLegend = container.data('show-legend') === "true" ? true : false;

        if (color === undefined || color === 'normal') {
            colors = [
                {
                    fillColor: "rgba(151,187,205,0.5)",
                    strokeColor: "rgba(151,187,205,0.8)",
                    highlightFill: "rgba(151,187,205,0.75)",
                    highlightStroke: "rgba(151,187,205,1)",
                },
                {
                    fillColor: "#dce5a9",
                    strokeColor: "#92c36c",
                    highlightFill: "#92c36c",
                    highlightStroke: "#4c8b4b",
                }
            ]
        } else if (color === 'cost') {
            colors = [
                {
                    fillColor: "#9e67ab",
                    strokeColor: "#662c91",
                    highlightFill: "#662c91",
                    highlightStroke: "#4a2069",
                },
                {
                    fillColor: "#d77fb4",
                    strokeColor: "#b43894",
                    highlightFill: "#b43894",
                    highlightStroke: "#97307c",
                }
            ]

        }

        utils.hashHelpers.loadFromUrlHash(hashId, form, function () {
            utils.barChart(container, form, url, unit, colors);

        });

        form.find('button').click(function (event) {
            event.preventDefault();
            utils.hashHelpers.updateLocation(hashId, form);
            utils.barChart(container, form, url, unit, colors, showLegend);
        });

    });

    $('.load-chart-pie').each(function (index) {
        var container = $(this),
            form = $(container.data('form')),
            url = container.data('url'),
            unit = container.data('unit'),
            hashId = 'piechart' + index;

        utils.hashHelpers.loadFromUrlHash(hashId, form, function () {
            utils.pieChart(container, form, url, unit);

        });

        form.find('button').click(function (event) {
            event.preventDefault();
            utils.hashHelpers.updateLocation(hashId, form);
            utils.pieChart(container, form, url, unit);
        });

    });

    $('.load-html').each(function (index) {
        var container = $(this),
            form = $(container.data('form')),
            url = container.data('url'),
            hashId = 'html' + index;

        utils.hashHelpers.loadFromUrlHash(hashId, form, function () {
            utils.html(container, form, url);
        });

        form.find('button').click(function (event) {
            event.preventDefault();
            utils.hashHelpers.updateLocation(hashId, form);
            utils.html(container, form, url);
        });
    });
});
