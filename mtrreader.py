# From http://ttime.no/rs232.pdf
#
# MESSAGE DESCRIPTION:
# ====================
#
# MTR--datamessage
# ---------------
# Fieldname        # bytes
# Preamble         4 FFFFFFFF(hex) (4 "FF"'s never occur "inside" a message).
#                    (Can be used to "resynchronize" logic if a connection is
#                    broken)
# Package-size     1 number of bytes excluding preamble (=230)
# Package-type     1 'M' as "MTR-datamessage"
# MTR-id           2 Serial number of MTR2; Least significant byte first
# Timestamp        6 Binary Year, Month, Day, Hour, Minute, Second
# TS-milliseconds  2 Milliseconds NOT YET USED, WILL BE 0 IN THIS VERSION
# Package#         4 Binary Counter, from 1 and up; Least sign byte first
# Card-id          3 Binary, Least sign byte first
# Producweek       1 0-53 ; 0 when package is retrived from "history"
# Producyear       1 94-99,0-..X ; 0 when package is retrived from "history"
# ECardHeadSum     1 Headchecksum from card; 0 when package is retrived from
#                    "history"
# The following fields are repeated 50 times:
#   CodeN          1 ControlCode; unused positions have 0
#   TimeN          2 Time binary seconds. Least sign. first, Most sign. last;
#                    unused:0
# ASCII-string    56 Various info depending on ECard-type; 20h (all spaces)
#                    when retr. from "history" (See ASCII-String)
# Checksum         1 Binary SUM (MOD 256) of all bytes including Preamble
# NULL-Filler      1 Binary 0 (to avoid potential 5 FF's. Making it easier to
#                    hunt PREAMBLE
# ---------------------------------------
# Size           234
#
# Status-message
# --------------
# Fieldname            # bytes
# Preamble             4 FFFFFFFF(hex) (FFFFFFFF never occur elsewhere within
#                        a frame).
# Package-size         1 number of bytes excluding preamble (=55)
# Package-type         1 'S' as "Status-message" (0x53)
# MTR-id               2 Serial number of MTR2.
# CurrentTime          6 Binary Year, Month, Day, Hour, Minute, Second
# CurrentMilliseconds  2 Milliseconds NOT YET USED, WILL BE 0 IN THIS VERSION
# BatteryStatus        1 1 if battery low. 0 if battery OK.
# RecentPackage#       4 if this is 0, then ALL following # should be ignored!
# OldestPackage#       4 note: If RecentPack==0 then this is still 1! meaning:
#                        Number of packages in MTR is
#                        "RecentPackage# - OldestPackage# + 1"
# CurrentSessionStart# 4 Current session is from here to RecentPackage
#                        (if NOT = 0)
# Prev1SessStart#      4 Prev session was from Prev1SessStart# to
#                        CurrentSessionStart# - 1
# Prev2SessStart#      4
# Prev3SessStart#      4
# Prev4SessStart#      4
# Prev5SessStart#      4
# Prev6SessStart#      4
# Prev7SessStart#      4
# Checksum             1 Binary SUM (MOD 256) of all bytes including Preamble
# NULL-Filler          1 Binary 0 (to avoid potential 5 FF's. Making it easier
#                        to hunt PREAMBLE
# ---------------------------------------
# Size                59

import logging

logger = logging.getLogger()


def extend_with(old_items, new_items):
    old_items.extend(new_items)
    return new_items


def checksum_of(message_bytes):
    return sum(message_bytes) % 256


class MtrReader:

    def __init__(self, serial_port):
        self.serial_port = serial_port

    def send_status_command(self):
        self.serial_port.write(b'/ST')

    def send_spool_all_command(self):
        self.serial_port.write(b'/SA')

    def receive(self):
        messages = []
        timed_out = False
        PREAMBLE = b'\xFF\xFF\xFF\xFF'
        while not timed_out:
            preamble_buffer = bytearray()
            while preamble_buffer != PREAMBLE:
                if len(preamble_buffer) == len(PREAMBLE):
                    # make room for incoming byte
                    preamble_buffer.pop(0)

                bytes_read_waiting = self.serial_port.read()
                timed_out = len(bytes_read_waiting) == 0
                if timed_out:
                    logger.debug(
                            'Timed out, returning %d messages', len(messages))
                    return messages

                preamble_buffer.extend(bytes_read_waiting)
                logger.debug(
                        'Byte read waiting (hex): %s '
                        '(current preamble buffer: %s)',
                        bytes_read_waiting.hex(),
                        preamble_buffer.hex())

            logger.debug('Saw preable, start package parsing')
            message_bytes = bytearray()
            message_bytes.extend(preamble_buffer)

            package_size_numbytes = 1
            package_type_numbytes = 1
            package_size = int.from_bytes(
                    extend_with(
                        message_bytes,
                        self.serial_port.read(package_size_numbytes)),
                    'little')
            package_type = int.from_bytes(
                    extend_with(
                        message_bytes,
                        self.serial_port.read(package_type_numbytes)),
                    'little')

            num_remaining_bytes_expected = (
                    package_size
                    - package_size_numbytes
                    - package_type_numbytes)
            remaining_bytes = self.serial_port.read(
                    num_remaining_bytes_expected)
            if len(remaining_bytes) < num_remaining_bytes_expected:
                logger.warning('Did not receive expected number of bytes')
                continue
            message_bytes.extend(remaining_bytes)

            msg = None
            if (package_type == ord('M')):
                msg = MtrDataMessage(message_bytes)
            elif package_type == ord('S'):
                msg = MtrStatusMessage(message_bytes)
            else:
                logger.warning('Got unsupported package type %d', package_type)
                continue

            logger.info(
                    "Got message number %d (hex): %s",
                    len(messages) + 1, message_bytes.hex())
            if not msg.is_checksum_valid():
                logger.warning("Message has incorrect checksum")
                continue

            messages.append(msg)

        return messages


