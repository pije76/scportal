/*jslint browser: true, devel: true */
/*global $, jQuery, gettext, pgettext, get_format, noty */

var gridportal = gridportal || {};
gridportal.website = gridportal.website || {};

// http://blogs.msdn.com/b/ie/archive/2010/09/03/same-markup-using-canvas-audio-and-video.aspx
gridportal.website.isCanvasSupported = !!window.HTMLCanvasElement;
gridportal.website.generateGraphs = function (graphs, callback) {
    'use strict';
    if (gridportal.website.isCanvasSupported) {
        if (callback !== undefined) {
            callback(graphs);
        }
    } else {
        graphs.html(gettext("Can't display graph, please upgrade your browser"));
    }
};


gridportal.website.notify = function (type, msg, timeout) {
    'use strict';
    var timeout_time = 3000;
    if (typeof(timeout) != 'undefined') {
        timeout_time = timeout;
    }

    noty({
        text: msg,
        type: type,
        dismissQueue: true,
        theme: 'gridmanager',
        layout: 'topCenter',
        timeout: timeout_time
    });
};

// Set up open/close animation for the settings menu.
gridportal.website.slideSettings = function () {
    'use strict';
    var slide = $('#settings-menu .slide'),
        sideId = $('body').attr('id');
    if (sideId === 'devices-page' ||
            sideId === 'locations-page' ||
            sideId === 'groups-page' ||
            sideId === 'mps-page' ||
            sideId === 'indexsettings-page' ||
            sideId === 'rules-page' ||
            sideId === 'users-page' ||
            sideId === 'userprofile-page') {
        slide.addClass('active');
    }
    slide.find('.settings-btn').click(function () {
        // when "active", the settings slider is open/visible

        if (slide.hasClass('active')) {
            // hide by sliding out
            slide.animate({top: '-67px'}, function () {
                // "cleanup"; use the class, remove explicit pixel value used
                // for animation
                slide.removeClass('active');
                slide.css('top', '');
            });
        } else {
            // show by sliding in
            slide.animate({top: '0px'}, function () {
                // "cleanup"; use the class, remove explicit pixel value used
                // for animation
                slide.addClass('active');
                slide.css('top', '');
            });
        }
        return false;
    });
};


gridportal.website.initInpageMenu = function (openIcon, closeIcon) {
    'use strict';
    var inpageMenu = $('.in-page-menu'),
        contentWidth,
        menuWidth;
    inpageMenu.find('.scroller').mCustomScrollbar({
        theme: 'dark',
        scrollButtons: {
            enable: true
        },
        advanced: {
            updateOnBrowserResize: true,
            updateOnContentResize: true
        }
    });

    contentWidth = $('.in-page-menu .scroller').width();
    menuWidth = parseInt(contentWidth, 10) + 2;


    $('#content-main').css('min-height', inpageMenu.height() + 'px');

    if (contentWidth > 900) {
        menuWidth = 922;
        $('.in-page-menu .menu-content').css({
            'overflow-x': 'scroll',
            width: '900px'
        });
    }

    $('.in-page-menu').css({left: '-' + menuWidth + 'px'});

    $('.in-page-menu .menu-btn').click(function () {
        var menu = $(this).closest('.in-page-menu'),
            menuImg = $(this).find('img');

        if (menu.hasClass('open')) {
            contentWidth = $('.in-page-menu .scroller').width();
            menuWidth = parseInt(contentWidth, 10) + 2;
            menu.removeClass('open');
            menuImg.attr('src', openIcon);
            menu.animate({left: '-' + menuWidth + 'px'});
        } else {
            contentWidth = $('.in-page-menu .scroller').width();
            menuWidth = parseInt(contentWidth, 10) + 12;
            menu.addClass('open');
            menuImg.attr('src', closeIcon);
            menu.animate({left: '-2px'});
        }
    });
};

// Error handler for ajax requests --- show noty-notification with error message reported by browser.
// NOTE: Must be explicitly bound to the error callbacks; i.e. not implicitly used.
// NOTE: The error message from the browser (textStatus) might not be all that useful; consider removing it again...
gridportal.website.ajaxError = function (jqXHR, textStatus) {
    'use strict';
    var status = jqXHR.status,
        errorType;
    if (500 <= status && status < 600) {
        // server error
        errorType = gettext('Server error.');
    } else if (400 <= status && status < 500) {
        // client error
        errorType = gettext('Error.');
    } else {
        // no connection to server?
        errorType = gettext('Could not contact server.');
    }
    gridportal.website.notify('error', errorType + ' (' + textStatus + ')');
};


gridportal.website.overlay = {};

gridportal.website.overlay.placement = function (listItem, form) {
    'use strict';
    var listItemPosition = listItem.position(),
        initialLeft = listItem.closest('.content-element').width(),
        left = listItemPosition.left,
        top = listItemPosition.top;

    listItem.css({overflow: 'hidden'});
    form.css({
        left: initialLeft,
        top: top,
        position: 'absolute',
        width: listItem.width()
    });
    form.insertAfter(listItem);

    return {
        height: form.height(),
        left: left
    };
};


