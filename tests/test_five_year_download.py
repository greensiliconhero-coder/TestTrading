import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from five_year_download import ranges, validate_response


class FiveYearDownloadTests(unittest.TestCase):
    def test_complete_nonoverlapping_calendar_ranges(self):
        for interval, maximum in [('minute', 59), ('day', 365)]:
            pairs = list(ranges(date(2021, 1, 1), date(2025, 12, 31), interval))
            self.assertEqual(pairs[0][0], date(2021, 1, 1))
            self.assertEqual(pairs[-1][1], date(2025, 12, 31))
            for i, (start, stop) in enumerate(pairs):
                self.assertLessEqual((stop-start).days + 1, maximum)
                if i:
                    self.assertEqual(start, pairs[i-1][1]+timedelta(days=1))

    def test_bad_prices_and_duplicate_timestamps_rejected(self):
        job = {'from': '2025-01-01', 'to': '2025-01-31', 'interval': 'minute'}
        candle = ['2025-01-02T09:15:00+0530', 100, 101, 99, 100, 10]
        def body(rows):
            return json.dumps({'status': 'success', 'data': {'candles': rows}}).encode()
        self.assertEqual(validate_response(body([candle]), job)['rows'], 1)
        with self.assertRaises(ValueError):
            validate_response(body([candle, candle]), job)
        candle[2] = 98
        with self.assertRaises(ValueError):
            validate_response(body([candle]), job)

    def test_empty_response_not_certified(self):
        result = validate_response(b'{"status":"success","data":{"candles":[]}}',
                                   {'from': '2025-01-01', 'to': '2025-01-02', 'interval': 'day'})
        self.assertEqual(result['status'], 'empty_unverified')
        self.assertFalse(result['calendar_verified'])


if __name__ == '__main__':
    unittest.main()
