import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import http.client
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kite_repair import Client, ApiFailure, instrument_map, validate_response, download_job, encoded, make_plan, validate_plan

JOB = {'symbol': 'TEST', 'day': '2024-06-25', 'interval': 'minute', 'reason': 'test'}
INSTRUMENT = {'instrument_token': '123', 'tradingsymbol': 'TEST'}
TEST_TMP = Path(__file__).resolve().parents[1] / 'work/test-temp'
TEST_TMP.mkdir(parents=True, exist_ok=True)


def payload(rows=None):
    if rows is None:
        rows = [['2024-06-25T09:15:00+0530', 100, 102, 99, 101, 10]]
    return encoded({'status': 'success', 'data': {'candles': rows}})


class FakeClient:
    def __init__(self, body=None, failure=None):
        self.body = payload() if body is None else body
        self.failure, self.calls = failure, 0

    def get(self, *args):
        self.calls += 1
        if self.failure:
            raise self.failure
        return self.body


class RepairTests(unittest.TestCase):
    def test_incomplete_body_retries_whole_request(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = [http.client.IncompleteRead(b'partial', 10), payload()]
        with patch('kite_repair.request.build_opener') as opener:
            opener.return_value.open.return_value = response
            client = Client('key', 'token', sleep=lambda _: None)
            self.assertEqual(client.get('/instruments/NSE'), payload())
            self.assertEqual(opener.return_value.open.call_count, 2)

    def test_persistent_incomplete_body_is_bounded_and_sanitized(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = http.client.IncompleteRead(b'sensitive-body', 10)
        with patch('kite_repair.request.build_opener') as opener:
            opener.return_value.open.return_value = response
            with self.assertRaises(ApiFailure) as caught:
                Client('key', 'token', sleep=lambda _: None).get('/instruments/NSE')
            self.assertEqual(opener.return_value.open.call_count, 3)
            self.assertEqual(caught.exception.kind, 'incomplete_response')
            self.assertNotIn('sensitive', str(caught.exception))

    def test_retry_transient_and_rate_spacing(self):
        calls, sleeps = [], []
        def send(*args):
            calls.append(args)
            if len(calls) < 3:
                raise ApiFailure(429)
            return b'ok'
        client = Client('secret-key', 'secret-token', send=send, sleep=sleeps.append, clock=lambda: 0)
        self.assertEqual(client.get('/instruments/NSE'), b'ok')
        self.assertEqual(len(calls), 3)
        self.assertIn(0.4, sleeps)

    def test_auth_and_permanent_errors_not_retried(self):
        for status in [400, 401, 403, 404]:
            count = []
            def send(*args):
                count.append(1)
                raise ApiFailure(status)
            client = Client('key', 'token', send=send, sleep=lambda _: None)
            with self.assertRaises(ApiFailure):
                client.get('/instruments/NSE')
            self.assertEqual(len(count), 1)

    def test_no_trading_endpoints(self):
        client = Client('key', 'token', send=lambda *args: self.fail('Network called'))
        for endpoint in ['/orders', '/portfolio/holdings', '/instruments/historical/1/../orders']:
            with self.assertRaises(ValueError):
                client.get(endpoint)

    def test_empty_is_not_failure_or_verified_complete(self):
        self.assertEqual(validate_response(payload([]), JOB)['status'], 'empty_unverified')
        for body in [b'null', b'{"status":"success","data":{}}', b'<html>Error</html>', b'{"status":"error"}']:
            with self.assertRaises(ValueError):
                validate_response(body, JOB)

    def test_candle_quarantine(self):
        rows = [['2024-06-25T09:15:00+0530', 100, 90, 99, 101, -1]] * 2
        result = validate_response(payload(rows), JOB)
        self.assertEqual(result['status'], 'quarantined')
        self.assertTrue({'duplicate_timestamp', 'inconsistent_ohlc', 'negative_volume'} <= set(result['issues']))

    def test_wrong_date_and_naive_time(self):
        for stamp in ['2024-06-24T09:15:00+0530', '2024-06-25T09:15:00']:
            result = validate_response(payload([[stamp, 1, 1, 1, 1, 0]]), JOB)
            self.assertEqual(result['status'], 'quarantined')

    def test_instrument_mapping_rejects_ambiguity(self):
        header = 'tradingsymbol,instrument_token,exchange,instrument_type,segment\n'
        row = 'TEST,123,NSE,EQ,NSE\n'
        self.assertEqual(instrument_map((header + row).encode())['TEST']['instrument_token'], '123')
        with self.assertRaises(ValueError):
            instrument_map((header + row + row).encode())

    def test_checksum_resume_and_corruption_refetch(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            client = FakeClient()
            result = download_job(client, JOB, INSTRUMENT, 'snapshot', directory)
            self.assertEqual(result['status'], 'downloaded_unverified')
            self.assertTrue(download_job(client, JOB, INSTRUMENT, 'snapshot', directory)['resumed'])
            self.assertEqual(client.calls, 1)
            next(Path(directory).glob('*/response.json')).write_text('broken')
            download_job(client, JOB, INSTRUMENT, 'snapshot', directory)
            self.assertEqual(client.calls, 2)
            self.assertFalse(list(Path(directory).glob('*/active.lock')))

    def test_failures_persist_and_resume_retries_them(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            bad = FakeClient(failure=ApiFailure(503))
            self.assertEqual(download_job(bad, JOB, INSTRUMENT, 'snapshot', directory)['status'], 'failed')
            good = FakeClient()
            self.assertEqual(download_job(good, JOB, INSTRUMENT, 'snapshot', directory)['status'], 'downloaded_unverified')
            self.assertEqual(good.calls, 1)

    def test_auth_failure_persisted_then_aborts(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            with self.assertRaises(ApiFailure):
                download_job(FakeClient(failure=ApiFailure(403)), JOB, INSTRUMENT, 'snapshot', directory)
            record = json.loads(next(Path(directory).glob('*/manifest.json')).read_text())
            self.assertEqual(record['failure'], 'http:403')

    def test_empty_response_not_skipped_next_run(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            client = FakeClient(payload([]))
            download_job(client, JOB, INSTRUMENT, 'snapshot', directory)
            download_job(client, JOB, INSTRUMENT, 'snapshot', directory)
            self.assertEqual(client.calls, 2)

    def test_prelisting_guard_and_plan_bound(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            path = Path(directory) / 'issues.csv'
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=['source_file', 'date'])
                writer.writeheader()
                writer.writerow({'source_file': str(Path(directory) / 'HDFCLIFE_2015.csv'), 'date': '2015-06-01'})
            plan = make_plan(path)
            self.assertEqual(plan['prelisting_rows_excluded_from_requests']['HDFCLIFE'], 1)
            validate_plan(plan)
            plan['requests'].append(dict(JOB, symbol='HDFCLIFE', day='2016-01-01'))
            with self.assertRaises(ValueError):
                validate_plan(plan)


if __name__ == '__main__':
    unittest.main()
