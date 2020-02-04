from datetime import datetime, timedelta
import serial
import unittest
import os
import logging

import mtrlog
import mtrreader


def initialize_logging(log_dir, log_file):
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
            filename=os.path.join(log_dir, log_file),
            level=logging.DEBUG)


class FakeMtr:

    def __init__(self, serial_port):
        self.serial_port = serial_port

    def send_message(self, data_message):
        self.serial_port.write(data_message)


class MtrStatusBytesBuilder():

    def __init__(
            self,
            mtr_id,
            current_datetime=datetime.now(),
            battery_status=0):
        self._mtr_id = mtr_id
        self._current_datetime = current_datetime
        self._battery_status = battery_status

    @property
    def mtr_id(self):
        return self._mtr_id

    @mtr_id.setter
    def mtr_id(self, mtr_id):
        self._mtr_id = mtr_id

    @property
    def current_datetime(self):
        return self._current_datetime

    @current_datetime.setter
    def current_datetime(self, current_datetime):
        self._current_datetime = current_datetime

    @property
    def battery_status(self):
        return self._battery_status

    @battery_status.setter
    def battery_status(self, battery_status):
        self._battery_status = battery_status

    def to_bytes(self):
        data = bytearray(b'\xFF\xFF\xFF\xFF')  # preamble
        data.append(55)
        data.append(ord('S'))
        data.extend(self._mtr_id.to_bytes(2, 'little'))
        data.append(self._current_datetime.year % 100)
        data.append(self._current_datetime.month)
        data.append(self._current_datetime.day)
        data.append(self._current_datetime.hour)
        data.append(self._current_datetime.minute)
        data.append(self._current_datetime.second)
        data.extend((0).to_bytes(2, 'little'))  # timestamp-ms
        data.append(self._battery_status % 256)  # battery status
        data.extend((0).to_bytes(4, 'little'))  # recent package num (n/a)
        data.extend((0).to_bytes(4, 'little'))  # oldest package num (n/a)
        data.extend((0).to_bytes(4, 'little'))  # current session start (n/a)
        data.extend((0).to_bytes(4, 'little'))  # prev 1 session start (n/a)
        data.extend((0).to_bytes(4, 'little'))  # prev 2 session start (n/a)
        data.extend((0).to_bytes(4, 'little'))  # prev 3 session start (n/a)
        data.extend((0).to_bytes(4, 'little'))  # prev 4 session start (n/a)
        data.extend((0).to_bytes(4, 'little'))  # prev 5 session start (n/a)
        data.extend((0).to_bytes(4, 'little'))  # prev 6 session start (n/a)
        data.extend((0).to_bytes(4, 'little'))  # prev 7 session start (n/a)
        data.append(sum(data) % 256)  # checksum
        data.append(0)  # 0-filler
        return data


class MtrDataBytesBuilder():

    def __init__(
            self,
            mtr_id,
            card_id,
            splits=[],
            datetime_read=datetime.now(),
            package_number=1,
            ascii_string=""):
        self._mtr_id = mtr_id
        self._datetime_read = datetime_read
        self._package_number = package_number
        self._card_id = card_id
        self._splits = splits
        self._ascii_string = ascii_string

    @property
    def mtr_id(self):
        return self._mtr_id

    @mtr_id.setter
    def mtr_id(self, mtr_id):
        self._mtr_id = mtr_id

    @property
    def card_id(self):
        return self._card_id

    @card_id.setter
    def card_id(self, card_id):
        self._card_id = card_id

    @property
    def splits(self):
        return self._splits

    @splits.setter
    def splits(self, splits):
        self._splits = splits

    @property
    def datetime_read(self):
        return self._datetime_read

    @datetime_read.setter
    def datetime_read(self, datetime_read):
        self._datetime_read = datetime_read

    @property
    def package_number(self):
        return self._package_number

    @package_number.setter
    def package_number(self, package_number):
        self._package_number = package_number

    @property
    def ascii_string(self):
        return self._ascii_string

    @ascii_string.setter
    def ascii_string(self, ascii_string):
        self._ascii_string = ascii_string

    def to_bytes(self):
        data = bytearray(b'\xFF\xFF\xFF\xFF')  # preamble
        data.append(230)
        data.append(ord('M'))
        data.extend(self._mtr_id.to_bytes(2, 'little'))
        data.append(self._datetime_read.year % 100)
        data.append(self._datetime_read.month)
        data.append(self._datetime_read.day)
        data.append(self._datetime_read.hour)
        data.append(self._datetime_read.minute)
        data.append(self._datetime_read.second)
        data.extend((0).to_bytes(2, 'little'))  # timestamp-ms
        data.extend(self._package_number.to_bytes(4, 'little'))
        data.extend(self._card_id.to_bytes(3, 'little'))
        data.append(0)  # product week (0 when spooling)
        data.append(0)  # product year (0 when spooling)
        data.append(0)  # ecard headchecksum (0 when spooling)
        num_splits_missing = max(0, 50 - len(self._splits))
        splits_exact_length = (
                self._splits[0:50] + num_splits_missing * [(0, 0)])
        for (control_code, time_at_control) in splits_exact_length:
            data.append(control_code)
            data.extend(time_at_control.to_bytes(2, 'little'))
        data.extend(self._ascii_string.ljust(56).encode('ascii'))
        data.append(sum(data) % 256)  # checksum
        data.append(0)  # 0-filler
        return data