// Insert overlay, make it cover content as overlay with slide-in animation
gridportal.website.overlay.slidein = function (content, overlay) {
    'use strict';
    var li = content.closest('li'),
        deleteBtn = overlay.find('.delete'),
        height;
    overlay.css({
        position: 'absolute',
        left: $('#content-main').width(),
        top: content.position().top,
        width: content.width()
    });
    overlay.insertAfter(content);
    deleteBtn.each(function () {
        var btn = $(this);
        btn.tooltip({
            content: btn.data('reason')
        });
    });
    overlay.find('select').chosen({enable_split_word_search: true, search_contains: true});

    $('input[type=submit], button').click(function () {
        overlay.find('.overlay-header .right').prepend('<img src="' + $('.list-block').data('spinner') + '" class="list-spinner">');
    });
    height = overlay.height();

    if (height < content.height()) {
        height = content.height();
        overlay.css({height: height});
    }
    overlay.find('.image a').fancybox({type: 'image'});
    overlay.find('.date').datepicker();

    overlay.find('.datetime').datetimepicker({
        timeFormat: 'HH:mm:ss',
        addSliderAccess: true,
        sliderAccessArgs: { touchonly: false }
    });
    overlay.find('select').on('change', function () {
        content.animate({height: overlay.height()});
    });
    content.animate({height: height});
    overlay.animate({left: content.position().left}, function () {
        li.css('overflow', 'visible');
        li.parents('li').css('overflow', 'visible');
    });

};


// Slide overlay out and readjust content height to its "natural" height.
// Remove the parent li after the animation if "remove" is specified.
// ("Remove" is used when adding a list item is cancelled, i.e. the newly
// inserted element should be completely removed rather than reverted to some
// previous state.)
gridportal.website.overlay.slideout = function (content, overlay, remove) {
    'use strict';
    // Check the required height of the content by making a copy with
    // "automatic" height, inserting that in the DOM inside the same li as the
    // content, measuring it and removing the copy again.
    var li = content.closest('li'),
        copy = content.clone().css('height', '').appendTo(li),
        height = copy.height();
    copy.remove();
    li.css('overflow', 'hidden');
    li.parents('li').css('overflow', 'hidden');
    content.animate({height: height}, function () {
        content.css('height', '');
    });
    overlay.animate({left: content.width()}, function () {
        overlay.remove();
        if (remove) {
            li.remove();
        }
    });
};


// Open/slide in a form to edit a specific list-item entry.
// The original contents (to be hidden) must be inside an element with class
// "list-item", and that element should have the url to fetch the form in its
// "url" data property.  (data-url attribute or otherwise accessible to jQuerys
// .data())
// NOTE: To be bound to the "open" button/elemen.
gridportal.website.overlay.open = function (event) {
    'use strict';
    var listItem = $(this).closest('li'),
        content = $(this).closest('li > div'),
        overlayUrl = content.data('url'),
        dialog;
    // When executing this open method, and the listitem already has
    // isOpen class set, stop doing anything; let the slide-in method
    // do it's job.
    if (listItem.hasClass('isOpen')) {
        return;
    }

    // If another form is open, warn the user about this
    if ($('.isOpen').length > 0) {
        dialog = $('<div>').attr('id', 'formDialog').html(gettext("Another form is currently open.<br> Do you want to discard this?"));
        dialog.dialog({
            title: gettext("Information"),
            modal: true,
            width: 350,
            buttons: [
                {
                    text: gettext('Discard'),
                    click: function () {
                        // Sliding out previous form
                        var li = $('.isOpen'),
                            previousContent = li.children('div').first(),
                            previousOverlay = li.find('div:nth-child(2)');

                        if (li.hasClass('new')) {
                            gridportal.website.overlay.slideout(previousContent, previousOverlay, true);
                        } else {
                            gridportal.website.overlay.slideout(previousContent, previousOverlay, content.html() === '');
                            li.removeClass('isOpen');
                        }

                        // Now sliding in desired form
                        jQuery.get(overlayUrl).success(function (data) {
                            gridportal.website.overlay.slidein(content, $(data));
                        }).error(gridportal.website.ajaxError);
                        listItem.addClass('isOpen');

                        $(this).dialog('close');
                    }
                },
                {
                    text: gettext('Jump to form'),
                    click: function () {
                        $('html, body').animate({
                            scrollTop: $(".isOpen").offset().top
                        }, 100);

                        $(this).dialog('close');
                    }
                },
                {
                    text: gettext('Abort'),
                    click: function () {
                        $(this).dialog('close');
                    }
                }
            ]
        });
    } else {
        jQuery.get(overlayUrl).success(function (data) {
            gridportal.website.overlay.slidein(content, $(data));
        }).error(gridportal.website.ajaxError);
        listItem.addClass('isOpen');
    }
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
};


