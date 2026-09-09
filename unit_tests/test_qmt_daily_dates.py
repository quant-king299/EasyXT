"""Regression fixtures for the DAT reader's timestamp validity window."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'core/qmt_local_reader.py'
spec = importlib.util.spec_from_file_location('daily_reader_under_test', PATH)
reader_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader_module)


class DailyDatesTest(unittest.TestCase):
    def read_fixture(self, dates):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.DAT'
            records = []
            for date in dates:
                records.append(struct.pack('<8I', int(date.timestamp()),
                                           10000, 11000, 9000, 10500, 0, 100, 0))
                records.append(bytes(32))
            path.write_bytes(bytes(8) + b''.join(records))
            reader = object.__new__(reader_module.QMTLocalReader)
            with patch.object(reader, 'get_file_path', return_value=path):
                return reader.read_daily_data('600519.SH')

    def test_accepts_2026_and_current_day(self):
        china = timezone(timedelta(hours=8))
        today = datetime.now(china).replace(hour=0, minute=0, second=0, microsecond=0)
        dates = [datetime(2026, 1, 5, tzinfo=china), today]
        result = self.read_fixture(dates)
        self.assertEqual(list(result.time.dt.strftime('%Y-%m-%d')),
                         sorted({date.strftime('%Y-%m-%d') for date in dates}))

    def test_rejects_implausible_future_record(self):
        result = self.read_fixture([datetime.now(timezone.utc) + timedelta(days=30)])
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
