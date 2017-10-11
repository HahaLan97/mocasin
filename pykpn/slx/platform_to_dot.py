#!/usr/bin/env python3

# Copyright (C) 2017 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard


import argparse

from pykpn.common import logging
from pykpn.slx.platform import SlxPlatform


log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()

    logging.add_cli_args(parser)

    parser.add_argument('platform', help="xml platform description", type=str)
    parser.add_argument('dot', help="dot output file", type=str)

    args = parser.parse_args()

    logging.setup_from_args(args)

    platform = SlxPlatform(args.platform)
    dot = platform.to_pydot()
    dot.write_raw(args.dot)


if __name__ == '__main__':
    main()
