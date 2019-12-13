/*jslint browser: true */

(function () {
    'use strict';
    // "Best effort" attempt to send JS error message to error reporting
    // service at server; attached as onerror event handler.  (Will call
    // previous onerror handler if it exists.)
    var oldOnError = window.onerror;
    window.onerror = function(message, url, line) {
        var req,
            csrftoken,
            cookies,
            cookie,
            i;
        if (window.XMLHttpRequest && window.JSON && window.JSON.stringify) {
            // Only attempt to send data if the browser supports standard APIs
            // for AJAX and JSON...
            if (document.cookie) {
                // Get CSRF token from cookie, if possible.  The cookie string
                // entries should be separated by ";", but split on " " too,
                // just in case.  ("Extra" empty entries won't harm.)
                cookies = document.cookie.split('; ');
                for (i = 0; i < cookies.length; i += 1) {
                    cookie = cookies[i];
                    if (cookie.indexOf('csrftoken=') === 0) {
                        csrftoken = cookie.substring('csrftoken='.length);
                        break;
                    }
                }
            }
            req = new XMLHttpRequest();
            req.open('post', '{% url "jserror-jserror" %}', true);
            req.setRequestHeader('Content-type', 'application/json');
            if (csrftoken) {
                // Include CSRF token if known.
                req.setRequestHeader('X-CSRFToken', csrftoken);
            }
            req.send(JSON.stringify({
                message: message,
                url: url,
                line: line,
                location: window.location.href
            }));
        }
        if (oldOnError) {
            // Call old error handler.
            return oldOnError(message, url, line);
        }
        // Don't preempt default error handler.
        return false;
    };
}());
