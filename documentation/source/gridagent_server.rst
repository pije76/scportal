****************
GridAgent Server
****************

The GridAgent server listens for network connections from GridAgents.  Its
primary purpose is to receive measurement data from the GridAgents and add it
to the database where the GridPortal may read it.

It keeps track of the currently connected GridAgents, and is responsible for
forwarding time-based rules to connected GridAgents, for setting the time on
GridAgents, for storing information about the current GridAgent and GridPoint
state as provided by the GridAgent, and it is also capable of sending GridAgent
software updates and relay control signals for GridPoints.

The GridAgent server access the same database as the GridPortal, using parts of
the same data model specified with the Django ORM that the GridPortal uses.



GridAgent Server Protocol
=========================

Communication is message-based.  Messages have a common header with type,
length and a field for Boolean where this may simplify the payload.

Apart from the initial handshake, communication is encrypted.  We use a
pre-shared key, merged with a nonce from the agent to protect against playback
attacks (and with the MAC address from the agent for slightly improved
obscurity).

Currently, the set of messages sent by a server is disjoint from the set of
messages sent by a client --- though the header is the same, and the type
identifiers are global, so this may be changed later.

The protocol has a version number, sent by both sides as part of the handshake.
At present, the server must handle version discrepencies, i.e. communication
takes place with the protocol version specified by the client.

Data is sent in big endian/network byte order format.


Handshake
---------

The server sends a 4-byte protocol version followed by a 8-byte random nonce.

The client/agent sends a 4-byte protocol version followed by an 8-byte
identifiers.  (Currently, agents use their Ethernet MAC address as identifiers,
with the 48-bit MAC address encoded as a 64-bit number; meaning that the first
two bytes of the identifier will always be zero.)

In the current setup, the server is responsible for handling protocol version
discrepancies; either communication happens with the protocol version specified
by the client, or the server closes the connection.


Encryption
----------

Communication is encrypted using RC4.

The encryption uses a key constructed by combining a shared secret with the
nonce and the ID provided by the client.

The same key is used for communication from client to server and from server to
client, though these are otherwise considered separate streams with separate
state.

After the handshake, communication is encrypted.


Message header
--------------

All messages after the handshake share a common header format:

* 4-bytes unsigned message size
* 2 bytes padding
* 1 byte message type
* 1 byte boolean flags

The length is the total length *including* the header.


Message structure
-----------------

All the different messages and their structure are very simple to follow by
simply inspecting the Python code. Client and server messages are found
:file:`gridplatform/gridagentserver_protocol/client_messages.py` and
:file:`gridplatform/gridagentserver_protocol/server_messages.py`, respectively.