// Close/slide out an edit form.  The "original" content should be the first
// div under the parent li, while the form to slide out should be the div
// containing the element triggering the event...  If the "original" content is
// empty (i.e. a div with no children or text inside), we also remove the li.
// (... that should normally be the case when "cancel" adding a new item ---
// but in any concievably other case where we have no actual content, not
// displaying that particular lack of content should be fine.)
// NOTE: To be bound to the "close" button/elemen.
gridportal.website.overlay.close = function (event) {
    'use strict';
    var li = $(this).closest('li'),
        content = li.children('div').first(),
        overlay = $(this).closest('li > div');

    gridportal.website.overlay.slideout(content, overlay, content.html() === '');
    li.removeClass('isOpen');
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
};


// Special case of overlay.open for new objects; adds list item to list
// element, sets special case close to remove the list item if closed without
// saving.
// NOTE: Not reusing gridportal.website.overlay.open --- that would entail
// adding the li to the DOM before the ajax-call --- or adding extra complexity
// to that function...
gridportal.website.overlay.openNew = function (list, url, callback) {
    'use strict';
    if ($('.isOpen').length > 0) {
        var dialog = $('<div>').attr('id', 'formDialog').html(gettext("Another form is currently open.<br> Do you want to discard this?"));
        dialog.dialog({
            title: gettext("Information"),
            modal: true,
            width: 350,
            buttons: [
                {
                    text: gettext('Discard'),
                    click: function () {
                        // Sliding out previous form
                        var li = $('.isOpen'),
                            previousContent = li.children('div').first(),
                            previousOverlay = li.find('div:nth-child(2)');

                        if (li.hasClass('new')) {
                            gridportal.website.overlay.slideout(previousContent, previousOverlay, true);
                        } else {
                            gridportal.website.overlay.slideout(previousContent, previousOverlay, false);
                            li.removeClass('isOpen');
                        }

                        // Now sliding in desired form
                        gridportal.website.overlay.doOpenNew(list, url, callback);

                        $(this).dialog('close');
                    }
                },
                {
                    text: gettext('Jump to form'),
                    click: function () {
                        $('html, body').animate({
                            scrollTop: $(".isOpen").offset().top
                        }, 100);

                        $(this).dialog('close');
                    }
                },
                {
                    text: gettext('Abort'),
                    click: function () {
                        $(this).dialog('close');
                    }
                }
            ]
        });
    } else {
        gridportal.website.overlay.doOpenNew(list, url, callback);
    }
};


gridportal.website.overlay.doOpenNew = function (list, url, callback) {
    'use strict';
    jQuery.get(url).success(function (data, textStatus, jqXHR) {
        // check content-type --- on wizards, all pages return JSON; on simple
        // forms, the initial form is plain html
        var contentType = jqXHR.getResponseHeader('Content-Type'),
            isHtml = contentType.indexOf('text/html') !== -1,
            html = isHtml ? $(data) : $(data.html),
            li = $('<li class="new isOpen"></li>'),
            content = $('<div></div>').appendTo(li);
        li.prependTo(list);
        gridportal.website.overlay.slidein(content, html);
        if (callback) {
            callback(li);
        }
    }).error(gridportal.website.ajaxError);
};


// Special case of overlay.close for new objects; removes the list item.  (To
// be used for close without saving.)  Returns false, so that, when used as an
// event handler, the event is not propagated --- useful when the event would
// otherwise propagate to the "common-case" close() function.
gridportal.website.overlay.closeNew = function (event) {
    'use strict';
    var li = $(this).closest('li'),
        content = li.children('div').first(),
        overlay = $(this).closest('li > div');
    gridportal.website.overlay.slideout(content, overlay, true);
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    return false;
};


// Error handler for overlay submit
gridportal.website.overlay.removeSpinnerajaxError = function (jqXHR, textStatus) {
    'use strict';
    var spinner = $('.list-spinner'),
        header = spinner.parent();
    gridportal.website.ajaxError(jqXHR, textStatus);
    spinner.remove();
    header.find('.error').remove();
    header.prepend('<span class="error">'+ gettext('An error accurred while saving. Please try again.') + '</span>');
    header.find('input[type=submit]').removeAttr('disabled');
};


