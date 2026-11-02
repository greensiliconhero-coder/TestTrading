"""Bounded chronological model comparisons and capital-constrained simulation."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import sklearn
import platform
import subprocess
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from five_year_context_features import ROOT, FOLDER, RESULTS, CONFIG, event_masks
from research_v1 import sha

MODELS = ROOT/'models/context_v4'


def fees(buy, sell, day):
    rate = 0.0000345
    for start, value in [('2023-04-01',0.0000325),('2024-04-01',0.0000322),('2024-10-01',0.0000297)]:
        if day >= start:
            rate = value
    brokerage = min(20,buy*0.0003)+min(20,sell*0.0003)
    exchange = (buy+sell)*rate
    sebi = (buy+sell)*0.000001
    return (brokerage+exchange+sebi)*1.18 + sell*0.00025 + buy*0.00003


def candidate_signals(frame, model, family, features, config):
    selected = frame.loc[event_masks(frame)[family]].copy()
    if model['kind']=='unavailable':
        selected['score'] = 0.0
        return selected.iloc[:0]
    if model['kind']=='rule':
        selected['score'] = selected.return_30 if family=='continuation' else (-selected.return_5 if family=='reversal' else selected.relative_return_30)
    else:
        selected['score'] = model['estimator'].predict(selected[features]) if len(selected) else pd.Series(dtype=float)
        hurdle = selected.day.map(lambda day:fees(config['position_budget'],config['position_budget'],day)/config['position_budget'])
        hurdle += (2*config['slippage_bps_per_side']+config['forecast_margin_bps'])/10000
        selected = selected.loc[selected.score > hurdle]
    return selected


def simulate(signals, all_days, config, slippage=None):
    """Nonoverlapping 30-minute batches; whole shares and cash accounting."""
    slip = (config['slippage_bps_per_side'] if slippage is None else slippage)/10000
    cash = float(config['initial_capital'])
    daily = []
    trades = []
    grouped = {day:g for day,g in signals.groupby('day')}
    for day in sorted(all_days):
        initial = cash
        group = grouped.get(day)
        if group is not None:
            previous_exit = -1
            for minute, batch in group.groupby('signal_minute',sort=True):
                entry_minute = minute + config['entry_delay_bars']
                if entry_minute < previous_exit:
                    raise ValueError('Simulator requires nonoverlapping execution batches.')
                previous_exit = minute + config['exit_delay_bars']
                batch = batch.sort_values(['score','symbol'],ascending=[False,True])
                positions = []
                for row in batch.itertuples():
                    if len(positions)>=config['maximum_positions']:
                        break
                    entry = row.entry_open*(1+slip)
                    exit_ = row.exit_open*(1-slip)
                    quantity = int(min(config['position_budget'],cash)/entry)
                    quantity = min(quantity,int(row.entry_volume*config['participation_fraction']))
                    # Reserve the entry component of fees, never borrow cash.
                    while quantity>0 and quantity*entry+fees(quantity*entry,0,day)>cash:
                        quantity-=1
                    if quantity<=0:
                        continue
                    buy, sell = quantity*entry, quantity*exit_
                    entry_fee = fees(buy,0,day)
                    cash -= buy+entry_fee
                    positions.append((row,quantity,buy,sell,entry_fee))
                for row,quantity,buy,sell,entry_fee in positions:
                    exit_fee = fees(0,sell,day)
                    cash += sell-exit_fee
                    trades.append({'symbol':row.symbol,'day':day,'signal_minute':int(minute),
                        'quantity':quantity,'buy':buy,'sell':sell,'fees':entry_fee+exit_fee,
                        'net_pnl':sell-buy-entry_fee-exit_fee,'score':row.score,
                        'exit_capacity_failure':quantity>row.exit_volume*config['participation_fraction']})
                if cash < -1e-6:
                    raise ValueError('Negative cash.')
        daily.append({'day':day,'equity':cash,'return':cash/initial-1})
    equity = np.array([config['initial_capital']]+[x['equity'] for x in daily])
    returns = np.array([x['return'] for x in daily])
    peak = np.maximum.accumulate(equity)
    frame = pd.DataFrame(trades)
    stats = {'trades':len(trades),'final_equity':cash,'net_total_return':cash/config['initial_capital']-1,
        'daily_close_max_drawdown':float((equity/peak-1).min()),
        'daily_sharpe':float(returns.mean()/returns.std(ddof=1)*np.sqrt(252)) if len(returns)>1 and returns.std(ddof=1)>0 else None,
        'total_fees':float(frame.fees.sum()) if len(frame) else 0,
        'exit_capacity_failures':int(frame.exit_capacity_failure.sum()) if len(frame) else 0,
        'mean_daily_return':float(returns.mean()),'active_days':int((returns!=0).sum()),
        'turnover_over_initial_capital':float((frame.buy.sum()+frame.sell.sum())/config['initial_capital']) if len(frame) else 0}
    return stats,pd.DataFrame(daily),frame


def fit(frame, features, family, kind, config):
    if kind=='rule':
        return {'kind':'rule','family':family}
    selected = frame.loc[event_masks(frame)[family]]
    if len(selected)<1000:
        return {'kind':'unavailable','training_rows':len(selected)}
    estimator = make_pipeline(StandardScaler(),Ridge(alpha=config['ridge_alpha'])) if kind=='ridge' else HistGradientBoostingRegressor(**config['tree'],random_state=config['seed'])
    estimator.fit(selected[features],selected.future_return)
    return {'kind':kind,'family':family,'estimator':estimator,'training_rows':len(selected)}


def uncertainty(returns, config):
    a = np.asarray(returns)
    rng = np.random.default_rng(config['seed'])
    block = config['bootstrap_block_sessions']
    draws = []
    for _ in range(config['bootstrap_repetitions']):
        starts = rng.integers(0,len(a),size=int(np.ceil(len(a)/block)))
        idx = ((starts[:,None]+np.arange(block))%len(a)).ravel()[:len(a)]
        draws.append(a[idx].mean())
    return {'mean_daily_return_lower_95_one_sided':float(np.quantile(draws,.05)),
        'mean_daily_return_lower_bonferroni_9':float(np.quantile(draws,.05/9)),
        'method':'circular five-session block bootstrap; exploratory, assumes local stationarity; Bonferroni covers nine declared candidates, not all prior research'}


def main():
    if (RESULTS/'results.json').exists():
        card = json.loads((MODELS/'bundle.json').read_text())
        if sha(MODELS/'candidates.joblib')!=card['models_sha256']:
            raise ValueError('Saved model checksum mismatch.')
        print('Completed models exist and pass hash check; no retraining.')
        return
    config = json.loads(CONFIG.read_text())
    desc = json.loads((FOLDER/'dataset.json').read_text())
    if desc['config_sha256']!=sha(CONFIG) or desc['dataset_sha256']!=sha(FOLDER/'samples.csv.gz'):
        raise ValueError('Prepared dataset/config changed.')
    data = pd.read_csv(FOLDER/'samples.csv.gz')
    features = desc['features']
    if not set(data.day.str[:4]).issubset({'2021','2022','2023','2024','2025'}):
        raise ValueError('Forbidden period.')
    MODELS.mkdir(parents=True,exist_ok=True)
    models = {}
    diagnostic_models = {}
    outcomes = {}
    predictions = []
    days = {name:sorted(g.day.unique()) for name,g in data.groupby('split')}
    # Earlier chronological diagnostic. Never used to tune this fixed study.
    warm_train = data.loc[data.day.str[:4]=='2021']
    warm_eval = data.loc[data.day.str[:4]=='2022']
    train = data.loc[data.split=='train']
    validation = data.loc[data.split=='validation']
    development = data.loc[data.split=='development']
    for family in config['event_families']:
        for kind in config['models']:
            key = family+'_'+kind
            print('Fitting',key,flush=True)
            earlier = fit(warm_train,features,family,kind,config)
            diagnostic_models[key] = earlier
            signals = candidate_signals(warm_eval,earlier,family,features,config)
            warm_stats,_,_ = simulate(signals,sorted(warm_eval.day.unique()),config)
            model = fit(train,features,family,kind,config)
            models[key] = model
            joblib.dump(model,MODELS/(key+'.joblib'),compress=3)
            signals = candidate_signals(validation,model,family,features,config)
            val_stats,daily,trades = simulate(signals,days['validation'],config)
            val_stats['uncertainty'] = uncertainty(daily['return'],config)
            daily.to_csv(RESULTS/f'{key}_validation_daily.csv',index=False)
            trades.to_csv(FOLDER/f'{key}_validation_trades.csv.gz',index=False,compression={'method':'gzip','mtime':0})
            pred = validation[['symbol','day','signal_minute','future_return']].copy()
            pred['candidate'] = key
            pred['event'] = event_masks(validation)[family].to_numpy()
            pred['forecast'] = model['estimator'].predict(validation[features]) if model['kind'] in {'ridge','tree'} else np.nan
            predictions.append(pred)
            outcomes[key] = {'earlier_2022':warm_stats,'validation_2024':val_stats,'training_event_rows':model.get('training_rows')}
            print(key,'validation return:',val_stats['net_total_return'],'trades:',val_stats['trades'],flush=True)
    eligible = [key for key,value in outcomes.items() if value['validation_2024']['trades']>=config['minimum_validation_trades'] and value['validation_2024']['exit_capacity_failures']==0 and value['validation_2024']['net_total_return']>0]
    chosen = max(eligible,key=lambda key:outcomes[key]['validation_2024']['net_total_return']) if eligible else None
    (RESULTS/'locked_selection.json').write_text(json.dumps({'selected_on_2024':chosen}))
    joblib.dump({'models':models,'features':features,'config':config,'chosen':chosen},MODELS/'candidates.joblib',compress=3)
    # Choice is persisted before 2025 evaluation.
    for key,model in models.items():
        signals = candidate_signals(development,model,key.rsplit('_',1)[0],features,config)
        stats,daily,trades = simulate(signals,days['development'],config)
        stats['uncertainty'] = uncertainty(daily['return'],config)
        stressed,_,_ = simulate(signals,days['development'],config,config['stress_slippage_bps_per_side'])
        outcomes[key]['test_2025'] = stats
        outcomes[key]['test_2025_stress'] = stressed
        daily.to_csv(RESULTS/f'{key}_development_daily.csv',index=False)
        trades.to_csv(FOLDER/f'{key}_development_trades.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.concat(predictions,ignore_index=True).to_csv(FOLDER/'validation_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    joblib.dump({'models':models,'features':features,'config':config,'chosen':chosen},MODELS/'candidates.joblib',compress=3)
    joblib.dump({'models':diagnostic_models,'features':features,'config':config},MODELS/'diagnostic_2021.joblib',compress=3)
    restored = joblib.load(MODELS/'candidates.joblib')
    delta = 0.0
    for key,model in models.items():
        if model['kind'] in {'ridge','tree'}:
            a = model['estimator'].predict(validation[features].iloc[:32])
            b = restored['models'][key]['estimator'].predict(validation[features].iloc[:32])
            if not np.array_equal(a,b):
                raise ValueError('Restored model changed predictions.')
    card = {'version':'context_v4','models_sha256':sha(MODELS/'candidates.joblib'),'dataset_sha256':desc['dataset_sha256'],
        'diagnostic_models_sha256':sha(MODELS/'diagnostic_2021.joblib'),'quality_config_sha256':desc.get('quality_config_sha256'),
        'config_sha256':sha(CONFIG),'training_code_sha256':sha(Path(__file__)),'features':features,'selected_candidate':chosen,
        'all_candidates_saved':list(models),'save_reload_max_difference':delta,'deployment':'disabled','2025_used':True,
        'versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'joblib':joblib.__version__},
        'training_git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
    (MODELS/'bundle.json').write_text(json.dumps(card,indent=2)+'\n')
    result = {'selected_on_2024':chosen,'candidate_count':len(models),'candidates':outcomes,'dataset':desc,
        'deployment':'disabled','2025_used':True,'save_reload_max_difference':delta,
        'verdict':'No validation-eligible profitable candidate; selected cash.' if chosen is None else 'Exploratory validation winner only; assess development, stress, uncertainty and forward evidence before any trading claim.'}
    (RESULTS/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Selected:',chosen,'Saved all models. No live deployment.',flush=True)


if __name__=='__main__':
    main()
