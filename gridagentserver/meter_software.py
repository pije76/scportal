#!/usr/bin/env python

# dry-run example command:
# ./meter_software.py 3C970E1E8E4E 2.1.1 3.0.9 0000aabbcc000009 -v -n

import argparse

from client import normalise_mac, normalise_version, send_message, gridpoint_id


parser = argparse.ArgumentParser()
parser.add_argument('agent', help='target agent (MAC address)')
parser.add_argument('sw_version', help='software version (n.n.n[extra])')
parser.add_argument('-m', '--model',
                    help='hardware model', default=3)
parser.add_argument('target_hw_version',
                    help='compatible hardware version (n.n.n[extra])')
parser.add_argument('meters', nargs='+',
                    help='target meters (ZigBee MAC addresses)')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='increase output verbosity')
parser.add_argument('-n', '--dry-run', action='store_true',
                    help='don\'t actually send command')


def meter_swupdate(args):
    agent_mac = normalise_mac(args.agent)
    sw_version = normalise_version(args.sw_version)
    hw_model = int(args.model)
    hw_version = normalise_version(args.target_hw_version)
    meters = [gridpoint_id(normalise_mac(meter, bytes=8))
              for meter in args.meters]
    routing_key = 'agent.%s' % (agent_mac,)
    message = {
        'command': 'gridpoint_software',
        'agent': agent_mac,
        'sw_version': sw_version,
        'hw_model': hw_model,
        'target_hw_version': hw_version,
        'meters': meters,
    }
    send_message(routing_key, message, args.verbose, args.dry_run)


if __name__ == '__main__':
    meter_swupdate(parser.parse_args())