// Submit handler for overlay/inline forms.
//
// URL from action attribute of form.
//
// Expects JSON dictionary with entries success, statusText, html from
// back-end.  "success" should be true and "statusText" set to something
// appropriate to display on successful save.  "html" should contain the
// rendered non-form data element on success; rendered form with errors on
// failure.  Callback can be used to modify the resulting html to insert ---
// should normally not be specified.
//
// The area that will be replaced with the "html" given to us on both failure
// and success must have the class "slide-in-overlay".
gridportal.website.overlay.submit = function (event, callback) {
    'use strict';
    event.preventDefault();
    var form = $(this),
        form_data,
        content_type,
        request;
    form.find("input[type=submit]").attr("disabled", "disabled");
    function successHandler(data, statusText, jqXHR) {
        //check content-type --- we have multi-page creation (measuring
        //points/...) where the first page is a POST returning a HTML form...
        var contentType = jqXHR.getResponseHeader('Content-Type'),
            isHtml = contentType.indexOf('text/html') !== -1,
            html = isHtml ? $(data) : $(data.html),
            li = form.closest('li'),
            content = li.children('div').first(),
            overlay = form.closest('.slide-in-overlay'),
            list,
            searchField;
        if (callback) {
            callback.call(html);
        }
        if (!data.success) {
            overlay = html.css({
                position: overlay.css('position'),
                left: overlay.css('left'),
                top: overlay.css('top'),
                width: overlay.css('width')
            }).replaceAll(overlay);

            noty({
                text: data.statusText,
                type: 'error',
                dismissQueue: true,
                theme: 'gridmanager',
                layout: 'topCenter',
                timeout: 3000
            });

            $('select').not('.empty-form select').chosen({enable_split_word_search: true, search_contains: true});
            $('select').on('change', function () {
                content.animate({height: overlay.height()});
            });
            content.animate({height: overlay.height()});
            overlay.find('input[type=submit], button').click(function () {
                overlay.find('.overlay-header .right').prepend('<img src="' + $('.list-block').data('spinner') + '" class="list-spinner">');
            });
        } else {
            // success...
            content = html.css({
                height: content.css('height')
            }).replaceAll(content);
            list = li.closest('.list-block');
            searchField = list.find('input[name=search]');

            // tree structured data --- item has a "parent", and we're not in
            // search mode...
            if (data.parent !== undefined && searchField.filter('.labelinside').size() > 0) {
                (function () {
                    var parent,
                        parentLi,
                        ul;
                    if (data.parent > 0) {
                        parent = list.find('div[data-id=' + data.parent + ']');
                        parentLi = parent.closest('li');
                        ul = parentLi.children('ul');
                        if (!ul.size()) {
                            ul = $('<ul></ul>').appendTo(parentLi);
                        }
                        li.appendTo(ul);
                    }
                }());
            }
            gridportal.website.overlay.close.call(overlay);
            noty({
                text: data.statusText,
                type: 'success',
                dismissQueue: true,
                theme: 'gridmanager',
                layout: 'topCenter',
                timeout: 3000
            });
        }
    }
    if (form.find('input[type=file]').length > 0) {
        // Setting contentType option to false,
        // forcing jQuery not to add a Content-Type header,
        // otherwise, the boundary string will be missing from it.
        form_data = new FormData(form[0]);
        content_type = false;
    } else {
        form_data = form.serialize();
        content_type = "application/x-www-form-urlencoded";
    }
    request = jQuery.ajax({
        url: form.attr('action'),
        type: "POST",
        data: form_data,
        contentType: content_type,
        processData: false,
        success: successHandler,
        error: gridportal.website.overlay.removeSpinnerajaxError
    });
};

gridportal.website.deleteItem = function (event) {
    'use strict';
    var deleteBtn = $(this),
        self = this,
        btns = {},
        url = deleteBtn.data('deleteurl'),
        dialog;
    event.preventDefault();
    if (!deleteBtn.data('reason')) {
        dialog = $('<div>').attr('id', 'formDialog').html(gettext("Are you sure you want to delete?"));
        $('body').append(dialog);
        dialog.find(':submit').hide();
        btns[gettext('Ok')] = function () {
            jQuery.getJSON(url, {pk: deleteBtn.closest('form').find('[name=item_id]').val()}, function (data) {
                gridportal.website.overlay.closeNew.call(self);
                noty({
                    text: data.statusText,
                    type: 'success',
                    dismissQueue: true,
                    theme: 'gridmanager',
                    layout: 'topCenter',
                    timeout: 3000
                });
            });
            $(this).dialog('close');
        };
        btns[gettext('Cancel')] = function () {
            $(this).dialog('close');
            $('.list-spinner').remove();
        };
        dialog.dialog({
            title: gettext("Delete"),
            modal: true,
            buttons: btns,
            close: function () {$(this).remove(); },
            width: 'auto',
            open: function (event, ui) {
                var dialog = $(event.target).parents(".ui-dialog.ui-widget"),
                    buttons = dialog.find(".ui-dialog-buttonpane").find("button");
                buttons.each(function () {
                    $(this).addClass('btn').removeClass('ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only ui-state-hover');
                });
            }
        });
    } else {
        dialog = $('<div>').attr('id', 'formDialog').html(deleteBtn.data("reason"));
        $('body').append(dialog);
        dialog.find(':submit').hide();
        dialog.dialog({
            title: gettext("Delete"),
            modal: true,
            buttons: {
                'Ok': function () {
                    $(this).dialog('close');
                }
            },
            close: function () {$(this).remove();
                    $('.list-spinner').remove();},
            width: 'auto',
            open: function (event, ui) {
                var dialog = $(event.target).parents(".ui-dialog.ui-widget"),
                    buttons = dialog.find(".ui-dialog-buttonpane").find("button");
                // TOOD: fix, as for the other one...
                buttons.each(function () {
                    $(this).addClass('btn').removeClass('ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only ui-state-hover');
                });
            }
        });
    }
};


