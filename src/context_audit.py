"""Verify staged index payloads and compare sessions with existing stock samples."""
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from context_sources import ROOT, RECORDS
from context_kite import chunks, validate


def main():
    manifest = json.loads((RECORDS / 'kite_manifest.json').read_text())
    mapping = json.loads((RECORDS / 'index_instruments.json').read_text())
    expected = {
        f'{index["tradingsymbol"].replace(" ", "_")}_{start}_{stop}'
        for index in mapping['indices'] for start, stop in chunks()
    }
    jobs = manifest['requests']
    if set(jobs) != expected:
        raise ValueError('Unexpected or missing download chunks.')
    stock_days = set()
    # Only the already-used 2021-24 development sample metadata is accessed.
    with (ROOT / 'work/neural_v2/metadata.csv').open() as stream:
        for row in csv.DictReader(stream):
            if '2021' <= row['day'][:4] <= '2024':
                stock_days.add(row['day'])
    counts = defaultdict(lambda: {'chunks': 0, 'rows': 0, 'outside_regular_rows': 0, 'sessions': {}})
    for job, rec in jobs.items():
        if rec['status'] != 'staged_unverified':
            raise ValueError(f'Chunk is not accepted: {job}')
        body = (ROOT / rec['path']).read_bytes()
        if hashlib.sha256(body).hexdigest() != rec['sha256']:
            raise ValueError(f'Payload hash mismatch: {job}')
        info = validate(body, date.fromisoformat(rec['from']), date.fromisoformat(rec['to']))
        if not info['rows']:
            raise ValueError(f'Empty chunk: {job}')
        stat = counts[rec['symbol']]
        if set(stat['sessions']).intersection(info['regular_session_counts']):
            raise ValueError(f'Duplicate session across chunks: {job}')
        stat['sessions'].update(info['regular_session_counts'])
        for field in ['rows', 'outside_regular_rows']:
            stat[field] += info[field]
        stat['chunks'] += 1
    summary = {}
    for symbol, stat in counts.items():
        sessions = stat.pop('sessions')
        summary[symbol] = dict(stat, regular_sessions=len(sessions),
            non_375_sessions={day: n for day, n in sessions.items() if n != 375},
            missing_stock_study_sessions=sorted(stock_days - sessions.keys()),
            incomplete_stock_study_sessions={day: sessions[day] for day in sorted(stock_days & sessions.keys()) if sessions[day] != 375})
    result = {'expected_chunks': len(expected), 'verified_chunks': len(jobs),
              'total_rows': sum(s['rows'] for s in summary.values()),
              'stock_study_sessions': len(stock_days), 'series': summary,
              'all_payload_hashes_verified': True, 'structural_validation_passed': True,
              'independent_calendar_verified': False, 'independent_prices_verified': False,
              'historical_identity_verified': False, 'training_merge': False,
              'reserved_2025_prices_accessed': False}
    (RECORDS / 'index_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
