#!/bin/sh

SERIAL_PORT="$1"
logger -p local0.info -t mtrservice "Starting MTR Log Extractor on port $SERIAL_PORT"
/home/pi/mtr-log-extractor/venv/bin/python3 /home/pi/mtr-log-extractor/mtr-log-extractor.py -p $SERIAL_PORT -t 120 -f /home/pi/extracts/mtr-{}.log -d dropbox /home/pi/dropbox.token