// Show delete dialog, and if user clicks OK, send a synchroneous POST of the
// specified pk to the url.
// csrftoken should be HTML for CSRF form hidden field --- what we get from {%
// csrf_token %} in a Django template.
// (This constructs a form, and then submits it, not using AJAX.)
gridportal.website.synchroneousDelete = function (url, pk, redirectUrl) {
    'use strict';
    var deleteBtn = $('input[name=delete]'), dialog, buttons, message;
    if (!deleteBtn.data('message')){
        message = gettext("Are you sure you want to delete this?");
    } else {
        message = deleteBtn.data('message');
    }

    if (!deleteBtn.data('reason')) {
        $('<div></div>').text(message).dialog({
            title: gettext("Delete"),
            modal: true,
            buttons: [
                {
                    text: gettext("Ok"),
                    click: function () {
                        $.post(url, {pk: pk, csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()}, function () {
                            document.location = redirectUrl;
                        });
                        $(this).dialog('close');
                    }
                },
                {
                    text: gettext("Cancel"),
                    click: function () {
                        $(this).dialog('close');
                    }
                }
            ],
            close: function () {
                $(this).remove();
            },
            open: function (event) {
                dialog = $(event.target).closest(".ui-dialog.ui-widget");
                dialog.find(".ui-dialog-buttonpane button").each(function () {
                    $(this).addClass('btn').removeClass('ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only ui-state-hover');
                });
            },
            width: 'auto'
        });
    } else {
        dialog = $('<div>').attr('id', 'formDialog').html(deleteBtn.data("reason"));
        $('body').append(dialog);
        dialog.find(':submit').hide();
        dialog.dialog({
            title: gettext("Delete"),
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
                // TOOD: fix, as for the other one...
                buttons.each(function () {
                    $(this).addClass('btn').removeClass('ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only ui-state-hover');
                });
            }
        });
    }
};



// Set up object list with GridPortal UI conventions --- query server with sort
// from sort buttons, filtering from search field; display pagination buttons.
//
// @param list: Some <div> containing the following:
//
//   - <ul>: The list into which the loaded objects will be inserted as
//     <li></li> elements.
//
//   - Elements with "data-sort" attributes.  The attribute value must be valid
//     as request.GET["order"] in the view.  These elements will be
//     instrumented with on-click behavior that causes the ordering to change
//     to the column identified by the attribute value of "data-sort".
//     Repeating a click on the same element will toggle between ascending and
//     descending ordering.  This is conveyed to the view through
//     request.GET["direction"] which will be either "asc" or "desc".
//
//   - <input> elements with name="search": These elements will be instrumented
//     with a behaviour that causes the entire list to be reloaded with
//     request.GET["search"] set to the value of the input field whenever it is
//     modified (after a reasonable time of staling).
//
// @param baseUrl: The full URL to the view that will render the JSON response.
//
// @resultsPerPage: The number of results pr page.  This corresponds to
// request.GET["count"].
//
// @orderBy: A string corresponding to the request.GET["order"] in the view
//
// @param callback: A function called when JSON response is received.
gridportal.website.gmList = function (list, baseUrl, resultsPerPage, orderBy, callback) {
    "use strict";
    var sortButtons = list.find("[data-sort]"),
        searchField = list.find("input[name=search]"),
        ul = list.find("ul"),
        loaderIcon = list.find(".loader"),
        paginator = list.find(".paginator"),
        orderDirection = "asc",
        search = "",
        getData,
        renderPaginator,
        renderItems,
        searchTimeout;

    orderBy = orderBy || "";
    list.find("[data-sort=" + orderBy + "]").addClass('active');

    // Search field settings
    searchField.labelify({labelledClass: "labelinside"});
    list.find(".clear-search-btn").css('left', searchField.width() + 35);
    list.find(".loader").css('left', searchField.width() + 35);

    renderPaginator = function (paginator, pageCount, currentPage) {
        var i, btn;
        paginator.empty();
        for (i = 0; i < pageCount; i += 1) {
            btn = $('<span class="page-button"></span>').text(i + 1).data('page', i);
            if (i === currentPage) {
                btn.addClass('active');
            }
            btn.appendTo(paginator);
        }
        paginator.find('.page-button').click(function () {
            var page = $(this).data('page');
            getData(page);
            // Scroll to the list top
            $.scrollTo(list.prev(), 400);
        });
    };

    renderItems = function (ul, data) {
        ul.empty();
        $.each(data, function (id, item) {
            $('<li></li>').append(item).appendTo(ul);
        });
    };

    getData = function (page) {
        loaderIcon.show();
        var getParams = {
            order: orderBy,
            direction: orderDirection,
            count: resultsPerPage,
            offset: page * resultsPerPage,
            search: search
        };
        jQuery.getJSON(baseUrl, getParams).success(function (response) {
            var pageCount = Math.ceil(response.total / resultsPerPage);
            renderItems(ul, response.data);
            if (callback) {
                callback();
            }
            renderPaginator(paginator, pageCount, page);
            loaderIcon.hide();
        }).error(gridportal.website.ajaxError);
    };

    searchField.on('keydown keyup change cut paste input', function () {
        var field = $(this);
        if (searchTimeout !== undefined) {
            window.clearTimeout(searchTimeout);
        }
        searchTimeout = window.setTimeout(function () {
            var val = field.val();
            if (field.hasClass('labelinside')) {
                val = '';
            }
            // don't trigger request/anything on e.g. releasing the shift key
            if (val !== search) {
                search = val;
                if (search.length > 0) {
                    list.find('.clear-search-btn').fadeIn(300);
                } else {
                    list.find('.clear-search-btn').fadeOut(300);
                }
                getData(0);
            }
        }, 200);
    });

    list.find('.clear-search-btn').click(function () {
        searchField.val('');
        // let labelify do its thing
        searchField.trigger('blur');
        // search/reset by triggering the normal change event handler
        searchField.trigger('change');
    });

    sortButtons.click(function (event) {
        var btn = $(this),
            column = btn.data('sort');
        sortButtons.not(btn).removeClass('active');
        btn.addClass('active');
        if (orderBy === column) {
            if (orderDirection === "asc") {
                orderDirection = "desc";
            } else {
                orderDirection = "asc";
            }
        } else {
            orderBy = column;
            orderDirection = "asc";
        }
        getData(0);
    });

    getData(0);
};



