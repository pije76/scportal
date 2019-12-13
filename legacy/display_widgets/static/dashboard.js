/*jslint browser: true, devel: true */
/*global $, jQuery, Flotr, gridportal*/

var gridportal = gridportal || {};
gridportal.widgets = gridportal.widgets || {};

gridportal.widgets.dashboard = function (updateUrl, fullscreen) {
    "use strict";
    $('.column').sortable({
        items: 'li',
        connectWith: $('.column'),
        handle: '.widget .header',
        placeholder: 'widget-placeholder',
        forcePlaceholderSize: true,
        revert: 300,
        delay: 100,
        opacity: 0.8,
        scroll: false,
        start: function (e, ui) {
            $(ui.helper).addClass('dragging');
        },
        stop: function (e, ui) {
            var orders = [],
                csrftoken;
            $(ui.item).css({width: ''}).removeClass('dragging');
            $('.column').sortable('enable');
            $('.column').each(function (key, val) {
                var columnName = $(this).attr('id'),
                    widgetCount = 0,
                    newOrder = [];
                $(this).find('.widget').each(function () {
                    newOrder[widgetCount] = $(this).data('id');
                    widgetCount++;
                });
                orders.push({column: columnName, widgets: newOrder});
            });
            jQuery.post(updateUrl, {order: JSON.stringify(orders)}, function (data) {
                if (!data.success && data.statusText) {
                    gridportal.website.notify('error', data.statusText);
                }
            });
        }
    });
    if (!fullscreen) {
        $(".column").sortable("option", "containment", "#dashboard");
    }
};

gridportal.widgets.gauges = [];
gridportal.widgets.drawGauge = function (widget, graph, widgetData) {
    "use strict";
    graph = $(graph);
    var gaugeId = graph.attr('id'),
        canvas,
        colors;
    //If the gauge is already created, we call refresh on it
    if ($(graph).find('.gauge').length > 0) {
        gridportal.widgets.gauges[gaugeId].gauge('setValue', widgetData.last_rate);
    } else {
        canvas = graph.find('canvas')
            .attr('id', gaugeId + 'canvas')
            .addClass('gauge')
            .attr('width', 180)
            .attr('height', graph.height());
        colors = {
            1: [{color: '#008000', from: widgetData.minimum, to: widgetData.low},
                {color: "#FFA500", from: widgetData.low, to: widgetData.high},
                {color: "#ff0000", from: widgetData.high, to: widgetData.maximum}],
            2: [{color: '#ff0000', from: widgetData.minimum, to: widgetData.low},
                {color: "#008000", from: widgetData.low, to: widgetData.high},
                {color: "#ff0000", from: widgetData.high, to: widgetData.maximum}],
            3: [{color: '#FFA500', from: widgetData.minimum, to: widgetData.low},
                {color: "#008000", from: widgetData.low, to: widgetData.high},
                {color: "#FFA500", from: widgetData.high, to: widgetData.maximum}],
            4: [{color: '#ff0000', from: widgetData.minimum, to: widgetData.low},
                {color: "#FFA500", from: widgetData.low, to: widgetData.high},
                {color: "#008000", from: widgetData.high, to: widgetData.maximum}]
        };
        gridportal.widgets.gauges[gaugeId] = canvas
            .gauge({
                min: widgetData.minimum,
                max: widgetData.maximum,
                label: widgetData.unit,
                bands: colors[widgetData.color]
            })
            .gauge('setValue', widgetData.last_rate);
    }
    if (widgetData.last_rate !== null) {
        $(graph).find('.info').show();
        $(graph).find('.offline').remove();
        $(graph).find('.min').html(widgetData.today_min + " " + widgetData.unit);
        $(graph).find('.max').html(widgetData.today_max + " " + widgetData.unit);
        $(graph).find('.avg').html(parseFloat(widgetData.today_avg).toFixed(3) + " " + widgetData.unit);
    } else {
        if (graph.find('.offline').length < 1) {
            $(graph).find('.info').hide();
            $(graph).find('.info').after('<h4 class="offline">Offline</h4>');
        }
    }
};

gridportal.widgets.drawGraph = function (graph) {
    "use strict";
    var widget = $(graph).closest('.widget'),
        spinnerUrl = $('#spinnerUrl').val(),
        statusUrl = $('#statusUrl').val(),
        requestUrl = widget.data("url"),
        jsonResultUrl = $('#jsonResultUrl').val(),
        widget_type = widget.data("type");

    if (widget_type === 0 || widget_type === 3 || widget_type === 2 || widget_type === 4 || widget_type === 5) {
        gridportal.website.startAsyncTask(requestUrl,
            statusUrl, jsonResultUrl, function (graphData) {
                Flotr.draw(graph, graphData.data, graphData.options);
                setTimeout(function () { gridportal.widgets.drawGraph(graph); }, 15 * 60 * 1000);
            }, $(graph), spinnerUrl, false, function () {
                setTimeout(function () { gridportal.widgets.drawGraph(graph); }, 15 * 60 * 1000);
            })();
    } else if (widget.data("type") === 1) {
        gridportal.website.startAsyncTask(requestUrl,
            statusUrl, jsonResultUrl, function (graphData) {
                gridportal.widgets.drawGauge(widget, graph, graphData);
                setTimeout(function () { gridportal.widgets.drawGraph(graph); }, 30 * 1000);
            }, $(graph), spinnerUrl, false, function () {
                setTimeout(function () { gridportal.widgets.drawGraph(graph); }, 30 * 1000);
            })();
    }
};

gridportal.widgets.drawGraphs = function () {
    "use strict";
    gridportal.website.generateGraphs($('.widget-graph'), function (graphs) {
        graphs.each(function () {
            gridportal.widgets.drawGraph(this);
        });
    });
};
