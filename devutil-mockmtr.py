#!/usr/bin/env python3

import argparse
import random
import serial
from datetime import datetime, timedelta
from tests.testmtrreader import MtrDataBytesBuilder
import csv


def create_argparser():
    argparser = argparse.ArgumentParser(
            description=(
                "Mock MTR supporting spool-all command ('/SA'). "
                "Responds with data messages in binary file to serial port."))
    argparser.add_argument('port', help='Serial port identifier')
    argparser.add_argument(
            '-n', type=int, default=100, help='Number of messages to generate')
    argparser.add_argument(
            '-f', '--file',
            help=(
                "Don't generate messages, but read from file. "
                '(File can be created with devutil-recordmtrdata.py.)'))
    argparser.add_argument(
            '--file-format',
            choices=['mtrbinary', 'mtrlogfile'], default='mtrbinary',
            help=(
                "Format of input file. 'mtrbinary' is the format emitted from "
                "physical MTR units. 'mtrlogfile' is a textual "
                "representation used in official programming interfaces and "
                "the output format of MTR Log Extractor."))
    argparser.add_argument(
            '-v', '--verbose', action='store_true', help='Verbose output')
    return argparser


def is_command(cmd_bytes):
    return cmd_bytes == b'/ST' or cmd_bytes == b'/SA'


def listen(serial_port):
    command_buffer = bytearray()
    COMMAND_LENGTH = 3
    print("Listening for command on {} ...".format(serial_port.name))
    while not is_command(command_buffer):
        if len(command_buffer) == COMMAND_LENGTH:
            # make room for incoming byte by removing oldest
            command_buffer.pop(0)
        command_buffer.extend(serial_port.read())
    print("Received command {}".format(command_buffer))
    return command_buffer


def respond_status(serial_port, mtr_id):
    now = datetime.now()
    data = bytearray()
    data.extend(b'\xFF\xFF\xFF\xFF')  # preamble
    data.append(55)  # status message length
    data.append(ord('S'))  # status message type
    data.extend(mtr_id.to_bytes(2, 'little'))
    data.append(now.year % 100)
    data.append(now.month)
    data.append(now.day)
    data.append(now.hour)
    data.append(now.minute)
    data.append(now.second)
    data.extend(b'\x00\x00')  # ms
    data.append(0)  # battery status (0=ok, 1=low)
    data.extend(b'\x00\x00\x00\x00')  # recent pkgnum
    data.extend(b'\x00\x00\x00\x00')  # oldest pkgnum
    data.extend(b'\x00\x00\x00\x00')  # curr sess start
    data.extend(b'\x00\x00\x00\x00')  # prev1 sess start
    data.extend(b'\x00\x00\x00\x00')  # prev2 sess start
    data.extend(b'\x00\x00\x00\x00')  # prev3 sess start
    data.extend(b'\x00\x00\x00\x00')  # prev4 sess start
    data.extend(b'\x00\x00\x00\x00')  # prev5 sess start
    data.extend(b'\x00\x00\x00\x00')  # prev6 sess start
    data.extend(b'\x00\x00\x00\x00')  # prev7 sess start
    data.append(sum(data) % 256)
    data.append(0)
    num_bytes_written = serial_port.write(data)
    print("Wrote {} bytes".format(num_bytes_written))


def respond_with_file(serial_port, source_filename, source_fileformat):
    if source_fileformat == 'mtrbinary':
        respond_with_file_mtrbinary(serial_port, source_filename)
    elif source_fileformat == 'mtrlogfile':
        respond_with_file_mtrlogfile(serial_port, source_filename)
    else:
        print("Unexpected file format '{}'".format(source_fileformat))


def respond_with_file_mtrbinary(serial_port, source_filename):
    with open(source_filename, 'rb') as source_file:
        print("Opened binary file {}".format(source_filename))
        data = source_file.read()
        print("Read {} bytes".format(len(data)))
        num_bytes_written = serial_port.write(data)
        print("Wrote {} bytes".format(num_bytes_written))


def respond_with_file_mtrlogfile(serial_port, source_filename):
    with open(source_filename, 'r', encoding='ascii') as source_file:
        print("Opened MTR log file {}".format(source_filename))
        parsed_data = csv.DictReader(
            source_file,
            fieldnames=[
                'package_type',
                'zero',
                'mtr_id',
                'card_id_string',
                'datetime_extracted_string',
                'datetime_read_string',
                'card_id',
                'product_week',
                'product_year'
            ], restkey='splits_and_more')
        line_num = 0
        for parsed_data_line in parsed_data:
            line_num = line_num + 1
            package_type = parsed_data_line['package_type']
            if package_type != 'M':
                print(
                    "Encountered unknown package type {} at line {}"
                    .format(package_type, line_num))
                continue
            mtr_id = int(parsed_data_line['mtr_id'].strip())
            card_id = int(parsed_data_line['card_id'].strip())
            datetime_read = datetime.strptime(
                parsed_data_line['datetime_read_string'],
                '%d.%m.%y %H:%M:%S.%f')
            splits_and_more = parsed_data_line['splits_and_more']
            if len(splits_and_more) < 100:
                print(
                    "Expected 50 split control/time pairs; found {} at line {}"
                    .format(len(splits_and_more), line_num))
                continue

            splits = []
            for i in range(0, 98, 2):
                control = int(splits_and_more[i])
                time = int(splits_and_more[i+1])
                splits.append((control, time))

            package_num = int(splits_and_more[100])

            num_bytes_written = serial_port.write(
                mtr_bytes(
                    mtr_id=mtr_id, card_id=card_id, splits=splits,
                    datetime_read=datetime_read, package_num=package_num))
            print(
                "Wrote message at line {} (package number {}, {} bytes)"
                .format(line_num, package_num, num_bytes_written))


def respond_with_generated(serial_port, mtr_id, n):
    print("Generating {} messages".format(n))

    now = datetime.now()
    course_a = [0, 31, 32, 33, 34, 35, 102, 103, 104, 249]
    course_b = [0, 31, 32, 33, 35, 103, 104, 249]
    course_c = [0, 65, 66, 67, 60, 61, 62, 249]
    courses = [course_a, course_b, course_c]

    for i in range(1, n+1):
        card_id = random.randint(
                1, int.from_bytes(bytes(b'\xFF\xFF\xFF'), 'little'))
        splits = random_splits_for_course(random.choice(courses))
        datetime_read = now - timedelta(minutes=(n - i)*2)
        message_bytes = mtr_bytes(mtr_id, card_id, splits, datetime_read, i)
        if is_verbose:
            print(message_bytes.hex())
        num_bytes_written = serial_port.write(message_bytes)
        if is_verbose:
            print("{} bytes sent".format(num_bytes_written))


def mtr_bytes(mtr_id, card_id, splits, datetime_read, package_num):
    return MtrDataBytesBuilder(
            mtr_id, card_id, splits, datetime_read, package_num
            ).to_bytes()


def random_splits_for_course(course):
    split_times = [0]
    for j in range(1, len(course)):
        split_times.append(split_times[j-1] + random.randint(60, 900))
    return list(zip(course, split_times))


args = create_argparser().parse_args()
is_verbose = args.verbose
test_serial = serial.Serial(port=args.port, baudrate=9600)
while True:
    cmd = listen(test_serial)
    mtr_id = random.randint(1, int.from_bytes(bytes(b'\xFF\xFF'), 'little'))
    if cmd == b'/ST':
        respond_status(test_serial, mtr_id)
    elif cmd == b'/SA':
        if args.file:
            respond_with_file(test_serial, args.file, args.file_format)
        else:
            respond_with_generated(test_serial, mtr_id, args.n)