(function () {
    'use strict';
    if (!jQuery.datepicker) {
	return;
    }

    var pythonFormat = get_format('SHORT_DATE_FORMAT'),
        jsFormat = '',
        i,
        c,
        // Python/Django format to jQuery Datepicker format: d, j, m, n, Y, y -> dd, d, mm, m, yy, y
        // 'dd' is two-digit day, 'mm' is two-digit month, 'y' is two-digit year while 'yy' is four-digit year --- WTF?
        mapping = {
            d: 'dd',
            j: 'd',
            m: 'mm',
            n: 'm',
            Y: 'yy',
            y: 'y'
        },
        capitalize = function (str) {
            return str.charAt(0).toUpperCase() + str.substring(1);
        },
        regional = jQuery.datepicker.regional[''];
    for (i = 0; i < pythonFormat.length; i += 1) {
        c = pythonFormat.charAt(i);
        if (mapping[c]) {
            jsFormat += mapping[c];
        } else {
            jsFormat += c;
        }
    }
    regional.closeText = gettext('Done');
    regional.prevText = gettext('Prev');
    regional.nextText = gettext('Next');
    regional.currentText = gettext('Today');
    regional.monthNames = [
        capitalize(gettext('January')),
        capitalize(gettext('February')),
        capitalize(gettext('March')),
        capitalize(gettext('April')),
        capitalize(gettext('May')),
        capitalize(gettext('June')),
        capitalize(gettext('July')),
        capitalize(gettext('August')),
        capitalize(gettext('September')),
        capitalize(gettext('October')),
        capitalize(gettext('November')),
        capitalize(gettext('December'))
    ];
    regional.monthNamesShort = [
        capitalize(gettext('jan')),
        capitalize(gettext('feb')),
        capitalize(gettext('mar')),
        capitalize(gettext('apr')),
        capitalize(gettext('may')),
        capitalize(gettext('jun')),
        capitalize(gettext('jul')),
        capitalize(gettext('aug')),
        capitalize(gettext('sep')),
        capitalize(gettext('oct')),
        capitalize(gettext('nov')),
        capitalize(gettext('dec'))
    ];
    regional.dayNames = [
        gettext('Sunday'),
        gettext('Monday'),
        gettext('Tuesday'),
        gettext('Wednesday'),
        gettext('Thursday'),
        gettext('Friday'),
        gettext('Saturday'),
        gettext('Sunday')
    ];
    regional.dayNamesShort = [
        gettext('Sun'),
        gettext('Mon'),
        gettext('Tue'),
        gettext('Wed'),
        gettext('Thu'),
        gettext('Fri'),
        gettext('Sat'),
        gettext('Sun')
    ];
    regional.daysNamesMin = [
        pgettext('weekday', 'Su'),
        pgettext('weekday', 'Mo'),
        pgettext('weekday', 'Tu'),
        pgettext('weekday', 'We'),
        pgettext('weekday', 'Th'),
        pgettext('weekday', 'Fr'),
        pgettext('weekday', 'Sa'),
        pgettext('weekday', 'Su')
    ];
    regional.weekHeader = pgettext('week-header', 'Wk');
    //regional.dateFormat = jsFormat;
    regional.dateFormat = 'yy-mm-dd';
    regional.firstDay = parseInt(get_format('FIRST_DAY_OF_WEEK'), 10);
    jQuery.datepicker.setDefaults(jQuery.datepicker.regional[""]);
}());

