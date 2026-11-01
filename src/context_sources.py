"""Stage public context references with provenance; never merge into training."""
import csv
import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'data/context_sources_v1'
RECORDS = ROOT / 'experiments/context_sources_v1'
SOURCES = [
    ('kite_nse_instruments', 'https://api.kite.trade/instruments/NSE', 'csv', 'instrument_token', 'Current security/index mapping; not historical identity.'),
    ('nifty50_current', 'https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv', 'csv', 'Symbol', 'Current constituents and industry labels; not point-in-time membership.'),
    ('nifty500_current', 'https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv', 'csv', 'Symbol', 'Current constituents and industry labels; not point-in-time membership.'),
    ('nifty_history_page', 'https://www.niftyindices.com/reports/historical-data', 'html', 'Historical', 'Source page, not a historical index-price dataset.'),
    ('nse_actions_page', 'https://www.nseindia.com/companies-listing/corporate-filings-actions', 'html', 'Corporate', 'Source page, not a corporate-action ledger.'),
] + [
    (f'nse_actions_{year}', f'https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date=01-01-{year}&to_date=31-12-{year}', 'json', None, 'Historical ex-date actions; announcement availability and adjustment factors still require review.')
    for year in range(2021, 2025)
]


def fetch(source):
    name, url, kind, required, limitation = source
    rec = {'name': name, 'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'limitation': limitation}
    try:
        req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
        with request.urlopen(req, timeout=20) as response:
            body = response.read(20_000_001)
            if len(body) > 20_000_000:
                raise ValueError('Response exceeds reference download limit.')
            rec['http_status'] = response.status
        text = body.decode('utf-8-sig')
        if kind == 'csv':
            reader = csv.DictReader(io.StringIO(text))
            if required not in (reader.fieldnames or []):
                raise ValueError('Required CSV header missing.')
            rows = list(reader)
            if not rows:
                raise ValueError('Empty CSV is not a successful download.')
            rec['rows'] = len(rows)
        elif kind == 'json':
            rows = json.loads(text)
            if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) and 'symbol' in row for row in rows):
                raise ValueError('Expected nonempty corporate-action list with symbols.')
            year = int(name[-4:])
            if any(datetime.strptime(row['exDate'], '%d-%b-%Y').year != year for row in rows):
                raise ValueError('Corporate actions outside requested ex-date year.')
            rec['rows'] = len(rows)
        elif required.lower() not in text.lower() or '<html' not in text.lower():
            raise ValueError('Expected source page was not returned.')
        digest = hashlib.sha256(body).hexdigest()
        target = STAGE / 'raw' / f'{name}_{digest[:16]}.{kind}'
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == body
        else:
            target.write_bytes(body)
        rec.update(status='staged_unverified', sha256=digest, bytes=len(body), path=target.relative_to(ROOT).as_posix())
    except error.HTTPError as exc:
        rec.update(status='unavailable', http_status=exc.code, error='HTTP failure; no bypass attempted.')
    except (error.URLError, TimeoutError, OSError, ValueError, UnicodeError) as exc:
        rec.update(status='unavailable', error=type(exc).__name__)
    return rec


def main():
    RECORDS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, SOURCES))
    result = {'training_merge': False, 'reserved_2025_prices_requested': False, 'raw_folder': str(STAGE), 'sources': records}
    (RECORDS / 'public_manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    # Current indices only; do not substitute a stock with a similar name.
    instruments = next((r for r in records if r['name'] == 'kite_nse_instruments' and r['status'] == 'staged_unverified'), None)
    if instruments:
        rows = list(csv.DictReader(io.StringIO((ROOT / instruments['path']).read_text(encoding='utf-8-sig'))))
        wanted = ['NIFTY 50', 'NIFTY BANK', 'NIFTY IT', 'NIFTY FMCG', 'NIFTY AUTO', 'NIFTY PHARMA', 'NIFTY METAL', 'NIFTY ENERGY', 'NIFTY FIN SERVICE']
        selected = []
        for symbol in wanted:
            matches = [r for r in rows if r['tradingsymbol'] == symbol and r['segment'] == 'INDICES' and r['exchange'] == 'NSE']
            if len(matches) == 1:
                selected.append({k: matches[0][k] for k in ['tradingsymbol', 'instrument_token', 'segment', 'exchange']})
        (RECORDS / 'index_instruments.json').write_text(json.dumps({'source_sha256': instruments['sha256'], 'indices': selected, 'unresolved': [s for s in wanted if s not in {r['tradingsymbol'] for r in selected}]}, indent=2) + '\n')
    for r in records:
        print(r['name'], r['status'], r.get('rows', ''), r.get('http_status', ''))


def review_actions():
    """Select study symbols without treating ex-date records as adjustment factors."""
    manifest = json.loads((RECORDS / 'public_manifest.json').read_text())
    with (ROOT / 'experiments/data_review/research_v1/source_manifest.csv').open() as stream:
        symbols = {row['symbol'] for row in csv.DictReader(stream)}
    rows = []
    for record in manifest['sources']:
        if record['name'].startswith('nse_actions_') and record['name'] != 'nse_actions_page' and record['status'] == 'staged_unverified':
            body = (ROOT / record['path']).read_bytes()
            if hashlib.sha256(body).hexdigest() != record['sha256']:
                raise ValueError('Staged source checksum changed.')
            values = json.loads(body)
            year = int(record['name'][-4:])
            if any(datetime.strptime(row['exDate'], '%d-%b-%Y').year != year for row in values):
                raise ValueError('Corporate actions outside requested year.')
            rows.extend(values)
    selected = [row for row in rows if row['symbol'] in symbols]
    target = STAGE / 'review'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'study_universe_actions.json').write_text(json.dumps(selected, indent=2))
    summary = {'all_equity_action_rows': len(rows), 'study_universe_action_rows': len(selected),
               'study_symbols': len(symbols), 'ex_date_years_verified': [2021, 2022, 2023, 2024],
               'adjustments_verified': False, 'historical_membership_verified': False, 'training_merge': False}
    (RECORDS / 'review_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(summary)


if __name__ == '__main__':
    main()
    review_actions()
