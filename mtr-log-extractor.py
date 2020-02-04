#!/usr/bin/env python3

import argparse
import logging
import logging.handlers
import os
import serial
import sys
from datetime import datetime, timedelta
import requests
import dropbox
import time

import mtrreader
import mtrlog


def create_argparser():
    argparser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    argparser.add_argument(
            '-p',
            '--serial-port',
            default='/dev/ttyMTR',
            help="Serial port device of MTR")
    argparser.add_argument(
            '-t',
            '--serial-port-polling-timeout',
            metavar='TIMEOUT',
            type=int,
            help=(
                'Number of seconds to spend polling MTR for status before '
                'giving up. (Exits with status code {} on timeout.)'.format(
                    exit_code_serial_port_unresponsive)))
    argparser.add_argument(
            '-f',
            '--output-file-name',
            default="mtr-{}.log",
            help=(
                'Name of output file in the "MTR log file" format read by '
                'tTime (See http://ttime.no. Format described at '
                'http://ttime.no/rs232.pdf.) '
                'A {} in the filename will be replaced with a timestamp in '
                'the ISO 8601 combined date and time basic format.'))
    argparser.add_argument(
            '-d',
            '--destination',
            nargs='+',
            metavar='DEST_ARG',
            help=(
                "Send MTR log file to a destination. Supported destinations: "
                "an HTTP URL (accepting POST form uploads) or "
                "'dropbox path/to/apitokenfile [/upload/dir]'"))
    argparser.add_argument(
            '-l',
            '--log',
            nargs='+',
            metavar='LOG_ARG',
            default=['syslog', '/dev/log', 'local0'],
            help=(
                "Configure logging. LOG_ARG can be a log file path or the "
                "default (using multiple values) 'syslog [SOCKET] [FACILITY]' "
                "where SOCKET is '/dev/log' and FACILITY is 'local0' by "
                "default."))
    return argparser


def initialize_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    if args.log[0] == 'syslog':
        address = args.log[1] if len(args.log) >= 2 else '/dev/log'
        facility = args.log[2] if len(args.log) >= 3 else 'local0'
        syslog_handler = logging.handlers.SysLogHandler(
                address=address,
                facility=facility)
        syslog_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logger.addHandler(syslog_handler)
    else:
        log_file = args.log[0]
        file_handler = logging.handlers.WatchedFileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logger.addHandler(file_handler)
    return logger


def should_poll_mtr_for_status(timeout_uptime):
    no_timeout_set = timeout_uptime is None
    return no_timeout_set or uptime() < timeout_uptime


def uptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
        return timedelta(seconds=uptime_seconds)


def is_status_response(messages):
    return (len(messages) == 1
            and isinstance(messages[0], mtrreader.MtrStatusMessage))


def serial_port_with_live_mtr(
        port, polling_timeout_secs, retry_wait_time_secs, serial_timeout_secs):
    if polling_timeout_secs is None:
        polling_timeout_uptime = None
        logger.info("Polling serial port %s forever", port)
    else:
        polling_timeout_uptime = (
                uptime() + timedelta(seconds=polling_timeout_secs))
        logger.info(
                "Polling serial port %s for status for %s seconds (until "
                "uptime is %s)",
                port, polling_timeout_secs, polling_timeout_uptime)

    while should_poll_mtr_for_status(polling_timeout_uptime):
        try:
            serial_port = serial.Serial(
                    port=port, baudrate=9600, timeout=serial_timeout_secs)

            logger.info(
                    "Opened serial port %s, sending 'status' command '/ST'...",
                    port)
            mtr_reader_status = mtrreader.MtrReader(serial_port)
            mtr_reader_status.send_status_command()
            messages = mtr_reader_status.receive()
            if is_status_response(messages):
                logger.info(
                        "MTR status response received, ID is %d",
                        messages[0].mtr_id())
                return serial_port

        except serial.SerialException:
            # Just log the error, the device could have been suddenly
            # connected and could be responding next time.
            logger.info((
                "MTR status polling failed; Serial port %s was closed or "
                "couldn't be opened"), port)

        logger.info(
                "Retrying MTR status polling in %d seconds",
                retry_wait_time_secs)
        time.sleep(retry_wait_time_secs)

    logger.info(
            "No status response received on serial port %s in %d seconds. "
            "Giving up.",
            port, polling_timeout_secs)
    return None