class MtrStatusMessage:

    def __init__(self, message_bytes):
        self.message_bytes = message_bytes

    def mtr_id(self):
        return int.from_bytes(self.message_bytes[6:8], 'little')

    def timestamp_year(self):
        return int.from_bytes(self.message_bytes[8:9], 'little')

    def timestamp_month(self):
        return int.from_bytes(self.message_bytes[9:10], 'little')

    def timestamp_day(self):
        return int.from_bytes(self.message_bytes[10:11], 'little')

    def timestamp_hours(self):
        return int.from_bytes(self.message_bytes[11:12], 'little')

    def timestamp_minutes(self):
        return int.from_bytes(self.message_bytes[12:13], 'little')

    def timestamp_seconds(self):
        return int.from_bytes(self.message_bytes[13:14], 'little')

    def timestamp_milliseconds(self):
        return int.from_bytes(self.message_bytes[14:16], 'little')

    def battery_status(self):
        return int.from_bytes(self.message_bytes[16:17], 'little')

    # package number fields not supported (yet)

    def is_checksum_valid(self):
        checksum = int.from_bytes(self.message_bytes[57:58], 'little')
        # calculate checksum for message bytes up until checksum
        calculated_checksum = checksum_of(self.message_bytes[:57])
        logger.debug(
                "Calculated checksum %d, read %d",
                calculated_checksum, checksum)
        return checksum == calculated_checksum


class MtrDataMessage:

    def __init__(self, message_bytes):
        self.message_bytes = message_bytes

    def mtr_id(self):
        return int.from_bytes(self.message_bytes[6:8], 'little')

    def timestamp_year(self):
        return int.from_bytes(self.message_bytes[8:9], 'little')

    def timestamp_month(self):
        return int.from_bytes(self.message_bytes[9:10], 'little')

    def timestamp_day(self):
        return int.from_bytes(self.message_bytes[10:11], 'little')

    def timestamp_hours(self):
        return int.from_bytes(self.message_bytes[11:12], 'little')

    def timestamp_minutes(self):
        return int.from_bytes(self.message_bytes[12:13], 'little')

    def timestamp_seconds(self):
        return int.from_bytes(self.message_bytes[13:14], 'little')

    def timestamp_milliseconds(self):
        return int.from_bytes(self.message_bytes[14:16], 'little')

    def packet_num(self):
        return int.from_bytes(self.message_bytes[16:20], 'little')

    def card_id(self):
        return int.from_bytes(self.message_bytes[20:23], 'little')

    # product week (1 byte)
    # product year (1 byte)
    # ecard head checksum (1 byte)

    def splits(self):
        splits = []
        splits_offset = 26
        code_numbytes = 1
        time_numbytes = 2
        split_numbytes = code_numbytes + time_numbytes
        for split_index in range(50):
            code_offset = splits_offset + split_index * split_numbytes
            time_offset = code_offset + code_numbytes
            code = int.from_bytes(
                    self.message_bytes[code_offset:code_offset+code_numbytes],
                    'little')
            time = int.from_bytes(
                    self.message_bytes[time_offset:time_offset+time_numbytes],
                    'little')
            splits.append((code, time))
        return splits

    def ascii_string(self):
        return self.message_bytes[176:232].decode('ascii')

    def is_checksum_valid(self):
        checksum = int.from_bytes(self.message_bytes[232:233], 'little')
        # calculate checksum for message bytes up until checksum
        calculated_checksum = checksum_of(self.message_bytes[:232])
        logger.debug(
                "Calculated checksum %d, read %d",
                calculated_checksum, checksum)
        return checksum == calculated_checksum