// It is not necessary to explicitly call Javascript directly in the Django
// templates.  It is enough to instrument HTML elements with proper classes and
// attributes.
//
// Usage::
//
//     <div class="list-block"
//          data-url="http://get-me-some-json-list-of-objects/"
//          data-showcount="15"
//          data-orderby="order-by-this-colum-name">
//       <span data-sort="name">Name</span>
//       <span data-sort="location">Location</span>
//       <input type="text" name="search">
//       <span class="clear-search-btn">Clear search</span>
//       <img src="http://some-awesome-loader-icon.png" class="loader">
//       <ul class="model-tree"></ul>
//       <div class="paginator"></div>
//     </div>
//
// The <ul> will be populated by the response from data-url in the list-block
// <div>.  data-showcount models will be shown pr page.  They will be ordered
// by data-orderby by default, but this is changed by clicking one of the
// data-sort <span>s.  The shown models may be filtered by entering text into
// the search <input>.  The filter is disabled by clicking the clear-search-btn
// <span>.  While models are being loaded the loader <img> is visible, and when
// models have been loaded, the loader <img> is hidden again.  The paginator
// <div> provides means to browse through the filtered and sorted pages of
// models.
//
// @see: L{@json_list_response} decorator and L{gmList()} for details on how to
// implement the corresponding view.
$(function () {
    "use strict";
    // Instruct elements with class="open", or class="close" to open or close
    // the update-form of a model in a model-list or model-tree.  Also instruct
    // <form> elements to replace themselves with the normal model
    // representation when submitted.

    var listBlock = $('.list-block'),
        modelList = $('.model-list, .model-tree');
    modelList.on('click', '.open', gridportal.website.overlay.open);
    modelList.on('click', '.close', gridportal.website.overlay.close);
    modelList.on('submit', '.slide-in-overlay form', gridportal.website.overlay.submit);
    modelList.on('click', '.delete', gridportal.website.deleteItem);

    listBlock.each(function () {
        var url = $(this).data('url'),
            showCount = $(this).data('showcount') || 10,
            orderBy = $(this).data('orderby');
        if (url !== undefined) {
            gridportal.website.gmList($(this), url, showCount, orderBy);
        }
    });

    // Use an element to modify a model-list or model-tree
    //
    // Elements with class="list-modifier" and attributes
    // data-targetlist="<targetList>", data-targeturl="<targetUrl>", will add a
    // new element to the top of <targetList>, where this element is retrived
    // asynchronuously from <targetUrl>.
    $('.list-modifier').click(function (event) {
        var targetList = $(this).data('targetlist'),
            targetUrl = $(this).data('targeturl');
        gridportal.website.overlay.openNew($(targetList), targetUrl);
        event.preventDefault();
    });
});


// NOTE: only used in gridplatform/manage_reports/templates/manage_reports/generate_report.html
gridportal.website.requestReport = function (csrfToken, requestUrl, statusUrl,
        finalizeUrl, resultElem, spinnerUrl, formData, outputType, noticeField, buttons) {
    'use strict';
    var progressbar = $("#progressbar").progressbar({ value: 0 }),
        progressLabel = $(".progress-label");

    var requestTaskStatus,
        disableButtons = function () {
            if (buttons) {
                buttons.attr('disabled', 'disabled');
            }
        },
        enableButtons = function () {
            if (buttons) {
                buttons.removeAttr('disabled');
            }
        },
        startSpinner = function () {
            resultElem.html('<img src="' + spinnerUrl + '">');
            disableButtons();
        },
        stopSpinner = function () {
            resultElem.empty();
            enableButtons();
        },
        hideNoticeField = function () {
            if (typeof(noticeField) != 'undefined'){
                noticeField.hide();
            }
        },
        showNoticeField = function () {
            if (typeof(noticeField) != 'undefined'){
                noticeField.show();
            }
        },
        failStatus = function (text) {
            stopSpinner();
            hideNoticeField();
            gridportal.website.notify('error', text, false);
        },
        successStatus = function (text) {
            stopSpinner();
            hideNoticeField();
        },
        finalizeFail = function (xhr) {
            if (xhr.status != 0) {
                failStatus(gettext("Failed to construct output files"));
            }
        },
        finalizeDone = function (data) {
            progressbar.progressbar("value", 100);
            successStatus(gettext("Report created"));
            if (outputType === 'pdf') {
                window.open(data.pdf.url, '_blank');
            } else {
                window.open(data.csv.url, '_blank');
            }
        },
        requestFinalize = function (taskId) {
            jQuery.post(
                finalizeUrl,
                {task_id: taskId, csrfmiddlewaretoken: csrfToken}
            ).done(finalizeDone).fail(finalizeFail);
        },
        taskStatusFail = function (jqXHR, textStatus) {
            if (textStatus === 'timeout') {
                failStatus(
                    gettext("Lost contact to the server. Please check your internet connetion."));
            } else if (jqXHR.status != 0) {
                failStatus(gettext("Failed to collect data"));
            }
        },
        taskStatusDone = function (data) {
            var taskId = data.task_id,
                status = data.status,
                errors = data.form_errors,
                result = data.result,
                procent = 0;
            $('.errorlist').remove();
            if (taskId) {
                if (status === 'SUCCESS') {
                    requestFinalize(taskId);
                    progressbar.progressbar("value", 80);
                } else if (status === 'PENDING' || status === 'STARTED' ||
                           status === 'RETRY') {
                    window.setTimeout(jQuery.proxy(requestTaskStatus, {}, data.task_id), 1000);
                } else if (status === 'PROGRESS') {
                    procent = result.current / result.total * 100 * 0.8;
                    progressbar.progressbar("value", procent);
                    window.setTimeout(jQuery.proxy(requestTaskStatus, {}, data.task_id), 1000);
                } else if (status === 'FAILURE') {
                    taskStatusFail();
                } else {
                    taskStatusFail();
                }
            } else {
                if (errors) {
                    jQuery.each(errors, function (key, val) {
                        $('#id_' + key).after('<ul class="errorlist"><li>' + val[0] + '</li></ul>');
                    });
                    stopSpinner();
                    hideNoticeField();
                } else {
                    taskStatusFail();
                }
            }
        };
    requestTaskStatus = function (taskId) {
        jQuery.ajax({
            url: statusUrl,
            data: {task_id: taskId, csrfmiddlewaretoken: csrfToken},
            type: 'POST',
            timeout: 30000
        }).done(taskStatusDone).fail(taskStatusFail);
    };
    outputType = outputType || 'pdf';
    startSpinner();
    showNoticeField();
    jQuery.post(requestUrl, formData).done(taskStatusDone).fail(taskStatusFail);
};


