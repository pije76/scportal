# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
"""
<p>This app define Django models and functionality related to
Rules.</p>

<div><p><b>Figure: Data-flow Diagram for Rules:</b> This figure
describes the data flow related to rules between input (GridPortal,
Spot Index, Meter), output (Phone, Email, Meter (relays)), functions
(GridEngine, Agent), and database (PostgreSQL). </p><img
src="data-flow-diagram-for-rules.jpg" style="max-width:100%;" align="center"
/></div>

<p>{@link UserRule}s are created in the GridPortal and stored in the
PostgreSQL database.</p>

<p>Spot {@link Index}es in the PostgreSQL database are updated daily
from their relevant sources, such as Nordpool FTP, by {@link
#legacy.nordpool.importer.fetch_import_week fetch_import_week()}.</p>

<p>{@link measurementpoints.models.LogicalInput LogicalInput} values are
measured by {@link legacy.devices.models.Meter Meter}s which
forwards these measurements to their {@link legacy.devices.Agent
Agent}, who forwards them on to the PostgreSQL server.</p>

<p>The stored {@link UserRule}s are loaded along with relevant data,
such as {@link Index}es by the GridEngine.  The GridEngine processes
the loaded {@link UserRule}s with these results:</p>

<ul>
<li>relay switch schedules in form of {@link AgentRule}s</li>
<li>rule execution objects in form of {@link EngineRule}s</li>
</ul>

<p>The {@link AgentRule} are send to the relevant {@link
legacy.devices.Agent Agent}, which then makes sure to process
these schedules as time goes.</p>

<p>The {@link EngineRule}s regularily monitor {@link
measurementpoints.models.LogicalInput LogicalInput} values to check if
their triggering conditions are all met, to produce the following
kinds of actions:</p>

<ul>
<li>relay switch actions in form of {@link RelayAction}s</li>
<li>email message actions in form of {@link EmailAction}s</li>
<li>phone text message actions in form of {@link PhoneAction}s</li>
</ul>

<p>The relay switch actions are too send to the relevant {@link
legacy.devices.Agent Agent}, which then immediatly executes the
switch action.</p>

<p>The email message actions are executed directly by the GridEngine,
by sending an email message to a given recipient.</p>

<p>The phone text message actions are executed directly by the
GridEngine, by sending a text message to the given recipient.</p>
"""
__docformat__ = "javadoc en"


class RuleError(Exception):
    """
    Base class for exceptions raised by the rules package.
    """
    pass


class UserRuleIntegrityError(RuleError):
    """
    """
    pass
