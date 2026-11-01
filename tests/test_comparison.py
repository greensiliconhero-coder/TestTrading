import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from compare_downloads import compare


class ComparisonTests(unittest.TestCase):
    def test_timezone_normalization_and_changed_values(self):
        old = [['2024-06-25 09:15:00+05:30', '100', '102', '99', '101', '10']]
        new = [['2024-06-25T03:45:00+0000', 100, 102, 99, 101, 12],
               ['2024-06-25T09:16:00+0530', 101, 103, 100, 102, 20]]
        summary, details = compare(old, new)
        self.assertEqual(summary['matched_timestamps'], 1)
        self.assertEqual(summary['changed_values'], 1)
        self.assertEqual(summary['new_only_rows'], 1)
        self.assertEqual(details[0]['field'], 'volume')

    def test_duplicates_are_not_silently_overwritten(self):
        rows = [['2024-06-25T09:15:00+0530', 100, 102, 99, 101, 10]] * 2
        with self.assertRaises(ValueError):
            compare(rows, [])

    def test_nonfinite_values_do_not_disappear_from_differences(self):
        with self.assertRaises(ValueError):
            compare([['2024-06-25T09:15:00+0530', 'NaN', 102, 99, 101, 10]], [])


if __name__ == '__main__':
    unittest.main()