class TestMtrReader(unittest.TestCase):

    def setUp(self):
        self.serial_loop = serial.serial_for_url("loop://", timeout=1)
        self.fake_mtr = FakeMtr(self.serial_loop)
        self.mtr_reader = mtrreader.MtrReader(self.serial_loop)
        self.data_bytes_builder = MtrDataBytesBuilder(
                mtr_id=1,
                card_id=546,
                splits=[(0, 0), (249, 60)],
                datetime_read=datetime.now(),
                package_number=1)
        self.status_bytes_builder = MtrStatusBytesBuilder(mtr_id=1)

    def test_send_status_command(self):
        self.mtr_reader.send_status_command()
        self.assertEqual(self.serial_loop.read(3), b'/ST')

    def test_send_spool_all_command(self):
        self.mtr_reader.send_spool_all_command()
        self.assertEqual(self.serial_loop.read(3), b'/SA')

    def test_receive_none(self):
        self.mtr_reader.send_spool_all_command()
        self.fake_mtr.send_message(bytes())
        data_messages = self.mtr_reader.receive()
        self.assertEqual(data_messages, [])

    def test_spool_all_receive_one(self):
        self.mtr_reader.send_spool_all_command()
        self.fake_mtr.send_message(self.data_bytes_builder.to_bytes())
        data_messages = self.mtr_reader.receive()
        self.assertEqual(len(data_messages), 1)

    def test_spool_all_receive_two(self):
        self.mtr_reader.send_spool_all_command()
        self.fake_mtr.send_message(self.data_bytes_builder.to_bytes())
        self.data_bytes_builder.package_number = 2
        self.fake_mtr.send_message(self.data_bytes_builder.to_bytes())
        data_messages = self.mtr_reader.receive()
        self.assertEqual(len(data_messages), 2)

    def test_receive_status(self):
        self.mtr_reader.send_status_command()
        self.status_bytes_builder.mtr_id = 2
        self.fake_mtr.send_message(self.status_bytes_builder.to_bytes())
        status_message = self.mtr_reader.receive()[0]
        self.assertEqual(status_message.mtr_id(), 2)


