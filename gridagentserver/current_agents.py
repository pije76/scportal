#!/usr/bin/env python

# dry-run example command:
# ./current_agents.py -n -v

import argparse

from client import send_message


parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='store_true',
                    help='increase output verbosity')
parser.add_argument('-n', '--dry-run', action='store_true',
                    help='don\'t actually send command')


def current_agents(args):
    routing_key = 'agentserver'
    message = {
        'command': 'current_agents',
    }
    send_message(routing_key, message, args.verbose, args.dry_run)


if __name__ == '__main__':
    current_agents(parser.parse_args())
