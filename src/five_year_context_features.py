"""V4 adapter of frozen v3 feature formulas; five-year sources and chronological split."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from research_v1 import sha, FEATURES
from context_sources import ROOT

FOLDER = ROOT / 'data/context_training_v4'
RESULTS = ROOT / 'experiments/v4'
CONFIG = ROOT / 'config/context_v4.json'


def candle_features(group, minute):
    """Only bars at/before minute influence inputs. Execution fields are separate."""
    t = minute - 555
    close = group.close.to_numpy(float)
    volume = group.volume.to_numpy(float)
    window = close[t-30:t+1]
    average = volume[t-29:t+1].mean()
    return {
        'return_5': close[t]/close[t-5]-1,
        'return_15': close[t]/close[t-15]-1,
        'return_30': close[t]/close[t-30]-1,
        'volatility_30': float(np.diff(np.log(window)).std()),
        'volume_ratio_5_30': volume[t-4:t+1].mean()/average if average else 0,
        'range_5': (group.high.iloc[t-4:t+1].max()-group.low.iloc[t-4:t+1].min())/close[t],
        'return_since_open': close[t]/group.open.iloc[0]-1,
        'session_fraction': t/375,
    }


def add_time(frame):
    stamps = pd.to_datetime(frame.date, format='ISO8601', utc=True).dt.tz_convert('Asia/Kolkata')
    frame['day'] = stamps.dt.strftime('%Y-%m-%d')
    frame['minute'] = stamps.dt.hour*60 + stamps.dt.minute
    frame['seconds'] = stamps.dt.second
    return frame


def complete(group):
    return len(group) == 375 and not group.seconds.any() and np.array_equal(group.minute.to_numpy(), np.arange(555,930))


def event_masks(frame):
    return {
        'continuation': (frame.return_30 > 0) & (frame.idx_NIFTY_50_return_30 > 0) & (frame.volume_ratio_5_30 >= 1.2),
        'reversal': (frame.return_5 < -frame.volatility_30*np.sqrt(5)) & (frame.idx_NIFTY_50_return_30 >= 0),
        'relative': (frame.relative_return_30 > frame.volatility_30*np.sqrt(30)) & (frame.sector_median_return_30 > 0),
    }


def main():
    if (FOLDER / 'dataset.json').exists():
        raise ValueError('Dataset already prepared. Preserve it; use a new version for changes.')
    config = json.loads(CONFIG.read_text())
    FOLDER.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    source_manifest = []
    rejected = []
    indices = []
    comparisons = []
    official = {}
    all_jobs = json.loads((ROOT / 'experiments/five_year_v4/download_manifest.json').read_text())['requests']
    jobs = {k:r for k,r in all_jobs.items() if r['kind']=='index' and r['interval']=='minute'}
    names = sorted({r['symbol'] for r in jobs.values()})
    context_fields = ['return_5','return_15','return_30','return_since_open','volatility_30']
    for symbol in names:
        batches = []
        for rec in jobs.values():
            if rec['symbol'] != symbol:
                continue
            path = ROOT / rec['path']
            if sha(path) != rec['sha256']:
                raise ValueError('Index source changed.')
            rows = json.loads(path.read_bytes())['data']['candles']
            batches.append(pd.DataFrame(rows, columns=['date','open','high','low','close','volume']))
            source_manifest.append(dict(path=rec['path'], sha256=rec['sha256'], role='index_minute'))
        frame = add_time(pd.concat(batches, ignore_index=True))
        frame = frame.loc[frame.minute.between(555,929)].sort_values(['day','minute'])
        for day, group in frame.groupby('day', sort=True):
            # Official daily close is not assumed equal to final minute quote.
            match = official.get(day, {}).get(symbol.replace('NIFTY FIN SERVICE', 'NIFTY FINANCIAL SERVICES'))
            if match:
                comparisons.append({'symbol': symbol, 'day': day,
                    'high_difference': float(group.high.max())-float(match['High Index Value']),
                    'low_difference': float(group.low.min())-float(match['Low Index Value']),
                    'last_quote_minus_official_close': float(group.close.iloc[-1])-float(match['Closing Index Value'])})
            if not complete(group):
                rejected.append(dict(symbol=symbol, day=day, reason='incomplete_index_session', rows=len(group)))
                continue
            group = group.reset_index(drop=True)
            for minute in config['signal_minutes']:
                feature = candle_features(group, minute)
                indices.append(dict(day=day, signal_minute=minute, index=symbol.replace(' ','_'), **{k:feature[k] for k in context_fields}))
        print('Index features:', symbol, flush=True)
    index_long = pd.DataFrame(indices)
    context = index_long.pivot(index=['day','signal_minute'], columns='index', values=context_fields)
    context.columns = [f'idx_{index}_{field}' for field,index in context.columns]
    context = context.dropna().reset_index()
    quality = json.loads((ROOT/'experiments/five_year_v4/quality_policy.json').read_text())
    manifest = pd.read_csv(ROOT/'experiments/five_year_v4/canonical_inventory.csv')
    manifest = manifest.loc[(manifest.kind=='stock') & (manifest.interval=='minute') & ~manifest.symbol.isin(quality['excluded_symbols'])].copy()
    actions_path=ROOT/'data/five_year_processing_v4/references/study_actions.json'
    actions=json.loads(actions_path.read_text())
    exdates={(r['symbol'],pd.to_datetime(r['exDate'],format='%d-%b-%Y').strftime('%Y-%m-%d')) for r in actions}
    source_manifest.append({'path':actions_path.relative_to(ROOT).as_posix(),'sha256':sha(actions_path),'role':'corporate_action_exclusions'})
    rows = []
    for number, rec in enumerate(manifest.to_dict('records'), 1):
        path = ROOT / rec['path']
        if sha(path) != rec['sha256']:
            raise ValueError('Stock source changed.')
        source_manifest.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=rec['sha256'], role='stock_minute'))
        frame = add_time(pd.read_csv(path, usecols=['date','open','high','low','close','volume']))
        for day, group in frame.groupby('day', sort=True):
            if not complete(group) or (group.volume <= 0).any() or (rec['symbol'],day) in exdates:
                rejected.append(dict(symbol=rec['symbol'], day=day, reason='stock_session_or_zero_volume_or_exdate', rows=len(group)))
                continue
            group = group.reset_index(drop=True)
            for minute in config['signal_minutes']:
                t = minute-555
                entry, exit_ = t+config['entry_delay_bars'], t+config['exit_delay_bars']
                rows.append(dict(symbol=rec['symbol'], day=day, signal_minute=minute,
                    **candle_features(group,minute), signal_close=float(group.close.iloc[t]),
                    volume_last_5=float(group.volume.iloc[t-4:t+1].sum()),
                    entry_open=float(group.open.iloc[entry]), exit_open=float(group.open.iloc[exit_]),
                    entry_volume=float(group.volume.iloc[entry]), exit_volume=float(group.volume.iloc[exit_]),
                    future_return=float(group.open.iloc[exit_]/group.open.iloc[entry]-1)))
        if number % 20 == 0:
            print(f'Stock files {number}/{len(manifest)}', flush=True)
    data = pd.DataFrame(rows).sort_values(['symbol','signal_minute','day'])
    data['seasonal_volume_ratio'] = data.groupby(['symbol','signal_minute']).volume_last_5.transform(lambda s:s/s.shift(1).rolling(20,min_periods=5).mean())
    data = data.merge(context,on=['day','signal_minute'],how='inner',validate='many_to_one')
    data = data.dropna(subset=['seasonal_volume_ratio'])
    breadth = data.groupby(['day','signal_minute']).return_30.agg(panel_mean_return_30='mean',panel_breadth=lambda s:float((s>0).mean()))
    data = data.join(breadth,on=['day','signal_minute'])
    data['relative_return_30'] = data.return_30-data.idx_NIFTY_50_return_30
    sector_columns = [c for c in context.columns if c.endswith('_return_30') and c!='idx_NIFTY_50_return_30']
    data['sector_median_return_30'] = data[sector_columns].median(axis=1)
    features = FEATURES + [c for c in context.columns if c.startswith('idx_')] + ['seasonal_volume_ratio','panel_mean_return_30','panel_breadth','relative_return_30','sector_median_return_30']
    data = data.sort_values(['day','signal_minute','symbol']).reset_index(drop=True)
    data = data.loc[~data.day.isin(quality['quarantined_dates'])].copy()
    data['split'] = np.select([data.day.str[:4].isin(['2021','2022','2023']),data.day.str[:4]=='2024',data.day.str[:4]=='2025'],['train','validation','development'],default='forbidden')
    if (data.split=='forbidden').any() or not np.isfinite(data[features+['future_return']].to_numpy()).all():
        raise ValueError('Invalid features or reserved period.')
    data.to_csv(FOLDER/'samples.csv.gz',index=False,float_format='%.12g',compression={'method':'gzip','mtime':0})
    pd.DataFrame(rejected).to_csv(FOLDER/'omitted_sessions.csv',index=False)
    pd.DataFrame(comparisons).to_csv(RESULTS/'independent_price_comparison.csv',index=False)
    pd.DataFrame(source_manifest).to_csv(FOLDER/'source_manifest.csv',index=False)
    description = {'version':'context_v4','features':features,'rows':len(data),'split_rows':data.split.value_counts().to_dict(),
        'split_sessions':data.groupby('split').day.nunique().to_dict(),'symbols':sorted(data.symbol.unique().tolist()),
        'config_sha256':sha(CONFIG),'builder_sha256':sha(Path(__file__)),
        'dataset_sha256':sha(FOLDER/'samples.csv.gz'),'source_manifest_sha256':sha(FOLDER/'source_manifest.csv'),
        'independent_sample_comparisons':len(comparisons),'source_count':len(source_manifest),
        'deployment':'disabled','2025_used':True,'calendar_complete':False,
        'exclusion_counts':pd.DataFrame(rejected).reason.value_counts().to_dict()}
    (FOLDER/'dataset.json').write_text(json.dumps(description,indent=2)+'\n')
    (RESULTS/'dataset.json').write_text(json.dumps(description,indent=2)+'\n')
    print(json.dumps(description,indent=2),flush=True)


if __name__=='__main__':
    main()
