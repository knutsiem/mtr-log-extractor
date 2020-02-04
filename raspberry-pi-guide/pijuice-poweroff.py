#!/usr/bin/env python3

import argparse
from pijuice import PiJuice

delay_min = 1
delay_max = 254

argparser = argparse.ArgumentParser(description="Schedule PiJuice power-off")
argparser.add_argument(
        '-d', '--delay', type=int,
        metavar='[{}-{}]'.format(delay_min, delay_max),
        help=(
            "Delay in seconds. Note that this delay must allow proper "
            "shutdown of the system. Given that system shutdown is initiated "
            "immediately it is recommended that this is 30 seconds at "
            "minimum."))
argparser.add_argument(
        '-c', '--cancel', action='store_true',
        help="Cancel a scheduled power-off")

args = argparser.parse_args()

i2c_bus = 1  # found with `i2cdetect -l`
i2c_bus_address = 0x14  # found with `pijuice_cli` > General
pijuice = PiJuice(i2c_bus, i2c_bus_address)

if args.cancel:
    pijuice.power.SetPowerOff(255)
elif args.delay:
    if delay_min <= args.delay <= delay_max:
        pijuice.power.SetPowerOff(args.delay)
    else:
        argparser.error(
                "Given delay {} is outside allowed interval (min: {}, max: {})"
                .format(args.delay, delay_min, delay_max))
else:
    argparser.error("Expected either -d/--delay or -c/--cancel argument")
