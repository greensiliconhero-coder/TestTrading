"""Export confirmed numeric/candle issues with original CSV line numbers."""
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
audit = root / 'outputs/audit'
inventory = pd.read_csv(audit / 'file_audit.csv')
parts = []
for record in inventory.loc[(inventory.nonpositive_price_rows > 0) | (inventory.invalid_ohlc_rows > 0)].itertuples():
    source = pd.read_csv(record.file)
    prices = source[['open', 'high', 'low', 'close']].apply(pd.to_numeric, errors='coerce')
    nonpositive = (prices <= 0).any(axis=1)
    inconsistent = (prices.high < prices[['open', 'low', 'close']].max(axis=1)) | (prices.low > prices[['open', 'high', 'close']].min(axis=1))
    flagged = source.loc[nonpositive | inconsistent].copy()
    flagged['csv_line'] = flagged.index + 2
    flagged['source_file'] = record.file
    flagged['nonpositive_price'] = nonpositive.loc[flagged.index]
    flagged['inconsistent_ohlc'] = inconsistent.loc[flagged.index]
    parts.append(flagged)
issues = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
issues.to_csv(audit / 'flagged_candles.csv', index=False)
print('Flagged source rows:', len(issues))
if len(issues):
    print(issues.groupby('source_file').size().to_string())
    print(issues.loc[issues.inconsistent_ohlc, ['date', 'open', 'high', 'low', 'close', 'csv_line']].to_string(index=False))