class TestMtrStatusMessage(unittest.TestCase):

    def setUp(self):
        self.bytes_builder = MtrStatusBytesBuilder(mtr_id=1)

    def test_mtr_id(self):
        self.bytes_builder.mtr_id = 33145
        msg = mtrreader.MtrStatusMessage(self.bytes_builder.to_bytes())
        self.assertEqual(msg.mtr_id(), 33145)

    def test_current_datetime(self):
        now = datetime.now()
        self.bytes_builder.current_datetime = now
        msg = mtrreader.MtrDataMessage(self.bytes_builder.to_bytes())
        self.assertEqual(msg.timestamp_year(), now.year % 100)
        self.assertEqual(msg.timestamp_month(), now.month)
        self.assertEqual(msg.timestamp_day(), now.day)
        self.assertEqual(msg.timestamp_hours(), now.hour)
        self.assertEqual(msg.timestamp_minutes(), now.minute)
        self.assertEqual(msg.timestamp_seconds(), now.second)
        self.assertEqual(msg.timestamp_milliseconds(), 0)

    def test_battery_status(self):
        self.bytes_builder.battery_status = 1
        msg = mtrreader.MtrStatusMessage(self.bytes_builder.to_bytes())
        self.assertEqual(msg.battery_status(), 1)

    def test_checksum_valid(self):
        msg = mtrreader.MtrStatusMessage(self.bytes_builder.to_bytes())
        self.assertTrue(msg.is_checksum_valid())

    def test_checksum_not_valid_if_incorrect(self):
        message_bytes = self.bytes_builder.to_bytes()
        checksum_offset = len(message_bytes) - 2
        current_checksum = message_bytes[checksum_offset]
        message_bytes[checksum_offset] = current_checksum + 1 % 256
        msg = mtrreader.MtrStatusMessage(message_bytes)
        self.assertFalse(msg.is_checksum_valid())


class TestMtrDataMessage(unittest.TestCase):

    def setUp(self):
        self.bytes_builder = MtrDataBytesBuilder(
                mtr_id=1,
                card_id=546,
                splits=[(0, 0), (249, 60)],
                datetime_read=datetime.now(),
                package_number=1)

    def test_mtr_id(self):
        self.bytes_builder.mtr_id = 33145
        msg = mtrreader.MtrDataMessage(self.bytes_builder.to_bytes())
        self.assertEqual(msg.mtr_id(), 33145)

    def test_datetime_read(self):
        now = datetime.now()
        self.bytes_builder.datetime_read = now
        msg = mtrreader.MtrDataMessage(self.bytes_builder.to_bytes())
        self.assertEqual(msg.timestamp_year(), now.year % 100)
        self.assertEqual(msg.timestamp_month(), now.month)
        self.assertEqual(msg.timestamp_day(), now.day)
        self.assertEqual(msg.timestamp_hours(), now.hour)
        self.assertEqual(msg.timestamp_minutes(), now.minute)
        self.assertEqual(msg.timestamp_seconds(), now.second)
        self.assertEqual(msg.timestamp_milliseconds(), 0)

    def test_packet_num(self):
        self.bytes_builder.package_number = 39
        msg = mtrreader.MtrDataMessage(self.bytes_builder.to_bytes())
        self.assertEqual(msg.packet_num(), 39)

    def test_card_id(self):
        self.bytes_builder.card_id = 131586
        msg = mtrreader.MtrDataMessage(self.bytes_builder.to_bytes())
        self.assertEqual(msg.card_id(), 131586)

    def test_splits(self):
        input_splits = [(0, 0), (31, 60), (32, 120), (33, 180), (249, 240)]
        self.bytes_builder.splits = input_splits

        msg = mtrreader.MtrDataMessage(self.bytes_builder.to_bytes())
        output_splits = msg.splits()

        expected_splits = input_splits + 45 * [(0, 0)]
        self.assertEqual(output_splits, expected_splits)

    def test_ascii_string(self):
        self.bytes_builder.ascii_string = "This is a test"
        msg = mtrreader.MtrDataMessage(self.bytes_builder.to_bytes())
        self.assertEqual(msg.ascii_string(), "This is a test".ljust(56))

    def test_checksum_valid(self):
        msg = mtrreader.MtrDataMessage(self.bytes_builder.to_bytes())
        self.assertTrue(msg.is_checksum_valid())

    def test_checksum_not_valid_if_incorrect(self):
        message_bytes = self.bytes_builder.to_bytes()
        checksum_offset = len(message_bytes) - 2
        current_checksum = message_bytes[checksum_offset]
        message_bytes[checksum_offset] = (current_checksum + 1) % 256
        msg = mtrreader.MtrDataMessage(message_bytes)
        self.assertFalse(msg.is_checksum_valid())


