#!/usr/bin/env python

# dry-run example command:
# ./control_mode.py -n -v 00:24:21:0e:8f:cd --manual \
#   aa:bb:cc:dd:11:22:33:44 11:22:33:44:aa:bb:cc:dd

import argparse

from client import normalise_mac, send_message, gridpoint_id


parser = argparse.ArgumentParser()
parser.add_argument('agent', help='target agent (MAC address)')
parser.add_argument('meters', nargs='+',
                    help='target meters (ZigBee MAC addresses)')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='increase output verbosity')
parser.add_argument('-n', '--dry-run', action='store_true',
                    help='don\'t actually send command')
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-a', '--auto', action='store_true', help='auto mode')
group.add_argument('-m', '--manual', action='store_true', help='manual mode')


def control_mode(args):
    agent_mac = normalise_mac(args.agent)
    meters = [gridpoint_id(normalise_mac(meter, bytes=8))
              for meter in args.meters]
    routing_key = 'agent.%s' % (agent_mac,)
    assert args.manual != args.auto
    control_manual = args.manual
    message = {
        'command': 'control_mode',
        'agent': agent_mac,
        'control_manual': control_manual,
        'meters': meters,
    }
    send_message(routing_key, message, args.verbose, args.dry_run)


if __name__ == '__main__':
    control_mode(parser.parse_args())
