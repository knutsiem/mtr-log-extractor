import logging

logger = logging.getLogger()


class MtrLogFormatter:

    def format_all(self, data_messages, datetime_extracted):
        log_lines = []
        for data_message in data_messages:
            log_lines.append(self.format(data_message, datetime_extracted))
        return log_lines

    def format(self, msg, datetime_extracted):
        log_line = []
        log_line.append('"M"')
        log_line.append('"0"')
        log_line.append('"%d"' % msg.mtr_id())
        log_line.append('"%06d"' % msg.card_id())
        log_line.append(
                '"%s"' % datetime_extracted.strftime('%d.%m.%y %H:%M:%S.000'))
        log_line.append(
                '"%02d.%02d.%02d %02d:%02d:%02d.%03d"' % (
                    msg.timestamp_day(),
                    msg.timestamp_month(),
                    msg.timestamp_year(),
                    msg.timestamp_hours(),
                    msg.timestamp_minutes(),
                    msg.timestamp_seconds(),
                    msg.timestamp_milliseconds()))
        log_line.append('%06d' % msg.card_id())
        log_line.append('%04d' % 0)  # skipped product week
        log_line.append('%04d' % 0)  # skipped product year
        for (control_code, time_at_control) in msg.splits():
            log_line.append('%03d' % control_code)
            log_line.append('%05d' % time_at_control)
        log_line.append('%07d' % msg.packet_num())

        log_line_str = ",".join(log_line)
        logger.info("Converted message to log line format: %s", log_line_str)
        return log_line_str