// This function can be used to start and follow a celery background task
// Runs failedCallback (if set) when task fails
gridportal.website.startAsyncTask = function (requestUrl, statusUrl, resultUrl,
        successFn, resultElem, spinnerUrl, useSpinner, failedCallback) {
    'use strict';
    var startSpinner = function () {
            if (useSpinner !== false){
                resultElem.html('<img src="' + spinnerUrl + '">');
            }
        },
        stopSpinner = function () {
            if (useSpinner !== false){
                resultElem.empty();
            }
        },
        failStatus = function (text) {
            stopSpinner();
            gridportal.website.notify('error', text);
        },
        taskStartFail = function (xhr) {
            if (xhr.status != 0) {
                failStatus(gettext("Failed to start background task"));
            }
            if (failedCallback) {
                failedCallback();
            }
        },
        runTask = function (data) {
            startSpinner();
            var catchTask = function (data) {
                gridportal.website.catchAsyncTask(data.task_id,
                        statusUrl, resultUrl, successFn, resultElem, spinnerUrl, failedCallback)();
            };
            jQuery.post(requestUrl, data).done(catchTask).fail(taskStartFail);
        };
    return runTask;
};

// This function can be used to catch and follow a celery background task.
gridportal.website.catchAsyncTask = function (taskId, statusUrl, resultUrl, successFn,
        resultElem, spinnerUrl, failedCallback) {
    'use strict';
    var requestTaskStatus,
        stopSpinner = function () {
            resultElem.empty();
        },
        failStatus = function (text) {
            stopSpinner();
            gridportal.website.notify('error', text);
        },
        // successStatus = function (text) {
        //     stopSpinner();
        // },
        requestResult = function (taskId) {
            jQuery.post(resultUrl, {task_id: taskId}).done(successFn).fail(taskStatusFail);
        },
        taskStatusFail = function (jqXHR, textStatus) {
            if (textStatus === 'timeout') {
                failStatus(
                    gettext("Lost contact to the server. Please check your internet connetion."));
            } else if (jqXHR === undefined || jqXHR.status != 0) {
                failStatus(gettext("Background task failed"));
            }
            if (failedCallback) {
                failedCallback();
            }
        },
        taskStatusDone = function (data) {
            var taskId = data.task_id,
                status = data.status;
            if (taskId) {
                if (status === 'SUCCESS') {
                    requestResult(taskId);
                } else if (status === 'PENDING' || status === 'STARTED' || status === 'RETRY') {
                    window.setTimeout(jQuery.proxy(requestTaskStatus, {}, data.task_id), 1000);
                } else if (status === 'FAILURE') {
                    taskStatusFail();
                } else {
                    taskStatusFail();
                }
            } else {
                taskStatusFail();
            }
        },
        catchTask = function () {
            requestTaskStatus(taskId);
        };
    requestTaskStatus = function (taskId) {
        jQuery.ajax({
            url: statusUrl,
            data: {task_id: taskId},
            type: 'POST',
            timeout: 30000
        }).done(taskStatusDone).fail(taskStatusFail);
    };

    return catchTask;
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
});

// Enable chosen on all selects that are not in empty forms when document is
// ready.  All other selects must manually enable chosen (e.g. empty forms
// being rendered and forms rendered as a result of some ajax call).
$(document).ready(function () {
    'use strict';
    $('select').not('.empty-form select').chosen({enable_split_word_search: true, search_contains: true});
    $('.datetime').datetimepicker({
        timeFormat: 'HH:mm:ss',
        addSliderAccess: true,
        sliderAccessArgs: { touchonly: false }
    });
});
