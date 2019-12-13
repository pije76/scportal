/*jslint browser: true */
/*global $, jQuery, gettext, pgettext, get_format*/

var ui = window.ui || {};

// The javascript version of the icon templatetag
ui.icon = function (iconName, size, spin) {
    'use strict';
    var icon = $('<i class="fa"></i>');
    icon.addClass('fa-' + iconName);
    if (size) {
        icon.addClass('fa-' + size);
    }
    if (spin) {
        icon.addClass('fa-spin');
    }

    //hack html() returns the html contents of the first node
    return $('<div>').append(icon).html();
};

ui.parseNumber = function (numberString) {
    'use strict';
    var thousandSeparator = get_format('THOUSAND_SEPARATOR'),
        decimalSeparator = get_format('DECIMAL_SEPARATOR');
    while (numberString.length !== numberString.replace(thousandSeparator, '').length) {
        numberString = numberString.replace(thousandSeparator, '');
    }
    return parseFloat(numberString.replace(decimalSeparator, '.'));
};

ui.formatNumber = function (number, decimalPlaces) {
    'use strict';
    var formattedWithoutThousandSeparator = number.toFixed(decimalPlaces).replace('.', get_format('DECIMAL_SEPARATOR')),
        addThousandSeparator = function (numberString, thousandSeparator) {
            var rx = /(\d+)(\d{3})/;
            return numberString.replace(/\d+/, function (w) {
                while (rx.test(w)) {
                    w = w.replace(rx, '$1' + thousandSeparator + '$2');
                }
                return w;
            });
        };
    return addThousandSeparator(formattedWithoutThousandSeparator, get_format('THOUSAND_SEPARATOR'));
};

ui.addFormsetForm = function (event) {
    'use strict';
    event.preventDefault();
    var parent = $(event.target).closest('div.box'),
        emptyForm = parent.find('.empty-form'),
        newForm = emptyForm.clone(),
        totalForms = parent.find('input[name$="TOTAL_FORMS"]'),
        newId = totalForms.val();
    newForm.find('div, input, select, li, label').each(function () {
        var input = $(this);
        if (input.attr("name")) {
            input.attr('name', input.attr('name').replace('__prefix__', newId));
        }
        if (input.attr("id")) {
            input.attr('id', input.attr('id').replace('__prefix__', newId));
        }
        if (input.attr("for")) {
            input.attr('for', input.attr('for').replace('__prefix__', newId));
        }
    });
    newForm.removeClass('empty-form').show();
    totalForms.val(parseInt(totalForms.val(), 10) + 1);
    newForm.appendTo(emptyForm.parent());
};


ui.datepickerOptions = (function () {
    'use strict';
    var format = get_format('DATE_INPUT_FORMATS')[0],
        // Python/Django format to Bootstrap Datepicker format...
        mapping = {
            '%d': 'dd',
            '%m': 'mm',
            '%Y': 'yyyy',
            '%y': 'yy'
        },
        capitalize = function (str) {
            return str.charAt(0).toUpperCase() + str.substring(1);
        };
    _.forEach(mapping, function (js, python) {
        format = format.replace(python, js);
    });
    jQuery.fn.datepicker.dates.current = {
        days: [
            gettext('Sunday'),
            gettext('Monday'),
            gettext('Tuesday'),
            gettext('Wednesday'),
            gettext('Thursday'),
            gettext('Friday'),
            gettext('Saturday'),
            gettext('Sunday')
        ],
        daysShort: [
            gettext('Sun'),
            gettext('Mon'),
            gettext('Tue'),
            gettext('Wed'),
            gettext('Thu'),
            gettext('Fri'),
            gettext('Sat'),
            gettext('Sun')
        ],
        daysMin: [
            pgettext('weekday', 'Su'),
            pgettext('weekday', 'Mo'),
            pgettext('weekday', 'Tu'),
            pgettext('weekday', 'We'),
            pgettext('weekday', 'Th'),
            pgettext('weekday', 'Fr'),
            pgettext('weekday', 'Sa'),
            pgettext('weekday', 'Su')
        ],
        months: [
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
        ],
        monthsShort: [
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
        ],
        today: gettext('Today')
    };
    return {
        // from Django i18n
        weekStart: parseInt(get_format('FIRST_DAY_OF_WEEK'), 10),
        format: format,
        autoclose: true,
        language: 'current'
    };
}());

