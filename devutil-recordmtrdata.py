#!/usr/bin/env python3

import argparse
import serial
from datetime import datetime

argparser = argparse.ArgumentParser(
        description=(
            'Spool all data messages from MTR at serial port to binary file'))
argparser.add_argument('port', help='Serial port identifier')
argparser.add_argument(
        'file',
        default='mtr-{}.bin',
        help=(
            'File to write MTR data messages to. '
            'A {} will be replaced with a timestamp in the ISO 8601 combined '
            'date and time basic format. (default: %(default)s).'))
args = argparser.parse_args()
port = args.port
timeout_seconds = 5
serial_port = serial.Serial(
        port=port, baudrate=9600, timeout=timeout_seconds)
print("Opened serial port %s, sending 'spool all' command '/SA'..." % port)
serial_port.write(b'/SA')

timed_out = False
bytes_read = bytearray()
while not timed_out:
    byte_read = serial_port.read()
    timed_out = len(byte_read) == 0
    if timed_out:
        print("Timed out after %d seconds" % timeout_seconds)
        break
    bytes_read.extend(byte_read)
    num_bytes_read = len(bytes_read)
    if (num_bytes_read % 100 == 0):
        print("%d bytes read" % num_bytes_read)

output_filename = args.file.format(datetime.now().strftime('%Y%m%d%H%M%S'))
print("Read %d bytes, writing to file %s" % (len(bytes_read), output_filename))
open(output_filename, 'wb').write(bytes_read)
