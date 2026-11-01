"""Read-only source audit. No imputation, adjustments, training or source writes."""
from __future__ import annotations
import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

REQUIRED = ['date', 'open', 'high', 'low', 'close', 'volume']
NUMERIC = REQUIRED[1:]


def inspect_frame(df: pd.DataFrame, frequency: str, symbol: str):
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError(f'Missing columns: {missing}')
    result = {'rows': len(df)}
    if df.empty:
        return result | {'status': 'empty'}, pd.DataFrame()
    # Require an explicit offset; never silently interpret naive source time as UTC.
    raw = df['date'].astype(str)
    offset = raw.str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$', regex=True)
    dates = pd.to_datetime(raw.where(offset), format='ISO8601', utc=True, errors='coerce').dt.tz_convert('Asia/Kolkata')
    values = df[NUMERIC].apply(pd.to_numeric, errors='coerce')
    finite = values.notna() & ~values.isin([float('inf'), float('-inf')])
    invalid_numbers = ~finite.all(axis=1)
    bad_price = (values[['open', 'high', 'low', 'close']] <= 0).any(axis=1)
    bad_ohlc = ((values.high < values[['open', 'close', 'low']].max(axis=1)) |
                (values.low > values[['open', 'close', 'high']].min(axis=1)))
    valid_dates = dates.dropna()
    minutes = dates.dt.hour * 60 + dates.dt.minute
    regular = (minutes >= 555) & (minutes < 930)
    result.update(
        status='checked', first=str(valid_dates.min()), last=str(valid_dates.max()),
        invalid_timestamps=int(dates.isna().sum()),
        timestamps_without_offset=int((~offset).sum()),
        duplicate_timestamps=int(valid_dates.duplicated().sum()),
        out_of_order_steps=int((valid_dates.diff().dt.total_seconds() < 0).sum()),
        invalid_numeric_rows=int(invalid_numbers.sum()), nonpositive_price_rows=int(bad_price.sum()),
        invalid_ohlc_rows=int(bad_ohlc.sum()), negative_volume_rows=int((values.volume < 0).sum()),
        zero_volume_rows=int((values.volume == 0).sum()),
        missing_oi_rows=int(df['oi'].isna().sum()) if 'oi' in df else len(df),
        outside_regular_session_rows=int((~regular & dates.notna()).sum()) if frequency == 'minute' else 0,
        off_minute_rows=int(((dates.dt.second != 0) & dates.notna()).sum()),
    )
    clean = values.assign(timestamp=dates)
    clean = clean.loc[dates.notna()].sort_values('timestamp')
    clean['day'] = clean.timestamp.dt.tz_localize(None).dt.normalize()
    grouped = clean.groupby('day', sort=True)
    sessions = grouped.agg(open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
                           close=('close', 'last'), volume=('volume', lambda x: x.sum(min_count=1)),
                           rows=('timestamp', 'size'), unique_timestamps=('timestamp', 'nunique'))
    sessions['symbol'] = symbol
    if frequency == 'minute':
        # Coverage only: 375 is a reference for normal NSE cash sessions, not a calendar assertion.
        regular_clean = clean.loc[(clean.timestamp.dt.hour * 60 + clean.timestamp.dt.minute).between(555, 929)]
        counts = regular_clean.groupby('day').timestamp.nunique()
        sessions['regular_unique_minutes'] = counts.reindex(sessions.index, fill_value=0)
        sessions['missing_regular_minutes_reference'] = 375 - sessions.regular_unique_minutes
        result['sessions_short_of_375_reference'] = int((sessions.regular_unique_minutes < 375).sum())
    result['sessions'] = len(sessions)
    sessions.index = sessions.index.strftime('%Y-%m-%d')
    return result, sessions.reset_index()


