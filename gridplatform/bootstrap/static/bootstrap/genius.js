/*jslint browser: true */
/*global $, jQuery, gettext, pgettext, get_format */

/* Genius Admin Template specific JavaScript */

// Save state of menu whenever menu is shown/hidden or minimized/restored
$(document).ready(function () {
    $('#main-menu-toggle, #main-menu-min').click(function () {
        if ($('#main-menu-toggle').hasClass('open')) {
            jQuery.cookie('main-menu-toggle', 'open', {path: '/'});
        } else if ($('#main-menu-toggle').hasClass('close')) {
            jQuery.cookie('main-menu-toggle', 'close', {path: '/'});
        }

        if ($('#main-menu-min').hasClass('full')) {
            jQuery.cookie('main-menu-min', 'full', {path: '/'});
        } else if ($('#main-menu-min').hasClass('minified')) {
            jQuery.cookie('main-menu-min', 'minified', {path: '/'});
        }
    });

    if (jQuery.cookie('main-menu-toggle') === 'close') {
        // Menu is initially hidden
        $('#main-menu-toggle').removeClass('open').addClass('close');
        $('#content').addClass('full');
        $('.navbar-brand').addClass('noBg');
        $('#sidebar-left').hide();
    }

    if (jQuery.cookie('main-menu-min') === 'minified') {
        // Menu is initially minimized
        $('#main-menu-min').removeClass('full').addClass('minified').find('i').removeClass('fa-angle-double-left').addClass('fa-angle-double-right');

        $('body').addClass('sidebar-minified');
        $('#content').addClass('sidebar-minified');
        $('#sidebar-left').addClass('minified');

        $('.dropmenu > .chevron').removeClass('opened').addClass('closed');
        $('.dropmenu').parent().find('ul').hide();

        $('#sidebar-left > div > ul > li > a > .chevron').removeClass('closed').addClass('opened');
        $('#sidebar-left > div > ul > li > a').addClass('open');
    }

    /* Hack to make dropdowns work in box headers. */
    $('.box-header .dropdown').on('show.bs.dropdown', function () {
        $('.box .box-header').css('overflow', 'visible');
    }).on('hide.bs.dropdown', function () {
        $('.box .box-header').css('overflow', 'hidden');
    });
});