/*
    target: A jquery object that should have the popup attached
    options: A list of filters
    contentLoader: A jquery object containing the contentLoader div
*/
ui.popoverFilter = function (target, options, contentLoader) {
    'use strict';
    var popop = $('<div><div class="arrow"></div></div>'),
        content,
        listContent,
        filterContent,
        label,
        count,
        countChecked,
        checkbox,
        selected = [],
        popover,
        extra = contentLoader.data('extra');

    if (extra !== undefined) {
        try {
            extra = JSON.parse(extra);
        } catch (err) {
            extra = {};
        }
    } else {
        extra = {};
    }
    jQuery.each(options, function (index, filter) {
        if (extra[filter.name] === undefined) {
            extra[filter.name] = [];
        }
    });
    filterContent = function () {
        jQuery.each(options, function (index, filter) {
            if (extra[filter.name]) {
                selected = extra[filter.name];
            }
            count = filter.choices.length;
            countChecked = 0;
            content = $('<div></div>').attr('id', filter.name).addClass('filter');

            $('<h3></h3>').addClass('popover-title').text(filter.verbose).appendTo(content);
            listContent = $('<div></div>').addClass('popover-content').appendTo(content);
            jQuery.each(filter.choices, function (index, choice) {
                label = $('<div><label></label></div>').appendTo(listContent);
                checkbox = $('<input type="checkbox">').val(choice[0]).appendTo(label);
                if (_.contains(selected, String(choice[0]))) {
                    checkbox.prop('checked', true);
                    countChecked += 1;
                }
                $('<span></span>').text(' ' + choice[1]).appendTo(label);
            });
            if (filter.allNone) {
                label = $('<div><label></label></div>').prependTo(listContent);
                checkbox = $('<input type="checkbox">').addClass('check-all').appendTo(label);
                $('<span></span>').text(' ' + filter.allNoneVerbose).appendTo(label);
                if (countChecked === count) {
                    checkbox.prop('checked', true);
                } else if (countChecked) {
                    checkbox.prop('indeterminate', true);
                }
            }
            popop.append(content);
        });

        return popop;
    };
    $(document).on('change', '.popover .filter input.check-all', function (event) {
        checkbox = $(event.target);
        var isChecked = checkbox.prop('checked'),
            filter = checkbox.closest('.filter');
        filter.find('input:not(.check-all)').prop('checked', isChecked);
        filter.find('input:not(.check-all)').change();
    });
    $(document).on('change', '.popover .filter input:not(.check-all)', function (event) {
        var filter = $(event.target).closest('.filter'),
            ids = [],
            anyChecked = false,
            anyUnchecked = false;
        filter.find('input:not(.check-all)').each(function () {
            checkbox = $(this);
            if (checkbox.prop('checked')) {
                ids.push(checkbox.attr('value'));
                anyChecked = true;
            } else {
                anyUnchecked = true;
            }
        });
        if (anyChecked && anyUnchecked) {
            filter.find('.check-all').prop('checked', false);
            filter.find('.check-all').prop('indeterminate', true);
        } else {
            // all checked or all unchecked
            filter.find('.check-all').prop('indeterminate', false);
            filter.find('.check-all').prop('checked', anyChecked);
        }
        extra[filter.attr('id')] = ids;
        ui.loadContent(contentLoader, extra, contentLoader.closest('.box').find('.list-search input').val());
    });

    // Content needs to be an empty space, else it doesn't get shown
    // We set the real content futher down
    target.popover({
        html: true,
        placement: 'bottom',
        content: ' ',
        title: ''
    });

    popover = target.data('bs.popover');
    popover.setContent = function () {
        var $tip = this.tip();
        if (!$tip.hasClass('filter')) {
            $tip.html(filterContent());
        }
        $tip.removeClass('fade top bottom left right in').addClass('filter');
    };
};


ui.getQuerystrings = function (url) {
    'use strict';
    var querystrings = {},
        match,
        pl = /\+/g,
        search = /([^&=]+)=?([^&]*)/g,
        decode = function (s) { return decodeURIComponent(s.replace(pl, " ")); },
        query = "";

    if (url === undefined) {
        query = window.location.search.substring(1);
    } else {
        if (url.indexOf('?') !== -1) {
            query = url.split('?')[1];
        }
    }

    while (match = search.exec(query)) {
       querystrings[decode(match[1])] = decode(match[2]);
    }
    return querystrings;
};

