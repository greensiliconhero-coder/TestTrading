"""Staged, data-only Kite download workflow. No orders or credential persistence."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import http.client
import io
import json
import math
import os
from pathlib import Path
import re
import socket
import tempfile
import time
import zlib
from datetime import date, datetime, timedelta, timezone
from urllib import request, error, parse

ROOT = Path(__file__).resolve().parents[1]
IST = timezone(timedelta(hours=5, minutes=30))
VERSION = 1
LISTING_DATES = {'HDFCLIFE': '2017-11-17'}


def parse_timestamp(value):
    # Python 3.10 does not accept Kite's compact +0530 offset directly.
    value = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', value.replace('Z', '+00:00'))
    return datetime.fromisoformat(value)


def encoded(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ApiFailure(Exception):
    def __init__(self, status, kind='http'):
        self.status = status
        self.kind = kind
        # Never include server response text, headers, or credential-bearing URLs.
        super().__init__(f'Kite request failed: {kind}, status={status}')


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ApiFailure(code, 'redirect_refused')


def transport(path, params, headers):
    url = 'https://api.kite.trade' + path
    if params:
        url += '?' + parse.urlencode(params)
    req = request.Request(url, headers=headers, method='GET')
    try:
        with request.build_opener(NoRedirect).open(req, timeout=30) as response:
            body = response.read()
            return gzip.decompress(body) if body.startswith(b'\x1f\x8b') else body
    except error.HTTPError as exc:
        raise ApiFailure(exc.code) from None
    except (http.client.IncompleteRead, http.client.RemoteDisconnected,
            gzip.BadGzipFile, EOFError, zlib.error):
        # Discard partial bodies; Client retries the entire read-only request.
        raise ApiFailure(0, 'incomplete_response') from None
    except (error.URLError, TimeoutError, socket.timeout, ConnectionError):
        raise ApiFailure(0, 'network') from None


class Client:
    def __init__(self, key, token, send=transport, sleep=time.sleep, clock=time.monotonic):
        if not key or not token:
            raise ValueError('Set KITE_API_KEY and KITE_ACCESS_TOKEN locally before executing.')
        self.headers = {'X-Kite-Version': '3', 'Authorization': f'token {key}:{token}'}
        self.send, self.sleep, self.clock = send, sleep, clock
        self.last_request = -float('inf')

    def get(self, path, params=None):
        if path != '/instruments/NSE' and not re.fullmatch(r'/instruments/historical/[1-9]\d*/(?:minute|day)', path):
            raise ValueError('Endpoint is outside the data-only allowlist.')
        for attempt in range(3):
            self.sleep(max(0, 0.4 - (self.clock() - self.last_request)))
            self.last_request = self.clock()
            try:
                return self.send(path, params or {}, self.headers)
            except ApiFailure as exc:
                if exc.status not in {0, 429, 500, 502, 503, 504} or attempt == 2:
                    raise
                self.sleep(2 ** attempt)


def instrument_map(content):
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
    required = {'tradingsymbol', 'instrument_token', 'exchange', 'instrument_type', 'segment'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('Instrument response lacks required columns.')
    result = {}
    for row in reader:
        if row['exchange'] == 'NSE' and row['instrument_type'] == 'EQ' and row['segment'] == 'NSE':
            symbol, token = row['tradingsymbol'], row['instrument_token']
            if symbol in result or not re.fullmatch(r'[1-9]\d*', token):
                raise ValueError('Ambiguous or invalid NSE EQ instrument mapping.')
            result[symbol] = {k: row.get(k, '') for k in ['tradingsymbol', 'instrument_token', 'exchange_token', 'name', 'exchange', 'segment', 'instrument_type']}
    if not result:
        raise ValueError('No NSE cash-equity instruments returned.')
    return result


def make_plan(issues_path):
    candidates = {}
    exclusions = {}
    with Path(issues_path).open(newline='', encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            symbol = Path(row['source_file']).stem.rsplit('_', 1)[0]
            day = row['date'][:10]
            if symbol in LISTING_DATES and day < LISTING_DATES[symbol]:
                exclusions[symbol] = exclusions.get(symbol, 0) + 1
                continue
            issue = 'ohlc_inconsistency' if row.get('inconsistent_ohlc', '').lower() == 'true' else 'nonpositive_price'
            candidates.setdefault((symbol, issue), set()).add(day)
    jobs = []
    # One affected session per symbol/issue type; deduplicate shared sessions.
    chosen = set()
    for (symbol, issue), days in sorted(candidates.items()):
        day = min(days)
        if (symbol, day) not in chosen:
            jobs.append({'symbol': symbol, 'day': day, 'reason': issue})
            chosen.add((symbol, day))
    for symbol, day, reason in [('ADANIENT', '2025-10-03', 'overlap_control'),
                                ('ICICIBANK', '2025-10-03', 'overlap_control'),
                                ('ADANIENT', '2020-06-15', 'missing_year_probe'),
                                ('ICICIBANK', '2020-06-15', 'missing_year_probe'),
                                ('ITC', '2020-06-15', 'missing_year_probe')]:
        jobs.append({'symbol': symbol, 'day': day, 'reason': reason})
    requests = [dict(job, interval=interval) for job in jobs for interval in ['minute', 'day']]
    return {'schema_version': VERSION, 'phase': 'validation_pilot', 'source_audit_sha256': digest(Path(issues_path).read_bytes()),
            'listing_dates': LISTING_DATES, 'prelisting_rows_excluded_from_requests': exclusions,
            'limitations': ['Current instrument mapping does not establish historical identity.',
                            'These probes do not fill all gaps or establish a trading calendar.',
                            'No downloaded data is automatically merged into source or training files.'],
            'requests': requests}


def validate_plan(plan):
    if plan.get('schema_version') != VERSION or not isinstance(plan.get('requests'), list):
        raise ValueError('Unsupported plan schema.')
    if not 1 <= len(plan['requests']) <= 50:
        raise ValueError('Pilot requires 1–50 requests; broad backfills are a separate phase.')
    seen = set()
    for job in plan['requests']:
        if not re.fullmatch(r'[A-Z0-9&_-]+', job['symbol']) or job['interval'] not in {'minute', 'day'}:
            raise ValueError('Invalid symbol or interval.')
        day = date.fromisoformat(job['day'])
        if day.isoformat() != job['day'] or day >= datetime.now(IST).date():
            raise ValueError('Only completed historical dates are allowed.')
        if job['symbol'] in LISTING_DATES and job['day'] < LISTING_DATES[job['symbol']]:
            raise ValueError('Request precedes known listing date.')
        key = (job['symbol'], job['day'], job['interval'])
        if key in seen:
            raise ValueError('Duplicate request in plan.')
        seen.add(key)


def validate_response(body, job):
    try:
        response = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Response is not valid JSON.') from None
    if not isinstance(response, dict) or response.get('status') != 'success':
        raise ValueError('Response did not report success.')
    data = response.get('data')
    candles = data.get('candles') if isinstance(data, dict) else None
    if not isinstance(candles, list):
        raise ValueError('Successful response has no candle list.')
    problems, seen, previous = set(), set(), None
    regular = set()
    for candle in candles:
        if not isinstance(candle, list) or len(candle) not in {6, 7}:
            problems.add('invalid_row_shape')
            continue
        try:
            stamp = parse_timestamp(candle[0])
            if stamp.utcoffset() is None:
                raise ValueError()
            stamp = stamp.astimezone(IST)
            if stamp.date().isoformat() != job['day']:
                problems.add('outside_requested_date')
            if stamp in seen:
                problems.add('duplicate_timestamp')
            if previous is not None and stamp < previous:
                problems.add('out_of_order')
            seen.add(stamp)
            previous = stamp
            if stamp.second or stamp.microsecond:
                problems.add('off_minute_timestamp')
            minute = stamp.hour * 60 + stamp.minute
            if job['interval'] == 'minute' and 555 <= minute < 930:
                regular.add(stamp)
        except (ValueError, TypeError, AttributeError):
            problems.add('invalid_timestamp')
        numbers = candle[1:]
        if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in numbers):
            problems.add('invalid_number')
            continue
        op, hi, lo, cl, volume = numbers[:5]
        if min(op, hi, lo, cl) <= 0:
            problems.add('nonpositive_price')
        if hi < max(op, lo, cl) or lo > min(op, hi, cl):
            problems.add('inconsistent_ohlc')
        if volume < 0:
            problems.add('negative_volume')
    if job['interval'] == 'day' and len(candles) > 1:
        problems.add('multiple_daily_candles')
    return {'rows': len(candles), 'issues': sorted(problems), 'regular_unique_minutes': len(regular),
            'coverage_calendar_verified': False,
            'status': 'empty_unverified' if not candles else ('quarantined' if problems else 'downloaded_unverified')}


def download_job(client, job, instrument, snapshot_sha, folder):
    token = instrument['instrument_token']
    spec = dict(job, instrument=instrument, snapshot_sha256=snapshot_sha, validator_version=VERSION,
                from_time=job['day'] + ' 00:00:00', to_time=job['day'] + ' 23:59:59', oi=0, continuous=0)
    key = digest(encoded(spec))[:24]
    target = Path(folder) / key
    target.mkdir(parents=True, exist_ok=True)
    manifest = target / 'manifest.json'
    # A lock prevents two processes writing the same chunk concurrently.
    lock = target / 'active.lock'
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError('Chunk is locked by another run; inspect stale locks after a crash.') from None
    os.close(handle)
    try:
        if manifest.exists():
            old = json.loads(manifest.read_text())
            raw = target / 'response.json'
            if old.get('status') == 'downloaded_unverified' and old.get('request') == spec and raw.exists():
                content = raw.read_bytes()
                if digest(content) == old.get('response_sha256') and validate_response(content, job)['status'] == 'downloaded_unverified':
                    return dict(old, resumed=True)
        record = {'request': spec, 'requested_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'started'}
        atomic_write(manifest, encoded(record))
        try:
            body = client.get(f'/instruments/historical/{token}/{job["interval"]}',
                              {'from': spec['from_time'], 'to': spec['to_time'], 'oi': 0, 'continuous': 0})
            # Parse success before saving raw content, avoiding persistence of arbitrary error pages.
            checks = validate_response(body, job)
            atomic_write(target / 'response.json', body)
            record.update(checks, response_sha256=digest(body), received_at_utc=datetime.now(timezone.utc).isoformat())
        except ApiFailure as exc:
            record.update(status='failed', failure=f'{exc.kind}:{exc.status}')
            atomic_write(manifest, encoded(record))
            if exc.status in {401, 403}:
                raise
            return record
        except ValueError:
            record.update(status='failed', failure='invalid_response')
        atomic_write(manifest, encoded(record))
        return record
    finally:
        lock.unlink(missing_ok=True)


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'instruments', 'fetch'])
    parser.add_argument('--execute', action='store_true', help='Enable read-only network requests; default is dry-run.')
    parser.add_argument('--plan', type=Path, default=ROOT / 'config/repair_plan.json')
    args = parser.parse_args()
    store = ROOT / 'work/kite'
    # Do not allow output symlinks to redirect into the original datasets.
    sources = json.loads((ROOT / 'config/datasets.json').read_text())
    for source in sources.values():
        source = Path(source).resolve()
        if store.resolve() == source or source in store.resolve().parents:
            raise ValueError('Download output resolves inside a source dataset.')
    if args.command == 'plan':
        if args.plan.resolve() != (ROOT / 'config/repair_plan.json').resolve():
            raise ValueError('Generated plan location is fixed; custom plans can be read with fetch.')
        plan = make_plan(ROOT / 'outputs/audit/flagged_candles.csv')
        validate_plan(plan)
        atomic_write(args.plan, encoded(plan))
        print(f'Prepared {len(plan["requests"])} requests; no network access.')
        return
    if args.command == 'fetch':
        plan = json.loads(args.plan.read_text())
        validate_plan(plan)
        if not args.execute:
            print(json.dumps({'mode': 'dry-run', 'requests': len(plan['requests']), 'jobs': plan['requests']}, indent=2))
            return
    elif not args.execute:
        print('Dry-run: would retrieve GET /instruments/NSE and save an immutable snapshot.')
        return
    client = Client(os.environ.get('KITE_API_KEY'), os.environ.get('KITE_ACCESS_TOKEN'))
    if args.command == 'instruments':
        content = client.get('/instruments/NSE')
        mapping = instrument_map(content)
        sha = digest(content)
        atomic_write(store / 'instruments' / f'{sha}.csv', content)
        atomic_write(store / 'instrument_snapshot.json', encoded({'sha256': sha, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat()}))
        print(f'Saved NSE cash instrument snapshot: {len(mapping)} symbols.')
        return
    meta = json.loads((store / 'instrument_snapshot.json').read_text())
    sha = meta['sha256']
    if not re.fullmatch(r'[0-9a-f]{64}', sha):
        raise ValueError('Invalid snapshot identifier.')
    content = (store / 'instruments' / f'{sha}.csv').read_bytes()
    if digest(content) != sha:
        raise ValueError('Instrument snapshot checksum mismatch.')
    mapping = instrument_map(content)
    missing = sorted({j['symbol'] for j in plan['requests']} - mapping.keys())
    if missing:
        raise ValueError(f'Unresolved instruments: {missing}; do not guess renamed instruments.')
    results = []
    run_record = {'plan_sha256': digest(encoded(plan)), 'status': 'running', 'results': results}
    atomic_write(store / 'latest_run.json', encoded(run_record))
    for job in plan['requests']:
        try:
            result = download_job(client, job, mapping[job['symbol']], sha, store / 'chunks')
        except ApiFailure:
            run_record['status'] = 'authentication_required'
            atomic_write(store / 'latest_run.json', encoded(run_record))
            raise
        results.append(result)
        print(f'{job["symbol"]} {job["day"]} {job["interval"]}: {result["status"]}' + (' (cached)' if result.get('resumed') else ''))
        atomic_write(store / 'latest_run.json', encoded(run_record))
    run_record['status'] = 'finished_with_failures' if any(r['status'] == 'failed' for r in results) else 'finished'
    atomic_write(store / 'latest_run.json', encoded(run_record))
    if any(r['status'] == 'failed' for r in results):
        raise SystemExit(2)


if __name__ == '__main__':
    try:
        cli()
    except (ValueError, ApiFailure, OSError) as exc:
        print(f'Stopped: {exc}')
        raise SystemExit(1)
