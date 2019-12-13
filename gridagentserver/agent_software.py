#!/usr/bin/env python

# dry-run example command:
# ./agent_software.py 3C970E1E8E4E 2.1.0 4.4.0 -v -n

import argparse

from client import normalise_mac, normalise_version, send_message


parser = argparse.ArgumentParser()
parser.add_argument('agent', help='target agent (MAC address)')
parser.add_argument('sw_version', help='software version (n.n.n[extra])')
parser.add_argument('-m', '--model',
                    help='hardware model', default=1)
parser.add_argument('target_hw_version',
                    help='compatible hardware version (n.n.n[extra])')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='increase output verbosity')
parser.add_argument('-n', '--dry-run', action='store_true',
                    help='don\'t actually send command')


def agent_swupdate(args):
    mac = normalise_mac(args.agent)
    sw_version = normalise_version(args.sw_version)
    hw_model = int(args.model)
    hw_version = normalise_version(args.target_hw_version)
    routing_key = 'agent.%s' % (mac,)
    message = {
        'command': 'gridagent_software',
        'agent': mac,
        'sw_version': sw_version,
        'hw_model': hw_model,
        'target_hw_version': hw_version,
    }
    send_message(routing_key, message, args.verbose, args.dry_run)


if __name__ == '__main__':
    agent_swupdate(parser.parse_args())
