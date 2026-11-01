import sys
import unittest
import tempfile
import json
import io
from contextlib import redirect_stdout
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from audit import inspect_frame, run


class AuditTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame([
            ['2024-01-02 09:15:00+05:30', 100, 102, 99, 101, 10],
            ['2024-01-02 09:17:00+05:30', 101, 104, 100, 103, 20],
        ], columns=['date', 'open', 'high', 'low', 'close', 'volume'])

    def test_aggregation_and_gap_reference(self):
        report, sessions = inspect_frame(self.frame(), 'minute', 'TEST')
        row = sessions.iloc[0]
        self.assertEqual((row.open, row.high, row.low, row.close, row.volume), (100, 104, 99, 103, 30))
        self.assertEqual(row.missing_regular_minutes_reference, 373)
        self.assertEqual(report['outside_regular_session_rows'], 0)

    def test_duplicate_invalid_candle_and_negative_volume(self):
        df = self.frame()
        df.loc[1, 'date'] = df.loc[0, 'date']
        df.loc[1, 'high'] = 90
        df.loc[1, 'volume'] = -1
        report, _ = inspect_frame(df, 'minute', 'TEST')
        self.assertEqual(report['duplicate_timestamps'], 1)
        self.assertEqual(report['invalid_ohlc_rows'], 1)
        self.assertEqual(report['negative_volume_rows'], 1)

    def test_naive_time_is_not_silently_assumed(self):
        df = self.frame()
        df.loc[0, 'date'] = '2024-01-02 09:15:00'
        report, _ = inspect_frame(df, 'minute', 'TEST')
        self.assertEqual(report['invalid_timestamps'], 1)
        self.assertEqual(report['timestamps_without_offset'], 1)

    def test_empty_and_missing_columns(self):
        report, _ = inspect_frame(self.frame().iloc[:0], 'minute', 'TEST')
        self.assertEqual(report['status'], 'empty')
        with self.assertRaises(ValueError):
            inspect_frame(pd.DataFrame({'date': []}), 'minute', 'TEST')

    def test_invalid_numeric_and_order(self):
        df = self.frame().iloc[::-1].reset_index(drop=True)
        df['open'] = df['open'].astype(float)
        df.loc[0, 'open'] = float('inf')
        report, _ = inspect_frame(df, 'minute', 'TEST')
        self.assertEqual(report['out_of_order_steps'], 1)
        self.assertEqual(report['invalid_numeric_rows'], 1)

    def test_pipeline_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            path = source / 'TEST_2024.csv'
            self.frame().to_csv(path, index=False)
            original = path.read_bytes()
            config = root / 'config.json'
            config.write_text(json.dumps({'daily': str(source), 'minute': str(source)}))
            with redirect_stdout(io.StringIO()):
                run(config, root / 'report')
            report = json.loads((root / 'report/summary.json').read_text())
            self.assertEqual(report['comparison']['matched_symbol_days'], 1)
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue((root / 'report/audit_report.md').exists())
            with self.assertRaises(ValueError):
                run(config, source / 'unsafe-output')


if __name__ == '__main__':
    unittest.main()
