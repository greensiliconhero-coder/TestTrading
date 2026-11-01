import json
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from context_kite import chunks, validate


class ContextTests(unittest.TestCase):
    def test_chunks_cover_only_requested_period_without_gaps(self):
        spans = list(chunks())
        self.assertEqual(spans[0][0], date(2021, 1, 1))
        self.assertEqual(spans[-1][1], date(2024, 12, 31))
        for a, b in zip(spans, spans[1:]):
            self.assertEqual((b[0] - a[1]).days, 1)
        self.assertTrue(all((b-a).days < 60 for a, b in spans))

    def body(self, rows):
        return json.dumps({'status': 'success', 'data': {'candles': rows}}).encode()

    def test_index_zero_volume_is_valid(self):
        r = validate(self.body([['2021-01-01T09:15:00+0530', 100, 102, 99, 101, 0]]), date(2021,1,1), date(2021,1,1))
        self.assertEqual(r['status'], 'staged_unverified')
        self.assertFalse(r['calendar_verified'])

    def test_duplicates_and_future_dates_rejected(self):
        row = ['2021-01-01T09:15:00+0530', 100, 102, 99, 101, 0]
        with self.assertRaises(ValueError):
            validate(self.body([row, row]), date(2021,1,1), date(2021,1,1))
        with self.assertRaises(ValueError):
            validate(self.body([row]), date(2020,1,1), date(2020,1,1))


if __name__ == '__main__':
    unittest.main()
