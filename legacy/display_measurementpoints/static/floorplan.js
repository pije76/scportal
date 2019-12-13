/*jslint browser: true, devel: true */
/*global $, jQuery */
var gridportal = gridportal || {};
gridportal.floorplan = gridportal.floorplan || {};

gridportal.floorplan.show = function (updateUrl) {
    'use strict';
    var floorplan = $('#floorplan');
    floorplan.height(floorplan.find('.map .floorplan-image').height());
    setTimeout(function () {
        gridportal.floorplan.update(updateUrl);
    }, 60 * 1000);
};

gridportal.floorplan.update = function (updateUrl) {
    'use strict';
    jQuery.get(updateUrl, function (data) {
        var floorplan = $('#floorplan');
        $('#floorplan .item').not('.infoitem').each(function () {
            var item = $(this),
                value = data[item.data('id')],
                rendered_value;
            if (value === null) {
                rendered_value = "";
            } else {
                rendered_value = value[0] + ' ' + value[1];
            }
            item.find('.item_value').html(rendered_value);
        });
        setTimeout(function () {
            gridportal.floorplan.update(updateUrl);
        }, 60 * 1000);
    });
};