ui.updateLocationHash = function (hashObject, override) {
    'use strict';
    var currentHash = window.location.hash.replace(/^#/, ''),
        override = override || false,
        currentObject = {};

    if (currentHash !== "") {
        currentObject = JSON.parse(decodeURIComponent(currentHash));
        if (!override) {
            hashObject = jQuery.extend(currentObject, hashObject);
        }
    }

    window.location.hash = encodeURIComponent(
        JSON.stringify(hashObject));
};

ui.getHashValueFromKey = function (key) {
    var currentHash = window.location.hash.replace(/^#/, ''),
        hashObject = {}
        result = "";

    if (currentHash !== "") {
        hashObject = JSON.parse(decodeURIComponent(currentHash));
        if (hashObject[key]) {
            result = hashObject[key];
        }
    }
    return result;
};

ui.generateStringHash = function (string) {
    // Found at http://stackoverflow.com/questions/7616461/generate-a-hash-from-string-in-javascript-jquery
    var hash = 0,
        i,
        chr,
        len;
    if (string.length === 0) {
        return hash;
    }
    for (i = 0, len = string.length; i < len; i++) {
        chr   = string.charCodeAt(i);
        hash  = ((hash << 5) - hash) + chr;
        hash |= 0; // Convert to 32bit integer
    }
    return hash;
},


ui.loadContent = function (selector, extra, query) {
    'use strict';
    var load,
        storageId = function (url, setting) {
            // remove pagination and similar parameters from storage key
            var baseUrl = url.replace(/\?.*$/, '');
            return 'contentLoader-' + baseUrl + '-' + setting;
        },
        saveOptions = function (contentLoader) {
            var options = contentLoader.data(),
                url = options.url;
            localStorage.setItem(storageId(url, 'orderby'), options.orderby);
            localStorage.setItem(storageId(url, 'direction'), options.direction);
        },
        loadOptions = function (contentLoader) {
            var url = contentLoader.data('url'),
                orderBy = localStorage.getItem(storageId(url, 'orderby')),
                direction = localStorage.getItem(storageId(url, 'direction')),
                extra = localStorage.getItem(storageId(url, 'extra'));
            if (orderBy) {
                contentLoader.data('orderby', orderBy);
            }
            if (direction) {
                contentLoader.data('direction', direction);
            }
            if (extra !== null) {
                contentLoader.data('extra', extra);
            }
        },
        setUpSorting = function (contentLoader) {
            var options = contentLoader.data();
            // First remove the old sorting direction indicator
            contentLoader.find('th').removeClass('sorting_asc sorting_desc');
            // Then add the current one
            contentLoader.find('th[data-orderby="' + options.orderby + '"]').
                addClass('sorting_' + (options.direction || 'asc'));
            // Make every sortable th clickable.
            contentLoader.find('th.sorting').click(function () {
                var sorting = $(this),
                    orderBy = sorting.data('orderby');
                if (orderBy === options.orderby) {
                    if (options.direction === 'asc' || !options.direction) {
                        contentLoader.data('direction', 'desc');
                    } else {
                        contentLoader.data('direction', 'asc');
                    }
                }
                contentLoader.data('orderby', orderBy);
                saveOptions(contentLoader);
                load(contentLoader);
            });
        },
        setUpPagination = function (contentLoader) {
            contentLoader.find('.pagination a').click(function (event) {
                event.preventDefault();
                event.stopPropagation();
                contentLoader.data('url', $(this).attr('href'));
                load(contentLoader);
            });
        },
        updateLocationHash = function (contentLoader) {
            var options = contentLoader.data(),
                hashObject = {},
                page = ui.getQuerystrings(options.url).page;
            if (page) {
                hashObject[options.urlHash] = page;
                ui.updateLocationHash(hashObject);
            }
        },
        urlHashString = function (url) {
            var location = url;
            if (url.indexOf('?') !== -1) {
                location = url.split('?')[0];
            }
            return ui.generateStringHash(location);
        },
        extractPageFromHash = function (contentLoader, page) {
            var pageFromHash = ui.getHashValueFromKey(contentLoader.data('urlHash'));
            if (pageFromHash) {
                return pageFromHash;
            }
            return page;
        };
    load = function (contentLoader) {
        var options = contentLoader.data(),
            urlHash = options.urlHash || undefined,
            page;
        if (!options.url) {
            throw "You must specify an URL for the content loader!";
        }
        contentLoader.html('<i class="fa fa-spinner fa-spin"></i>');
        if (!options.urlHash) {
            urlHash = urlHashString(options.url);
            contentLoader.data('urlHash', urlHash);
        }
        updateLocationHash(contentLoader);
        page = extractPageFromHash(contentLoader, ui.getQuerystrings(options.url).page);
        jQuery.ajax(options.url, {
            type: 'GET',
            data: {
                o: options.orderby,
                ot: options.direction || 'asc',
                extra: options.extra || undefined,
                page: page,
                q: query
            }
        }).done(function (data) {
            contentLoader.empty(); // Kill spinner
            // Hack: jquery only searches inside the outmost block,
            // so we have to append a div around the atual data
            if (contentLoader.hasClass('search-block') && $('.no-data', $('<div></div>').append(data)).length > 0) {
                contentLoader.closest('.box').fadeOut(500, function () {
                    $(this).remove();
                });
            } else {
                contentLoader.append(data);
            }
            // Enable rowlink
            contentLoader.find('table[data-provides="rowlink"]').rowlink();
            setUpSorting(contentLoader);
            setUpPagination(contentLoader);
            contentLoader.trigger('contentloader.loaded');
        }).fail(function () {
            contentLoader.empty(); // Kill spinner
            // TODO: Report (connection?) error?
        });
    };
    $(selector).each(function () {
        var contentLoader = $(this),
            url;
        if (extra !== undefined) {
            url = contentLoader.data('url');
            localStorage.setItem(storageId(url, 'extra'), JSON.stringify(extra));
        }
        loadOptions(contentLoader);
        load(contentLoader);
    });
};


ui.initializeSearchField = function (selector) {
    'use strict';
    var field = $(selector),
        input = field.find('input');
    input.keydown(function (event) {
        if (event.keyCode === 13) {
            window.location = field.data('url') + '?q=' + encodeURIComponent(input.val());
        }
    });
};

$(document).ready(function () {
    'use strict';
    var changed = false,
        submit = false;
    // NOTE: wrap stuff in something with class empty-form to *not* use chosen or multiselect --- should be done for empyt_form for JS-insert in particular
    $('select').not('.empty-form select, [multiple=multiple]').chosen({enable_split_word_search: true, search_contains: true});

    $('select[multiple=multiple]').not('.empty-form select').multiSelect({
        selectableHeader: "<input type='text' class='charfield textinput form-control search-input' autocomplete='off'>",
        selectionHeader: "<input type='text' class='charfield textinput form-control search-input' autocomplete='off'>",
        afterInit: function () {
            var multiselect = this,
                selectableSearch = multiselect.$selectableUl.prev(),
                selectionSearch = multiselect.$selectionUl.prev(),
                selectableSearchString = '#' + multiselect.$container.attr('id') + ' .ms-elem-selectable:not(.ms-selected)',
                selectionSearchString = '#' + multiselect.$container.attr('id') + ' .ms-elem-selection.ms-selected';

            multiselect.qs1 = selectableSearch.quicksearch(selectableSearchString);
            multiselect.qs2 = selectionSearch.quicksearch(selectionSearchString);
        },
        afterSelect: function () {
            this.qs1.cache();
            this.qs2.cache();
        },
        afterDeselect: function () {
            this.qs1.cache();
            this.qs2.cache();
        }
    });

    $('.dateinput, .date-picker').datepicker(ui.datepickerOptions);

    $('.list-datepicker i').click(function () {
        $(this).parent().find('input.date-picker').datepicker().focus();
    });

    // Makes it possible to click on the icon to show the datepicker
    $('#customerfilter').quicksearch('#customer-select-modal .list-group a');

    ui.loadContent('.content-loader');
    ui.initializeSearchField('#search');

    $('body').on('click', '.popover .close', function () {
        $(this).parent().hide();
    });

    // It should not be possible to generate two POSTs in a row by mistake. For
    // this reason buttons can be decorated with the "disable-on-click" class.
    $('.disable-reenable-on-click').click(function () {
        var button = $(this);
        button.addClass('disabled');
        window.setTimeout(function () {
            button.removeClass('disabled');
        }, 500);
    });

    //Disable form submit on Enter press
    $('form').bind("keyup keypress", function (e) {
        var code = e.keyCode || e.which;
        if (code === 13 && e.target.nodeName !== "TEXTAREA") {
            e.preventDefault();
            return false;
        }
    });

    $('form :input').not('.ms-selectable .search-input').change(function () {
        changed = true;
    });

    $("form button[type=submit], form input[type=submit]").click(function () {
        submit = true;
    });


    window.onbeforeunload = function () {
        if (changed && !submit) {
            submit = false;
            return gettext('Your changes are not saved');
        }
    };

    $('.list-search input').each(function () {
        var input = $(this),
            oldQuery = '';
        input.on('keydown keyup change cut paste input', _.debounce(function () {
            var query = input.val(),
                contentLoader;
            if (query !== oldQuery) {
                oldQuery = query;
                contentLoader = input.closest('.box').find('.content-loader');
                ui.loadContent(contentLoader, undefined, query);
            }
        }, 250));
    });
});