def run(config: Path, output: Path):
    sources = json.loads(config.read_text(encoding='utf-8'))
    resolved_output = output.resolve()
    for root in sources.values():
        source = Path(root).resolve()
        if not source.is_dir():
            raise ValueError(f'Source directory unavailable: {source}')
        if resolved_output == source or source in resolved_output.parents:
            raise ValueError('Output must not be inside a source dataset.')
    output.mkdir(parents=True, exist_ok=True)
    records, session_sets = [], {'daily': [], 'minute': []}
    for frequency, root in sources.items():
        files = sorted(Path(root).rglob('*.csv'))
        for i, path in enumerate(files, 1):
            before = path.stat()
            symbol, _, filename_year = path.stem.rpartition('_')
            record = {'frequency': frequency, 'file': str(path), 'symbol': symbol or path.stem,
                      'filename_year': filename_year, 'bytes': before.st_size, 'mtime_ns': before.st_mtime_ns}
            try:
                result, sessions = inspect_frame(pd.read_csv(path), frequency, record['symbol'])
                record.update(result)
                if not sessions.empty:
                    sessions['source_file'] = str(path)
                    session_sets[frequency].append(sessions)
                after = path.stat()
                record['changed_during_read'] = before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns
            except Exception as exc:
                record.update(status='error', error=f'{type(exc).__name__}: {exc}')
            records.append(record)
            if i % 25 == 0 or i == len(files):
                print(f'{frequency}: {i}/{len(files)} inspected', flush=True)
    inventory = pd.DataFrame(records)
    inventory.to_csv(output / 'file_audit.csv', index=False)
    sets = {}
    for frequency, parts in session_sets.items():
        sets[frequency] = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        sets[frequency].to_csv(output / f'{frequency}_sessions.csv', index=False)
    daily, minute = sets['daily'], sets['minute']
    reconciliation = pd.DataFrame()
    overlap_duplicates = {}
    for frequency, data in sets.items():
        overlap_duplicates[frequency] = int(data.duplicated(['symbol', 'day'], keep=False).sum()) if not data.empty else 0
    if not daily.empty and not minute.empty:
        # Never multiply rows through ambiguous symbol/day matches.
        daily = daily.loc[~daily.duplicated(['symbol', 'day'], keep=False)]
        minute = minute.loc[~minute.duplicated(['symbol', 'day'], keep=False)]
        reconciliation = daily.merge(minute, on=['symbol', 'day'], how='outer', suffixes=('_daily', '_minute'), indicator=True)
        for field in NUMERIC:
            reconciliation[f'{field}_difference'] = reconciliation[f'{field}_minute'] - reconciliation[f'{field}_daily']
        reconciliation.to_csv(output / 'daily_minute_comparison.csv', index=False)
    metrics = ['invalid_timestamps', 'timestamps_without_offset', 'duplicate_timestamps', 'out_of_order_steps',
               'invalid_numeric_rows', 'nonpositive_price_rows', 'invalid_ohlc_rows', 'negative_volume_rows',
               'zero_volume_rows', 'outside_regular_session_rows', 'sessions_short_of_375_reference']
    summary = {'created_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
               'pandas': pd.__version__, 'sources': sources, 'datasets': {}, 'ambiguous_symbol_days': overlap_duplicates}
    lines = ['# Trading data audit', '', 'Read-only scan; original data was not modified. No model has been trained and no trading performance is claimed.', '']
    for frequency in sources:
        subset = inventory.loc[inventory.frequency == frequency]
        totals = {m: int(subset[m].fillna(0).sum()) if m in subset else 0 for m in metrics}
        info = {'files': len(subset), 'symbols': int(subset.symbol.nunique()),
                'rows': int(subset.get('rows', pd.Series(dtype=float)).fillna(0).sum()),
                'empty_files': int((subset.status == 'empty').sum()),
                'error_files': int((subset.status == 'error').sum()), **totals}
        data = sets[frequency]
        if not data.empty:
            info.update(first_day=data.day.min(), last_day=data.day.max())
        summary['datasets'][frequency] = info
        lines += [f'## {frequency.capitalize()}', '', *[f'- {k}: {v}' for k, v in info.items()], '']
    if not reconciliation.empty:
        matches = reconciliation.loc[reconciliation._merge == 'both']
        comparison = {'matched_symbol_days': len(matches), 'daily_only_days': int((reconciliation._merge == 'left_only').sum()),
                      'minute_only_days': int((reconciliation._merge == 'right_only').sum())}
        for field in NUMERIC:
            comparison[f'{field}_different_days'] = int((matches[f'{field}_difference'].abs() > (0.011 if field != 'volume' else 0)).sum())
        summary['comparison'] = comparison
        lines += ['## Cross-frequency comparison', '', *[f'- {k}: {v}' for k, v in comparison.items()], '']
    empty = inventory.loc[inventory.status.isin(['empty', 'error'])]
    lines += ['## Files requiring attention', '']
    lines += [f'- {r.frequency}: {Path(r.file).name} ({r.status})' for r in empty.itertuples()]
    lines += ['', '## Interpretation and remaining work', '',
              '- This is a structural audit, not validation against an independent market-data vendor.',
              '- The 375-minute reference assumes 09:15 through 15:29 IST, minute-start labels, and normal cash sessions. Special sessions, trading halts and intervals without trades can differ. No exchange calendar has been applied.',
              '- Session aggregates are diagnostic only. They include source rows, even when flagged; they are not cleaned model inputs. Duplicate rows can inflate aggregate volume.',
              '- Daily close can differ from the final minute close due to official closing-price methodology. Auctions and vendor conventions can also affect comparisons; disagreement alone does not establish corruption.',
              '- Confirm source, timestamp conventions, minute-volume semantics and corporate-action adjustment policy before modelling.',
              '- Symbol names are inferred from filenames and require verification against instrument identifiers. Historical index membership and delisted securities have not been established.',
              '- Entire missing trading days require a verified exchange calendar and instrument listing history to diagnose.',
              '- Missing OI is not a blocker for cash-equity research.',
              '- Do not select a model or trading horizon using the final held-out evaluation period.',
              '', 'Detailed evidence: file_audit.csv, daily_sessions.csv, minute_sessions.csv, daily_minute_comparison.csv, summary.json.', '']
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (output / 'audit_report.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1] / 'config/datasets.json')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'outputs/audit')
    args = parser.parse_args()
    run(args.config, args.output)
