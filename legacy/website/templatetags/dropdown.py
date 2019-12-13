# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
This module defines Django template tags for using jQuery-dropdown.

The template tag C{{% dropdown %}} is used to define everything where the
drop-down is to be shown.  A secondary C{{% dropdown_bodies %}} template tag is
used to insert bodies with the correct id for all drop-downs that have been
rendered earlier in the same document.

Yes, you can have any number of drop-downs on the same page, and you don't need
to manually couple each drop down with its anchor.

@see: U{http://labs.abeautifulsite.net/jquery-dropdown/}

The jQuery-dropdown javascript inserts the contents of a named C{<div>} as
dropdown on elements (anchors) that have their C{data-dropdown} set to the id
of that C{<div>}.  The C{<div>} needs to be defined in a place where it is not
styled, and so, it will usually be a different place in the document than where
the drop-down is to be shown, thus creating a high coupling between these two
locations.
"""
from django import template


register = template.Library()


@register.tag
def dropdown(parser, token):
    """
    Construct an anchor which will drop-down a body when clicked.

    Usage::

        {% dropdown %}
          {% anchor %}
            {% trans 'Add' %} <img ... >
          {% endanchor %}
          {% body %}
            <ul>
              <li>
                <a href="{% url ... %}">
                  {% trans "Drop-down link 1" %}
                </a>
              </li>
              <li>
                <a href="{% url ... %}">
                  {% trans "Drop-down link 2" %}
                </a>
              </li>
            </ul>
          {% endbody %}
        {% enddropdown %}

        ...

        {% dropdown_bodies %}
        </body>

    The popup direction defaults to 'anchor-right' to change this add an
    argument to the dropdown tag:
        {% dropdown "anchor-left" %}

    The tag should be used where the drop-down should be rendered.  A seperate
    tag, C{{% dropdown_bodies %}} is used to insert the C{dropdown_body}
    outside formatting context, so that it will be placed correctly when
    rendered.

    @see: L{dropdown_bodies} for details on the C{{% dropdown_bodies %}} tag.
    """
    menu_direction = 'anchor-right'
    tokens = token.split_contents()
    if len(tokens) > 1:
        menu_direction = tokens[1][1:-1]
    parser.parse("anchor")
    parser.delete_first_token()
    anchor_nodes = parser.parse("endanchor")
    parser.delete_first_token()
    parser.parse("body")
    parser.delete_first_token()
    body_nodes = parser.parse("endbody")
    parser.delete_first_token()
    parser.parse("enddropdown")
    parser.delete_first_token()
    return DropDownNode(anchor_nodes, body_nodes, menu_direction)


@register.simple_tag(takes_context=True)
def dropdown_bodies(context):
    """
    Insert drop-down bodies from all drop-downs that has been rendered so far.

    Usage::

        ...
        {% dropdown_bodies %}
        </body>

    This tag should be inserted just before the C{</body>} element, as
    prescribed by the jQuery dropdown documentation.

    @see: L{do_dropdown} for a full example of using C{{% dropdown %}}
    """
    result = ""
    if "dropdown" in context.render_context:
        for dropdown_id, dropdown_body in \
                context.render_context["dropdown"].iteritems():
            result += \
                u'<div id="%s" class="dropdown-menu %s">%s</div>' % (
                    dropdown_id,
                    dropdown_body['direction'],
                    dropdown_body['node'])
    return result


class DropDownNode(template.Node):
    """
    A C{DropDownNode} keeps track of C{anchor_nodes} and C{body_nodes}, and
    inserts the C{anchor_nodes} when rendered.
    """

    def __init__(self, anchor_nodes, body_nodes, direction):
        """
        Create a C{DropDownNode} from given C{anchor_nodes} and C{body_nodes}.
        """
        self.anchor_nodes = anchor_nodes
        self.body_nodes = body_nodes
        self.direction = direction

    def render(self, context):
        """
        Renders C{self.anchor_nodes} and stores C{self.body_nodes},
        C{self.direction} and an ID string in the C{context.render_context}.
        """
        if "dropdown" not in context.render_context:
            context.render_context["dropdown"] = {}

        dropdown_id = "dropdown-%d" % len(context.render_context["dropdown"])
        context.render_context["dropdown"][dropdown_id] = \
            {'direction': self.direction,
             'node': self.body_nodes.render(context)}

        return u'<a href="#" data-dropdown="#%s">%s</a>' % (
            dropdown_id,
            self.anchor_nodes.render(context))
