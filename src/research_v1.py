"""Curate immutable copies and evaluate a bounded minute-data learning experiment."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ['return_5', 'return_15', 'return_30', 'volatility_30', 'volume_ratio_5_30',
            'range_5', 'return_since_open', 'session_fraction']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def session_samples(frame, symbol, day):
    """Features end at candle t; entry t+1 open; exit t+30 close. No overnight labels."""
    if len(frame) != 375:
        return []
    op, hi, lo, close, vol = [frame[c].to_numpy(dtype=float) for c in ['open', 'high', 'low', 'close', 'volume']]
    if not all(np.isfinite(a).all() for a in [op, hi, lo, close, vol]) or min(op.min(), hi.min(), lo.min(), close.min()) <= 0:
        raise ValueError('Invalid price escaped curation.')
    samples = []
    for t in range(30, 345, 30):
        history = close[t-30:t+1]
        mean_volume = vol[t-29:t+1].mean()
        sample = {
            'symbol': symbol, 'day': str(day)[:10], 'signal_minute': 555+t,
            'return_5': close[t]/close[t-5]-1, 'return_15': close[t]/close[t-15]-1,
            'return_30': close[t]/close[t-30]-1,
            'volatility_30': np.std(np.diff(np.log(history))),
            'volume_ratio_5_30': vol[t-4:t+1].mean()/mean_volume if mean_volume > 0 else 0,
            'range_5': (hi[t-4:t+1].max()-lo[t-4:t+1].min())/close[t],
            'return_since_open': close[t]/op[0]-1, 'session_fraction': t/375,
            'future_return': close[t+30]/op[t+1]-1,
            'entry_zero_volume': bool(vol[t+1] == 0), 'exit_zero_volume': bool(vol[t+30] == 0),
        }
        samples.append(sample)
    return samples


def prepare():
    config = json.loads((ROOT / 'config/experiment_v1.json').read_text())
    inventory = pd.read_csv(ROOT / 'outputs/audit/file_audit.csv')
    excluded = dict(config['extra_exclusions'])
    numeric_flags = ['invalid_timestamps', 'timestamps_without_offset', 'duplicate_timestamps', 'out_of_order_steps',
                     'invalid_numeric_rows', 'nonpositive_price_rows', 'invalid_ohlc_rows', 'negative_volume_rows']
    for record in inventory.to_dict('records'):
        reasons = [f for f in numeric_flags if pd.notna(record.get(f)) and record[f] > 0]
        if record['status'] == 'error':
            reasons.append('unreadable_file')
        if reasons:
            excluded[record['symbol']] = ', '.join(sorted(set(reasons + [excluded.get(record['symbol'], '')]) - {''}))
    years = config['training_years'] + [config['validation_year'], config['test_year']]
    selected = inventory.loc[(inventory.frequency == 'minute') & inventory.filename_year.isin(years)]
    for symbol, group in selected.groupby('symbol'):
        if set(group.filename_year) != set(years) or (group.status != 'checked').any():
            excluded[symbol] = 'Missing or empty requested year file.'
    selected = selected.loc[~selected.symbol.isin(excluded)].sort_values(['symbol', 'filename_year'])
    if selected.empty:
        raise ValueError('No eligible files.')
    folder = ROOT / 'data/curated_minute_v1'
    folder.mkdir(parents=True, exist_ok=True)
    output = ROOT / 'outputs/research_v1'
    output.mkdir(parents=True, exist_ok=True)
    rows, manifest, rejected = [], [], []
    for i, record in enumerate(selected.to_dict('records'), 1):
        source = Path(record['file'])
        stat = source.stat()
        if stat.st_size != int(record['bytes']) or abs(stat.st_mtime_ns - int(record['mtime_ns'])) > 1024:
            raise ValueError(f'Source changed since audit: {source.name}; audit again before curation.')
        checksum = sha(source)
        target = folder / source.name
        if target.exists() and sha(target) != checksum:
            raise ValueError(f'Existing curated copy differs: {target.name}')
        if not target.exists():
            shutil.copy2(source, target)
        if sha(target) != checksum:
            raise ValueError('Copy checksum mismatch.')
        manifest.append({'symbol': record['symbol'], 'year': int(record['filename_year']), 'source': str(source),
                         'copy': str(target), 'sha256': checksum, 'bytes': stat.st_size})
        data = pd.read_csv(target, usecols=['date','open','high','low','close','volume'])
        timestamps = pd.to_datetime(data['date'], format='ISO8601', utc=True).dt.tz_convert('Asia/Kolkata')
        data['day'] = timestamps.dt.tz_localize(None).dt.normalize()
        data['minute'] = timestamps.dt.hour * 60 + timestamps.dt.minute
        data['seconds'] = timestamps.dt.second
        for day, group in data.groupby('day', sort=True):
            # Strict complete regular-session subset; report every omitted session.
            if len(group) != 375 or not np.array_equal(group.minute.to_numpy(), np.arange(555,930)) or group.seconds.any():
                rejected.append({'symbol': record['symbol'], 'day': str(day)[:10], 'reason': 'Not exact regular 375-minute session', 'rows': len(group)})
                continue
            rows.extend(session_samples(group, record['symbol'], day))
        if i % 12 == 0 or i == len(selected):
            print(f'Prepared {i}/{len(selected)} source copies; {len(rows):,} learning examples', flush=True)
    pd.DataFrame(manifest).to_csv(output / 'source_manifest.csv', index=False)
    pd.DataFrame(rejected, columns=['symbol','day','reason','rows']).to_csv(output / 'omitted_sessions.csv', index=False)
    samples = pd.DataFrame(rows)
    samples.to_pickle(ROOT / 'work/research_v1_samples.pkl')
    summary = {'companies': sorted(selected.symbol.unique().tolist()), 'company_count': int(selected.symbol.nunique()),
               'excluded_companies': excluded, 'copied_files': len(manifest), 'copied_bytes': sum(r['bytes'] for r in manifest),
               'examples': len(samples), 'omitted_sessions': len(rejected),
               'zero_volume_execution_examples': int((samples.entry_zero_volume | samples.exit_zero_volume).sum()),
               'experiment_config_sha256': sha(ROOT / 'config/experiment_v1.json'), 'status': 'structurally_screened_not_independently_certified'}
    (output / 'curation.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


def trade_stats(data, mask, cost_bps):
    selected = data.loc[mask]
    if selected.empty:
        return {'trades': 0, 'mean_gross_bps': None, 'mean_net_bps': None, 'execution_zero_volume': 0}
    return {'trades': len(selected), 'mean_gross_bps': float(selected.future_return.mean()*10000),
            'mean_net_bps': float(selected.future_return.mean()*10000-cost_bps),
            'execution_zero_volume': int((selected.entry_zero_volume | selected.exit_zero_volume).sum())}


def train():
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score, brier_score_loss
    import sklearn
    import joblib
    config = json.loads((ROOT / 'config/experiment_v1.json').read_text())
    output = ROOT / 'outputs/research_v1'
    if (output / 'model_results.json').exists():
        raise ValueError('This experiment was already evaluated. Use a new version and document any repeated test exposure.')
    data = pd.read_pickle(ROOT / 'work/research_v1_samples.pkl')  # locally generated only
    years = data.day.str[:4].astype(int)
    splits = {'train': data.loc[years.isin(config['training_years'])],
              'validation': data.loc[years == config['validation_year']],
              'test': data.loc[years == config['test_year']]}
    models = {'logistic': make_pipeline(StandardScaler(), LogisticRegression(max_iter=300, random_state=7)),
              'hist_gradient_boosting': HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=15,
                  learning_rate=0.05, l2_regularization=10, min_samples_leaf=100, early_stopping=False, random_state=7)}
    training, validation, test = [splits[k] for k in ['train','validation','test']]
    y = (training.future_return > 0).astype(int)
    results, candidates = {}, []
    for name, model in models.items():
        print(f'Training {name} on {len(training):,} examples...', flush=True)
        model.fit(training[FEATURES], y)
        probabilities = model.predict_proba(validation[FEATURES])[:,1]
        auc = float(roc_auc_score(validation.future_return > 0, probabilities))
        results[name] = {'validation_auc': auc, 'validation_brier': float(brier_score_loss(validation.future_return > 0, probabilities))}
        for threshold in config['thresholds']:
            stats = trade_stats(validation, probabilities >= threshold, config['assumed_round_trip_cost_bps'])
            candidates.append(dict(model=name, threshold=threshold, **stats))
    eligible = [r for r in candidates if r['trades'] >= config['minimum_validation_trades']]
    if not eligible:
        raise ValueError('No adequately sampled candidate. Review validation, not test.')
    chosen = max(eligible, key=lambda r:r['mean_net_bps'])
    selected = models[chosen['model']]
    probabilities = selected.predict_proba(test[FEATURES])[:,1]
    prediction = probabilities >= chosen['threshold']
    test_stats = trade_stats(test, prediction, config['assumed_round_trip_cost_bps'])
    # No model selection or threshold changes occur after reading test outcomes.
    baseline_probability = float(y.mean())
    metrics = {'test_auc': float(roc_auc_score(test.future_return > 0, probabilities)),
               'test_brier': float(brier_score_loss(test.future_return > 0, probabilities)),
               'constant_probability_brier': float(brier_score_loss(test.future_return > 0, np.full(len(test), baseline_probability))),
               'always_long_same_times': trade_stats(test, np.ones(len(test), dtype=bool), config['assumed_round_trip_cost_bps']),
               'selected_rule': test_stats}
    costs = {str(cost): trade_stats(test, prediction, cost) for cost in config['stress_cost_bps']}
    calibration = pd.DataFrame({'p':probabilities, 'outcome':(test.future_return>0).astype(int).to_numpy()})
    calibration['bin'] = pd.cut(calibration.p, np.linspace(0,1,11), include_lowest=True)
    calibration.groupby('bin', observed=True).agg(count=('p','size'), predicted=('p','mean'), actual=('outcome','mean')).to_csv(output / 'calibration.csv')
    # Permutation importance measures predictive association, never causal explanation.
    base_auc = metrics['test_auc']
    importance = []
    rng = np.random.default_rng(7)
    for feature in FEATURES:
        shuffled = test[FEATURES].copy()
        shuffled[feature] = rng.permutation(shuffled[feature].to_numpy())
        importance.append({'feature':feature,'auc_drop':base_auc-float(roc_auc_score(test.future_return>0, selected.predict_proba(shuffled)[:,1]))})
    pd.DataFrame(importance).sort_values('auc_drop', ascending=False).to_csv(output / 'feature_importance.csv', index=False)
    output_predictions = test[['symbol','day','signal_minute','future_return']].copy()
    output_predictions['predicted_probability'] = probabilities
    output_predictions['selected_by_rule'] = prediction
    output_predictions.to_csv(output / 'test_predictions.csv', index=False)
    joblib.dump(selected, ROOT / 'work/research_v1_model.joblib')
    result = {'split_sizes':{k:len(v) for k,v in splits.items()}, 'features':FEATURES, 'candidates':candidates,
              'source_manifest_sha256':sha(output / 'source_manifest.csv'),
              'config_sha256':sha(ROOT / 'config/experiment_v1.json'),
              'code_sha256':sha(Path(__file__)),
              'runtime':{'sklearn':sklearn.__version__, 'numpy':np.__version__, 'pandas':pd.__version__},
              'validation_model_metrics':results, 'chosen_on_validation':chosen, 'test_metrics':metrics, 'cost_sensitivity':costs,
              'validation_rule_passed':chosen['mean_net_bps']>0 and chosen['execution_zero_volume']==0,
              'deployment':'disabled', 'untouched_year':config['untouched_year'],
              'interpretation':'Exploratory direction classifier and idealized quote-return study; not an executable backtest or proof of profitability.'}
    (output / 'model_results.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['prepare','train'])
    args = parser.parse_args()
    prepare() if args.command == 'prepare' else train()
