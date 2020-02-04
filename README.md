# About

mtr-log-extractor extracts timing data (logs) from Emit Mini Time Recorder
(MTR) units commonly used in orienteering races. Extracts are uploaded them to
a destination such as Dropbox.

The intended use is for in-the-field extraction by non-technical race
organizers using a simple system such as a Raspberry Pi. Uploading the log over
WiFi or the mobile network allows more technical personnel to post-process the
timing data into split times and results without physical access to the
time-recording unit.

[tTime](http://ttime.no) is a GUI tool for performing the same kind of extract
and many features for further processing. The motivation for mtr-log-extractor
is simply the ability to extract and upload timing data with a minimal amount
of user interaction.


# Usage

_Note: See [the Raspberry Pi guide](raspberry-pi-guide/README.md) for
instructions on running on a Raspberry Pi with automatic extraction when the
MTR is connected._

mtr-log-extractor is run from source so download the source code.

Create Python (3.7) virtual environment and install dependencies:

    python3 -m venv venv
    source venv/bin/activate
    pip install pyserial requests dropbox

Find the MTR device name by having `dmesg` running while
connecting. For example, the device name could be /dev/ttyUSB4.

To upload to a server with a plain HTTP POST from submission:

    ./mtr-log-extractor.py -p /dev/ttyUSB4 -d http://example.org/

To upload to Dropbox, log in to Dropbox, create an App in the App Console and
generate a token for it. Save the token in a file. Run with:

    ./mtr-log-extractor.py -p /dev/ttyUSB4 -d dropbox ../dropbox.token

Logs are written to syslog (facility local0) by default.

Run `./mtr-log-extractor.py -h` for option details.


# Development

Run automated tests (find logs in testoutput/):

    python -m unittest discover tests

Check code style:

    sudo pip3 install flake8
    flake8


## Running without physical MTR

Setup serial port loop:

    sudo apt-get install socat
    ./devutil-serialportloop.sh

Start test http upload server:

    mkdir ../http-upload-dir
    ./devutil-http-upload-server.py -d ../http-upload-dir

Start mock MTR on one port:

    ./devutil-mock-mtr.py /dev/pts/4

or with data in file (recorded with devutil-recordmtrdata.py):

    ./devutil-mock-mtr.py /dev/pts/4 -f mtr.bin

Start program on the other port:

    ./mtr-log-extractor.py -p /dev/pts/3 -d http://localhost:8080/ -l log.log

or, using dropbox:

    ./mtr-log-extractor.py -p /dev/pts/3 -d dropbox ../dropbox.token -l log.log


## Utilities

`devutil-http-upload-server.py`: Starts a local HTTP server accepting uploads

`devutil-mock-mtr.py`: Script that listens to a serial port and acts like an MTR

`devutil-recordmtrdata.py`: Extracts and saves MTR data in raw/binary form

`devutil-serialportloop.sh`: Creates a virtual serial port pair (using `socat`)