def write_mtr_log_file(log_lines, output_filename):
    with open(output_filename, 'wb') as output_file:
        for log_line in log_lines:
            output_file.write(("%s\n" % log_line).encode('utf-8'))
        logger.info("Wrote log file %s", output_filename)
    return output_filename


def upload_mtr_log_file_dropbox(log_file_name, upload_dir, token):
    dbx = dropbox.Dropbox(token)
    with open(log_file_name, 'rb') as f:
        upload_filename = os.path.basename(f.name)
        dbx.files_upload(f.read(), upload_dir + "/" + upload_filename)
    return


def upload_mtr_log_file_http(log_file_name, url):
    with open(log_file_name, 'rb') as f:
        requests.post(url, files={'file': f})
    return


exit_code_serial_port_unresponsive = 100

argparser = create_argparser()
args = argparser.parse_args()
logger = initialize_logging()

serial_port = serial_port_with_live_mtr(
        args.serial_port,
        polling_timeout_secs=args.serial_port_polling_timeout,
        retry_wait_time_secs=5,
        serial_timeout_secs=3)
if serial_port is None:
    logger.info(
            "Serial port is unresponsive, exiting... (status=%d)",
            exit_code_serial_port_unresponsive)
    sys.exit(exit_code_serial_port_unresponsive)

mtr_reader = mtrreader.MtrReader(serial_port)
destination_args = args.destination
dropbox_api_token = None
if destination_args[0] == 'dropbox':
    if len(destination_args) < 2:
        argparser.error(
                "Missing second destination argument value for "
                "destination 'dropbox': path to file with Dropbox API token")
    try:
        dropbox_token_file = destination_args[1]
        with open(dropbox_token_file, 'r') as tf:
            try:
                dropbox_api_token = tf.read().strip()
                if len(dropbox_api_token) == 0:
                    error_message = (
                            "Dropbox token file '%s' is empty"
                            % dropbox_token_file)
                    logger.error(error_message)
                    argparser.error(error_message)
            except IOError:
                error_message = (
                        "Could not read contents of Dropbox token file '%s'"
                        % dropbox_token_file)
                logger.error(error_message)
                argparser.error(error_message)

    except OSError:
        error_message = (
                "Could not open Dropbox token file '%s'"
                % dropbox_token_file)
        logger.error(error_message)
        argparser.error(error_message)

output_filename = (
        args.output_file_name.format(datetime.now().strftime('%Y%m%dT%H%M%S')))

mtr_reader.send_spool_all_command()
data_messages = mtr_reader.receive()
datetime_extracted = datetime.now()
log_lines = mtrlog.MtrLogFormatter().format_all(
        data_messages, datetime_extracted)
mtr_log_file_name = write_mtr_log_file(log_lines, output_filename)

if destination_args[0] == 'dropbox':
    try:
        upload_dir = ""
        if len(destination_args) >= 3:
            upload_dir = destination_args[2]
            if not upload_dir.startswith("/"):
                upload_dir = "/" + upload_dir
        upload_mtr_log_file_dropbox(
                mtr_log_file_name, upload_dir, dropbox_api_token)
    except Exception:
        logger.exception("Error when uploading MTR log file to Dropbox")
else:
    try:
        upload_mtr_log_file_http(mtr_log_file_name, destination_args[0])
    except Exception:
        logger.exception(
                "Error when uploading MTR log file using plain HTTP POST")
