"""Summarize actual audited session dates, not just filename years."""
import argparse
from pathlib import Path
import pandas as pd


def run(folder):
    parts = []
    for frequency in ['daily', 'minute']:
        data = pd.read_csv(folder / f'{frequency}_sessions.csv')
        if data.empty:
            continue
        data['year'] = pd.to_datetime(data.day).dt.year
        table = data.groupby(['symbol', 'year']).agg(
            sessions=('day', 'nunique'), first_day=('day', 'min'), last_day=('day', 'max'))
        table['frequency'] = frequency
        parts.append(table.reset_index())
    coverage = pd.concat(parts, ignore_index=True)
    coverage.to_csv(folder / 'symbol_year_coverage.csv', index=False)
    lines = ['# Coverage findings', '', 'Counts below use actual timestamps, not filename labels.', '']
    for frequency in ['daily', 'minute']:
        data = coverage.loc[coverage.frequency == frequency]
        years = sorted(data.year.unique())
        absent = sorted(set(range(int(min(years)), int(max(years)) + 1)) - set(years))
        lines += [f'## {frequency.capitalize()}', '', f'- Entire absent years within observed range: {absent or "none"}', '', '| Year | Symbols with data | Symbol-days |', '|---|---:|---:|']
        grouped = data.groupby('year').agg(symbols=('symbol', 'nunique'), sessions=('sessions', 'sum'))
        lines += [f'| {year} | {row.symbols} | {row.sessions} |' for year, row in grouped.iterrows()]
        lines += ['']
    lines += ['## Next decisions', '',
              '1. Investigate absent years with the provider/downloader. Do not interpolate entire missing periods.',
              '2. Establish why the instrument universe differs over time before selecting a common research sample.',
              '3. Confirm corporate-action adjustments and official daily close conventions before treating cross-frequency differences as bad data.',
              '4. A model should not be trained until material numeric errors and duplicate timestamps are resolved explicitly.',
              '5. Preserve a final chronological holdout and record proposed horizons before comparing model performance.', '']
    (folder / 'coverage_report.md').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'outputs/audit')
    run(parser.parse_args().output)
