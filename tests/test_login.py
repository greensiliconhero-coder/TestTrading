import hashlib
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kite_login import callback_token, exchange_form


class LoginTests(unittest.TestCase):
    def test_success_callback(self):
        self.assertEqual(callback_token('/?status=success&request_token=test&state=abc', 'abc'), 'test')

    def test_reject_invalid_callbacks(self):
        for path in ['/?status=success&request_token=test&state=other',
                     '/?status=failure&request_token=test&state=abc',
                     '/?status=success&state=abc',
                     '/?status=success&request_token=a&request_token=b&state=abc']:
            with self.assertRaises(ValueError):
                callback_token(path, 'abc')

    def test_exchange_uses_checksum_not_secret(self):
        form = parse_qs(exchange_form('key', 'dummy-secret', 'request').decode())
        self.assertEqual(form['checksum'], [hashlib.sha256(b'keyrequestdummy-secret').hexdigest()])
        self.assertNotIn('api_secret', form)


if __name__ == '__main__':
    unittest.main()
