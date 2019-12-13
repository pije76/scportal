# break module dependency chain...
# messages module needs the lookup table to construct send/parse message
# headers; but client/server message modules depend on that code...

import client_messages
import server_messages

# NOTE: order matters; same as in client...
# (To make ID-number/type mapping simple.)
message_types = [
    client_messages.BulkMeasurements,
    server_messages.ConfigGp,
    server_messages.ConfigGaRulesets,
    server_messages.ConfigGaTime,
    server_messages.ConfigGaPrices,
    server_messages.ConfigGpSoftware,
    server_messages.ConfigGaSoftware,
    server_messages.CommandGaPollMeasurements,
    server_messages.CommandGaPropagateTime,
    server_messages.CommandGpSwitchControl,
    server_messages.CommandGpSwitchRelay,
    client_messages.NotificationGaAddMode,
    client_messages.NotificationGaTime,
    client_messages.NotificationGaConnectedSet,
    client_messages.NotificationGpState,
    client_messages.AcknowledgementGpSoftware,
    client_messages.AcknowledgementGaSoftware,
    client_messages.ErrorGpSoftware,
    client_messages.ErrorGaSoftware,
    client_messages.InfoAgentVersions,
    client_messages.InfoEventLog,
]
