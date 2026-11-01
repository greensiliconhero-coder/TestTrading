"""Authenticated, resumable index minute downloads into isolated staging."""
import csv
import getpass
import hashlib
import io
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path
from kite_login import login
from kite_repair import Client, ApiFailure, atomic_write, encoded, parse_timestamp, IST
from context_sources import ROOT, STAGE, RECORDS


def chunks():
    start, end = date(2021, 1, 1), date(2024, 12, 31)
    while start <= end:
        stop = min(start + timedelta(days=58), end)
        yield start, stop
        start = stop + timedelta(days=1)


def validate(body, start, stop):
    obj = json.loads(body)
    if obj.get('status') != 'success' or not isinstance(obj.get('data', {}).get('candles'), list):
        raise ValueError('Not a successful candle response.')
    rows = obj['data']['candles']
    previous = None
    sessions = {}
    outside = 0
    for row in rows:
        if len(row) != 6:
            raise ValueError('Expected OHLCV index candles.')
        stamp = parse_timestamp(row[0])
        if stamp.utcoffset() is None:
            raise ValueError('Missing timezone.')
        stamp = stamp.astimezone(IST)
        if not start <= stamp.date() <= stop or (previous and stamp <= previous) or stamp.second or stamp.microsecond:
            raise ValueError('Timestamp order, range or granularity failed.')
        previous = stamp
        op, hi, lo, close, volume = row[1:]
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in row[1:]):
            raise ValueError('Invalid number.')
        if min(op, hi, lo, close) <= 0 or hi < max(op, lo, close) or lo > min(op, hi, close) or volume < 0:
            raise ValueError('Invalid OHLCV.')
        # Indices are calculated values: zero volume is expected, not illiquidity.
        regular = 555 <= stamp.hour * 60 + stamp.minute < 930
        outside += not regular
        if regular:
            day = stamp.date().isoformat()
            sessions[day] = sessions.get(day, 0) + 1
    return {'rows': len(rows), 'regular_session_counts': sessions, 'outside_regular_rows': outside,
            'status': 'staged_unverified' if rows else 'empty_unverified', 'calendar_verified': False}


def main():
    mapping = json.loads((RECORDS / 'index_instruments.json').read_text())
    if mapping['unresolved'] or len(mapping['indices']) != 9:
        raise ValueError('Index mapping is unresolved.')
    key = getpass.getpass('Kite API KEY (hidden): ').strip()
    secret = getpass.getpass('Kite API SECRET (hidden): ').strip()
    if not key or not secret:
        raise ValueError('Both key and secret required.')
    token = login(key, secret)
    secret = None
    client = Client(key, token)
    # Refresh mapping after login, rather than trust stale instrument tokens.
    current = list(csv.DictReader(io.StringIO(client.get('/instruments/NSE').decode('utf-8-sig'))))
    for index in mapping['indices']:
        matches = [r for r in current if r['tradingsymbol'] == index['tradingsymbol'] and r['segment'] == 'INDICES' and r['exchange'] == 'NSE']
        if len(matches) != 1 or matches[0]['instrument_token'] != index['instrument_token']:
            raise ValueError('Index token changed; refresh public sources before downloading.')
    log = RECORDS / 'kite_manifest.json'
    records = json.loads(log.read_text())['requests'] if log.exists() else {}
    ranges = list(chunks())
    total = len(ranges) * len(mapping['indices'])
    done = 0
    for index in mapping['indices']:
        symbol = index['tradingsymbol'].replace(' ', '_')
        for start, stop in ranges:
            done += 1
            job = f'{symbol}_{start}_{stop}'
            old = records.get(job, {})
            if old.get('status') == 'staged_unverified' and (ROOT / old['path']).exists():
                if hashlib.sha256((ROOT / old['path']).read_bytes()).hexdigest() == old['sha256']:
                    print(f'{done}/{total} reuse {job}', flush=True)
                    continue
            rec = {'symbol': index['tradingsymbol'], 'instrument_token': index['instrument_token'],
                   'from': str(start), 'to': str(stop), 'endpoint': 'Kite historical/minute', 'calendar_verified': False}
            try:
                body = client.get(f'/instruments/historical/{index["instrument_token"]}/minute',
                                  {'from': f'{start} 00:00:00', 'to': f'{stop} 23:59:59', 'oi': 0})
                digest = hashlib.sha256(body).hexdigest()
                path = STAGE / 'kite_minute' / f'{job}_{digest[:16]}.json'
                atomic_write(path, body)  # preserve raw response even when validation fails
                rec.update(path=path.relative_to(ROOT).as_posix(), sha256=digest, bytes=len(body))
                rec.update(validate(body, start, stop))
            except (ValueError, ApiFailure) as exc:
                rec.update(status='failed_or_quarantined', error=str(exc))
                records[job] = rec
                atomic_write(log, encoded({'training_merge': False, 'reserved_2025_prices_requested': False, 'requests': records}))
                raise
            records[job] = rec
            atomic_write(log, encoded({'training_merge': False, 'reserved_2025_prices_requested': False, 'requests': records}))
            print(f'{done}/{total} {job}: {rec["status"]}, {rec["rows"]} rows', flush=True)
    print('Download complete. All files remain in staging; calendar and cross-source validation still required.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ApiFailure) as exc:
        print(f'Stopped: {exc}')
        sys.exit(1)
    except KeyboardInterrupt:
        print('Cancelled; verified chunks can be reused next time.')
        sys.exit(1)
