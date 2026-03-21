# -*- coding: utf-8 -*-
"""
QMT Local Data File Format Analyzer
Analyzes .dat file structure in userdata_mini/datadir/
"""

import struct
import pandas as pd
from pathlib import Path
from datetime import datetime


class QMTDatAnalyzer:
    """QMT .dat file format analyzer"""

    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.file_size = self.file_path.stat().st_size

    def analyze_header(self, header_size=1024):
        """Analyze file header information"""
        print(f"\n{'='*80}")
        print(f"File Analysis: {self.file_path.name}")
        print(f"{'='*80}")
        print(f"File Size: {self.file_size:,} bytes ({self.file_size / 1024 / 1024:.2f} MB)")
        print(f"File Path: {self.file_path}")

        with open(self.file_path, 'rb') as f:
            header_data = f.read(header_size)

        print(f"\nFirst {header_size} bytes of file header:")
        print("-" * 80)

        # Try different parsing methods
        self._try_parse_as_struct(header_data)
        self._try_parse_as_csv(header_data)
        self._print_hex_dump(header_data, 256)

    def _try_parse_as_struct(self, data):
        """Try parsing as structured binary data"""
        print("\n[Attempt 1] Parse as structured binary format:")

        # Common stock data formats
        formats_to_try = [
            # time(4) open(4) high(4) low(4) close(4) volume(4) amount(8) = 32 bytes
            ('IIIIII d', 'Format A (32B): time open high low close volume(I) amount(d)'),
            ('IIIIIId', 'Format A (32B): time open high low close volume(I) amount(d)'),

            # time(8) open(4) high(4) low(4) close(4) volume(8) amount(8) = 40 bytes
            ('QIIIddd', 'Format B (40B): time(Q) open high low close(I) volume amount(d)'),

            # time(4) open(8) high(8) low(8) close(8) volume(8) amount(8) = 52 bytes
            ('Ididddd', 'Format C (52B): time(I) open high low close volume amount(d)'),

            # time(8) open(8) high(8) low(8) close(8) volume(8) amount(8) = 56 bytes
            ('Qddddddd', 'Format D (56B): time(Q) open high low close volume amount(d)'),

            # time(4) open(4) high(4) low(4) close(4) volume(8) amount(8) = 36 bytes
            ('IIIIddd', 'Format E (36B): time open high low close(I) volume amount(d)'),

            # time(8) open(4) high(4) low(4) close(4) amount(8) = 32 bytes
            ('QIIII d', 'Format F (32B): time(Q) open high low close(I) amount(d)'),
        ]

        for fmt, desc in formats_to_try:
            # Remove spaces for calcsize
            fmt_calc = fmt.replace(' ', '')

            try:
                record_size = struct.calcsize(fmt_calc)
                num_records = len(data) // record_size

                print(f"\n  {desc}")
                print(f"    Record Size: {record_size} bytes")
                print(f"    Possible Records: {num_records:,}")

                if num_records > 0:
                    # Try to parse first few records
                    offset = 0
                    for i in range(min(3, num_records)):
                        try:
                            record = struct.unpack_from(fmt_calc, data, offset)
                            print(f"    Record #{i+1}: {record}")
                            offset += record_size
                        except Exception as e:
                            print(f"    Parse error at record #{i+1}: {e}")
                            break

                    # Check if reasonable
                    if num_records > 10 and num_records < 1000000:
                        print(f"    [OK] Record count looks reasonable")
            except struct.error as e:
                print(f"\n  {desc}")
                print(f"    [X] Invalid format: {e}")

    def _try_parse_as_csv(self, data):
        """Try parsing as CSV format"""
        print("\n[Attempt 2] Parse as text/CSV format:")

        try:
            # Try decoding as text
            text = data.decode('utf-8', errors='ignore')

            # Check for common separators
            separators = [',', '\t', '|', ';']
            for sep in separators:
                first_line = text.split('\n')[0]
                if sep in first_line:
                    print(f"    Found separator: '{sep}'")
                    print(f"    First line: {first_line[:100]}")
                    break
            else:
                print("    No obvious separator found")
                print(f"    Text content (first 100 chars): {text[:100]}")
        except Exception as e:
            print(f"    Not text format: {e}")

    def _print_hex_dump(self, data, size=256):
        """Print hex dump"""
        print(f"\n[Hex Dump] First {size} bytes:")
        print("-" * 80)

        for i in range(0, min(size, len(data)), 16):
            hex_part = ' '.join(f'{b:02x}' for b in data[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
            print(f"{i:04x}: {hex_part:<48} {ascii_part}")

    def analyze_complete_file(self):
        """Analyze complete file structure"""
        print(f"\n{'='*80}")
        print("Complete File Structure Analysis")
        print(f"{'='*80}")

        with open(self.file_path, 'rb') as f:
            file_data = f.read()

        # Try different record sizes
        possible_record_sizes = [28, 32, 36, 40, 44, 48, 52, 56, 60, 64]

        print(f"\nTrying different record sizes:")
        print("-" * 80)

        for record_size in possible_record_sizes:
            num_records = len(file_data) // record_size
            remainder = len(file_data) % record_size

            if num_records > 0 and remainder < 100:  # Allow small header/footer
                print(f"\nRecord Size: {record_size} bytes")
                print(f"  Records: {num_records:,}")
                print(f"  Remaining Bytes: {remainder}")

                if remainder > 0:
                    print(f"  Possible Header Size: {remainder} bytes")

    def estimate_records_per_day(self):
        """Estimate records per day (for format validation)"""
        # Minute data: 240 records per day (4 hours x 60 minutes)
        estimates = {
            '1m': 240,
            '5m': 48,
            '15m': 16,
            '30m': 8,
            '60m': 4,
            '1d': 1
        }

        print(f"\nEstimated Record Count (for validation):")
        print("-" * 80)
        for period, records_per_day in estimates.items():
            # Assume ~1 year of data (250 trading days)
            total_records = records_per_day * 250

            for record_size in [28, 32, 40, 48, 56, 64]:
                file_size_estimate = total_records * record_size
                if abs(file_size_estimate - self.file_size) < self.file_size * 0.1:  # 10% tolerance
                    print(f"  {period}: {records_per_day} records/day x 250 days = {total_records:,} records")
                    print(f"    Record size {record_size} bytes -> file size {file_size_estimate/1024/1024:.2f} MB [OK]")


def main():
    """Main function"""
    print("\n" + "="*80)
    print("QMT .dat File Format Analyzer")
    print("="*80)

    # Analyze 1-minute data file
    minute_files = [
        r"D:\国金QMT交易端模拟\userdata_mini\datadir\SZ\60\000001.DAT",
    ]

    # Check if files exist
    existing_files = [f for f in minute_files if Path(f).exists()]

    if not existing_files:
        print("\nError: QMT data files not found")
        print("Please ensure QMT path is correct and data has been downloaded")
        return

    # Analyze each file
    for file_path in existing_files:
        analyzer = QMTDatAnalyzer(file_path)

        # Analyze header
        analyzer.analyze_header()

        # Analyze complete file structure
        analyzer.analyze_complete_file()

        # Estimate record count
        analyzer.estimate_records_per_day()

    print("\n" + "="*80)
    print("Analysis Complete")
    print("="*80)


if __name__ == '__main__':
    main()