class TestMtrLogFormatter(unittest.TestCase):

    def setUp(self):
        self.datetime_read = datetime.now()
        self.default_bytes_builder = MtrDataBytesBuilder(mtr_id=1, card_id=1)
        self.default_line = mtrlog.MtrLogFormatter().format(
                mtrreader.MtrDataMessage(
                    self.default_bytes_builder.to_bytes()),
                self.datetime_read)

    def test_constant_fields(self):
        self.assertEqual(self.default_line[0:4], '"M",')
        self.assertEqual(self.default_line[4:8], '"0",')

    def test_mtr_id(self):
        self.default_bytes_builder.mtr_id = 258
        new_bytes = self.default_bytes_builder.to_bytes()
        expected_line = (
                self.default_line[0:8] + '"258",' + self.default_line[12:])
        line = mtrlog.MtrLogFormatter().format(
                mtrreader.MtrDataMessage(new_bytes), self.datetime_read)
        self.assertEqual(line, expected_line)

    def test_card_id(self):
        self.default_bytes_builder.card_id = 66308
        new_bytes = self.default_bytes_builder.to_bytes()
        expected_line = (
                self.default_line[0:12]
                + '"066308",'
                + self.default_line[21:69]
                + '066308,'
                + self.default_line[76:])
        line = mtrlog.MtrLogFormatter().format(
                mtrreader.MtrDataMessage(new_bytes), self.datetime_read)
        self.assertEqual(line, expected_line)

    def test_datetime_read(self):
        # subtract more than a year to get different values for all fields
        self.default_bytes_builder.datetime_read -= timedelta(
                days=366+32, hours=1, minutes=1, seconds=1)
        new_bytes = self.default_bytes_builder.to_bytes()
        new_datetime_read = (
                self.default_bytes_builder.datetime_read
                .strftime('%d.%m.%y %H:%M:%S.000'))
        expected_line = (
                self.default_line[0:45]
                + ('"%s",' % new_datetime_read)
                + self.default_line[69:])
        line = mtrlog.MtrLogFormatter().format(
                mtrreader.MtrDataMessage(new_bytes), self.datetime_read)
        self.assertEqual(line, expected_line)

    def test_package_number(self):
        self.default_bytes_builder.package_number = 4660
        new_bytes = self.default_bytes_builder.to_bytes()
        expected_line = self.default_line[0:586] + '0004660'
        line = mtrlog.MtrLogFormatter().format(
                mtrreader.MtrDataMessage(new_bytes), self.datetime_read)
        self.assertEqual(line, expected_line)

    def test_splits_minimal(self):
        self.default_bytes_builder.splits = [(0, 0), (249, 60)]
        new_bytes = self.default_bytes_builder.to_bytes()
        expected_line = (
                self.default_line[0:86]
                + '000,00000,249,00060,'
                + self.default_line[106:])
        line = mtrlog.MtrLogFormatter().format(
                mtrreader.MtrDataMessage(new_bytes), self.datetime_read)
        self.assertEqual(line, expected_line)

    def test_splits_full(self):
        splits = []
        expected_split_string = ''
        for i in range(0, 50):
            control_code = i
            time_at_control = i*60
            splits.append((control_code, time_at_control))
            expected_split_string += (
                    '%03d,%05d,' % (control_code, time_at_control))
        self.default_bytes_builder.splits = splits

        new_bytes = self.default_bytes_builder.to_bytes()
        expected_line = (
                self.default_line[0:86]
                + expected_split_string
                + self.default_line[586:])
        line = mtrlog.MtrLogFormatter().format(
                mtrreader.MtrDataMessage(new_bytes), self.datetime_read)
        self.assertEqual(line, expected_line)

    def test_multiple(self):
        expected_lines = []

        self.default_bytes_builder.package_number = 101
        bytes_msg_1 = self.default_bytes_builder.to_bytes()
        expected_lines.append(self.default_line[0:586] + '0000101')

        self.default_bytes_builder.package_number = 102
        bytes_msg_2 = self.default_bytes_builder.to_bytes()
        expected_lines.append(self.default_line[0:586] + '0000102')

        messages = [
                mtrreader.MtrDataMessage(bytes_msg_1),
                mtrreader.MtrDataMessage(bytes_msg_2)]
        lines = mtrlog.MtrLogFormatter().format_all(
                messages, self.datetime_read)

        self.assertEqual(lines, expected_lines)


initialize_logging(log_dir='testoutput', log_file='testlog.log')

if __name__ == '__main__':
    unittest.main()
