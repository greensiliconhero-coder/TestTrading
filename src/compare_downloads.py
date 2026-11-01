"""Compare staged pilot responses with original CSVs; never merge replacements."""
import csv
import io
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from kite_repair import ROOT, IST, digest, encoded, atomic_write, validate_response, parse_timestamp


def key(value):
    stamp = parse_timestamp(value)
    if stamp.utcoffset() is None:
        raise ValueError('Comparison requires timezone-aware timestamps.')
    return stamp.astimezone(IST).isoformat()


def compare(old, new):
    fields = ['open', 'high', 'low', 'close', 'volume']
    old_map, new_map = {}, {}
    for rows, mapping in [(old, old_map), (new, new_map)]:
        for row in rows:
            if len(row) < 6:
                raise ValueError('Incomplete candle cannot be compared.')
            stamp = key(row[0])
            if stamp in mapping:
                raise ValueError('Duplicate timestamps cannot be compared unambiguously.')
            numbers = [float(n) for n in row[1:6]]
            if not all(math.isfinite(n) for n in numbers):
                raise ValueError('Non-finite candle cannot be compared.')
            mapping[stamp] = numbers
    differences = []
    for stamp in sorted(old_map.keys() | new_map.keys()):
        left, right = old_map.get(stamp), new_map.get(stamp)
        if left is None or right is None:
            differences.append({'timestamp': stamp, 'field': 'row', 'old': '', 'new': '',
                                'kind': 'new_only' if left is None else 'old_only'})
        else:
            for field, a, b in zip(fields, left, right):
                if abs(a - b) > 1e-8:
                    differences.append({'timestamp': stamp, 'field': field, 'old': a, 'new': b, 'kind': 'changed'})
    return {'old_rows': len(old_map), 'new_rows': len(new_map), 'matched_timestamps': len(old_map.keys() & new_map.keys()),
            'changed_values': sum(r['kind'] == 'changed' for r in differences),
            'old_only_rows': len(old_map.keys() - new_map.keys()), 'new_only_rows': len(new_map.keys() - old_map.keys())}, differences


def main():
    store = ROOT / 'work/kite'
    latest = store / 'latest_run.json'
    if not latest.exists():
        print('No pilot downloads yet. Run the data-only fetch after configuring Kite access.')
        return
    config = json.loads((ROOT / 'config/datasets.json').read_text())
    results = json.loads(latest.read_text())['results']
    grouped = defaultdict(list)
    summaries, details = [], []
    for result in results:
        spec = result['request']
        frequency = 'minute' if spec['interval'] == 'minute' else 'daily'
        path = Path(config[frequency]) / f'{spec["symbol"]}_{spec["day"][:4]}.csv'
        grouped[path].append(result)
    for path, group in grouped.items():
        days = {r['request']['day']: [] for r in group}
        if path.exists():
            with path.open(newline='', encoding='utf-8-sig') as stream:
                for row in csv.DictReader(stream):
                    day = key(row['date'])[:10]
                    if day in days:
                        days[day].append([row[f] for f in ['date', 'open', 'high', 'low', 'close', 'volume']])
        for result in group:
            spec = result['request']
            base = {k: spec[k] for k in ['symbol', 'day', 'interval']}
            base['download_status'] = result['status']
            if result['status'] not in {'downloaded_unverified', 'quarantined', 'empty_unverified'}:
                summaries.append(dict(base, comparison='not_available'))
                continue
            body = (store / 'chunks' / digest(encoded(spec))[:24] / 'response.json').read_bytes()
            if digest(body) != result['response_sha256']:
                raise ValueError('Staged response checksum mismatch; rerun fetch.')
            validate_response(body, spec)
            new = json.loads(body)['data']['candles']
            try:
                counts, changes = compare(days[spec['day']], new)
                summaries.append(dict(base, comparison='compared', **counts))
                details.extend(dict(base, **row) for row in changes)
            except ValueError:
                summaries.append(dict(base, comparison='invalid_or_ambiguous_rows'))
    output = ROOT / 'outputs/repair'
    for name, rows in [('comparison_summary.csv', summaries), ('comparison_details.csv', details)]:
        fields = list(dict.fromkeys(k for row in rows for k in row)) or ['status']
        text = io.StringIO(newline='')
        writer = csv.DictWriter(text, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        atomic_write(output / name, text.getvalue().encode())
    print(f'Compared {len(summaries)} requests. Results in outputs/repair. No files were merged.')


if __name__ == '__main__':
    main()
