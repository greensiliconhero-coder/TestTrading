"""Resumable, data-only five-year snapshot. Credentials remain in memory."""
import argparse
import csv
import getpass
import hashlib
import io
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from context_kite import validate
from kite_login import login
from kite_repair import Client, ApiFailure, atomic_write, encoded, instrument_map

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'data/five_year_v4'
LOG = ROOT / 'experiments/five_year_v4/download_manifest.json'


def ranges(start, end, interval):
    while start <= end:
        stop = min(start + timedelta(days=58 if interval == 'minute' else 364), end)
        yield start, stop
        start = stop + timedelta(days=1)


def jobs(config):
    for kind, symbols in [('stock', config['stocks']), ('index', config['indices'])]:
        for symbol in symbols:
            for interval in ['minute', 'day']:
                for start, end in ranges(date.fromisoformat(config['from']), date.fromisoformat(config['to']), interval):
                    yield {'kind': kind, 'symbol': symbol, 'interval': interval, 'from': str(start), 'to': str(end)}


def validate_response(body, job):
    result = validate(body, date.fromisoformat(job['from']), date.fromisoformat(job['to']))
    if job['interval'] == 'day':
        rows = json.loads(body)['data']['candles']
        days = [r[0][:10] for r in rows]
        if len(days) != len(set(days)):
            raise ValueError('Duplicate daily session.')
        result.pop('regular_session_counts')
        result.pop('outside_regular_rows')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config/five_year_v4.json').read_text())
    planned = list(jobs(config))
    STAGE.mkdir(parents=True, exist_ok=True)
    atomic_write(STAGE / 'plan.json', encoded({'config': config, 'requests': planned}))
    print(f'{len(planned)} requests; destination {STAGE}', flush=True)
    if not args.execute:
        return
    key = getpass.getpass('Kite API KEY (hidden): ').strip()
    secret = getpass.getpass('Kite API SECRET (hidden): ').strip()
    client = Client(key, login(key, secret))
    secret = None
    instruments = client.get('/instruments/NSE')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    snapshot = STAGE / 'instruments' / f'NSE_{stamp}.csv'
    atomic_write(snapshot, instruments)
    stocks = instrument_map(instruments)
    indices = {r['tradingsymbol']: r for r in csv.DictReader(io.StringIO(instruments.decode('utf-8-sig'))) if r['segment'] == 'INDICES' and r['exchange'] == 'NSE'}
    missing = [s for s in config['stocks'] if s not in stocks] + [s for s in config['indices'] if s not in indices]
    if missing:
        raise ValueError('Resolve instrument identity before downloading: ' + ', '.join(missing))
    records = json.loads(LOG.read_text())['requests'] if LOG.exists() else {}
    def save():
        atomic_write(LOG, encoded({'dataset': 'five_year_v4', 'training_started': False,
                                  'requests': records, 'updated_utc': datetime.now(timezone.utc).isoformat()}))
    for number, job in enumerate(planned, 1):
        name = f"{job['symbol'].replace(' ', '_')}_{job['interval']}_{job['from']}_{job['to']}"
        token = (stocks if job['kind'] == 'stock' else indices)[job['symbol']]['instrument_token']
        old = records.get(name, {})
        oldpath = ROOT / old.get('path', 'nonexistent')
        if old.get('status') == 'staged_unverified' and old.get('instrument_token') == token and oldpath.is_file() and hashlib.sha256(oldpath.read_bytes()).hexdigest() == old['sha256']:
            print(f'{number}/{len(planned)} reuse {name}', flush=True)
            continue
        rec = dict(job, instrument_token=token, instrument_snapshot=snapshot.relative_to(ROOT).as_posix(), retrieved_utc=datetime.now(timezone.utc).isoformat())
        try:
            body = client.get(f'/instruments/historical/{token}/{job["interval"]}', {'from': job['from'] + ' 00:00:00', 'to': job['to'] + ' 23:59:59', 'oi': 0})
            digest = hashlib.sha256(body).hexdigest()
            path = STAGE / 'raw' / job['kind'] / job['interval'] / f'{name}_{digest[:16]}.json'
            atomic_write(path, body)
            rec.update(path=path.relative_to(ROOT).as_posix(), sha256=digest, bytes=len(body))
            rec.update(validate_response(body, job))
        except ValueError as exc:
            rec.update(status='quarantined', error=str(exc))
        except ApiFailure as exc:
            rec.update(status='request_failed', error=str(exc))
            records[name] = rec
            save()
            raise
        records[name] = rec
        save()
        print(f'{number}/{len(planned)} {name}: {rec["status"]}, {rec.get("rows", 0)} rows', flush=True)
    bad = [k for k, v in records.items() if v['status'] != 'staged_unverified']
    print(f'Download pass finished; {len(bad)} empty/quarantined requests. Audit required before training.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ApiFailure) as exc:
        print(f'Stopped: {exc}', flush=True)
        raise SystemExit(1)
