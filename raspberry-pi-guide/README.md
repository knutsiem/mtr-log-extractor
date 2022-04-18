# Installation instructions for use on Raspberry Pi

mtr-log-extractor can be launched manually as described in the [main README](../README), but
this is not ideal in an in-the-field situation. This guide explains
installation on a Raspberry Pi with automatic launching when an MTR is
connected, connecting to the mobile network, logging configuration, status
indication via a LED and automatic shutdown to conserve battery power. The
actual Raspberry Pi used in the orignal development was powered by a [PiJuice
HAT](https://uk.pi-supply.com/products/pijuice-standard), so the installation
template files include PiJuice-specific power management. The mobile network
connection was made using a [Sixfab Raspberry Pi 4G/LTE Shield
Kit](https://sixfab.com/product/raspberry-pi-4g-lte-shield-kit/) but the
specifics of this particular hardware is abstracted into the `pon`/`poff`
commands and the `ppp` package by the installation process of the Sixfab card.

The configuration files and and scripts in this directory are to be regarded as
templates which may require modification depending on the system in use. As
they are they attempt to configure a system so that

* the extract and upload can happen with no other user interaction than
  bringing the MTR and the Raspberry Pi to a connected and powered state, and
* the MTR and the Raspberry Pi can be connected and powered in any order


## Technical solution

The udev rule in [`ftdi-mtr.rules`](ftdi-mtr.rules) triggers when an MTR is connected. The rule
starts a systemd service [`mtrlogextractor@.service`](mtrlogextractor@.service), which runs
`mtr-log-extractor.py` via [`start.sh`](start.sh). Prior to starting, [`prestart.sh`](prestart.sh) is run
to connect to the mobile network (among other things). When the service has
stopped, [`poststop.sh`](poststop.sh) is run to disconnect from the mobile network and
schedule a shutdown to conserve battery power. To avoid shutting down if the
MTR is re-connected before shutdown starts, `prestart.sh` cancels any scheduled
shutdown. The systemd service is bound to the device so that it stops if the
MTR is abruptly disconnected (proceeding to shutdown unless reconnected
before).

Another systemd service
[`mtrlogextractor-led.service`](mtrlogextractor-led.service) starts
independently and controls a LED attached via GPIO (port 24) to indicate
extract/upload status.

## Installation

Follow instructions in [main README](../README.md).

Enter dir:

    cd raspberry-pi-guide

Add udev rule:

    sudo cp ftdi-mtr.rules /etc/udev/rules.d/
    sudo udevadm control --reload

Add systemd services:

    sudo cp mtrlogextractor@.service mtrlogextractor-led.service /etc/systemd/system/
    sudo systemctl daemon-reload

Add lifecycle scripts:

    sudo mkdir /opt/mtr-log-extractor
    sudo cp prestart.sh start.sh poststop.sh pijuice-poweroff.py status-led.py /opt/mtr-log-extractor
    sudo chmod +x /opt/mtr-log-extractor/*.*

Modify scripts as necessary.

Add logging configuration:

    sudo cp mtrlogextractor.conf /etc/rsyslog.d/
