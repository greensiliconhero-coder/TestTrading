"""Frozen-seed positive/null controls. These are engineering tests, not trading evidence."""
import json
import platform
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits
from research_v1 import ROOT,sha
from kite_repair import atomic_write,encoded
from ledger_v7 import purged_training_mask

OUT=ROOT/'experiments/backtest_validation_v7'
DATA=ROOT/'data/backtest_validation_v7'
MODELS=ROOT/'models/backtest_validation_v7'


def sample_stats(y,p,threshold,cost):
    selected=np.zeros(len(y),dtype=bool) if threshold is None else p>threshold
    values=y[selected]-cost
    return {'trades':int(selected.sum()),'mean_net_return':float(values.mean()) if len(values) else None,'profitable_trades':int((values>0).sum())}


def main():
    for folder in [OUT,DATA,MODELS]:folder.mkdir(parents=True,exist_ok=True)
    if (OUT/'synthetic_results.json').exists():raise ValueError('Preserve completed controls, do not search seeds.')
    config=json.loads((ROOT/'config/backtest_validation_v7.json').read_text())
    n=config['synthetic_rows'];boundary=config['synthetic_train_rows'];test_start=boundary+config['synthetic_validation_rows'];steps=np.arange(n)
    train=purged_training_mask(steps,steps+1,boundary)
    val=(steps>=boundary)&(steps<test_start)&(steps+1<test_start)
    test=steps>=test_start
    cost=config['synthetic_cost_bps']/10000
    records=[];hashes=[]
    for seed in config['synthetic_seeds']:
        rng=np.random.default_rng(seed);x=rng.normal(size=(n,3));noise=rng.normal(0,config['synthetic_noise_sigma'],size=n)
        for control in ['planted','null']:
            y=noise+config['synthetic_signal_coefficient']*x[:,0] if control=='planted' else noise.copy()
            path=DATA/f'{control}_{seed}.npz';np.savez_compressed(path,x=x,y=y,signal_steps=steps,exit_steps=steps+1,train=train,validation=val,test=test)
            hashes.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path)})
            for name in ['ridge','tree']:
                model=make_pipeline(StandardScaler(),Ridge(alpha=100)) if name=='ridge' else HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=15,learning_rate=.05,l2_regularization=10,min_samples_leaf=100,early_stopping=False,random_state=31)
                model.fit(x[train],y[train]);mp=MODELS/f'{control}_{seed}_{name}.joblib';joblib.dump(model,mp,compress=3)
                vp=model.predict(x[val]);candidates=[]
                for t in config['synthetic_thresholds']:candidates.append(dict(threshold=t,**sample_stats(y[val],vp,t,cost)))
                eligible=[r for r in candidates if r['trades'] and r['mean_net_return']>0]
                choice=max(eligible,key=lambda r:r['mean_net_return'])['threshold'] if eligible else None
                atomic_write(OUT/f'{control}_{seed}_{name}_selection.json',encoded({'threshold':choice,'validation_candidates':candidates}))
                # Only now compute test predictions and statistics.
                tp=model.predict(x[test]);loaded=joblib.load(mp)
                if not np.array_equal(tp[:32],loaded.predict(x[test][:32])):raise ValueError('Model reload changed predictions.')
                corr=float(np.corrcoef(tp,y[test])[0,1]) if np.std(tp)>0 else 0.
                stats=sample_stats(y[test],tp,choice,cost)
                pred=DATA/f'{control}_{seed}_{name}_predictions.npz';np.savez_compressed(pred,validation_predictions=vp,test_predictions=tp)
                records.append(dict(seed=seed,control=control,model=name,selected_threshold=choice,test_correlation=corr,test_stats=stats,model_sha256=sha(mp),predictions_sha256=sha(pred)))
        print('Completed paired controls seed',seed,flush=True)
    summary={}
    for control in ['planted','null']:
        for name in ['ridge','tree']:
            subset=[r for r in records if r['control']==control and r['model']==name];corr=np.array([r['test_correlation'] for r in subset])
            summary[f'{control}_{name}']={'runs':len(subset),'mean_test_correlation':float(corr.mean()),'mean_absolute_test_correlation':float(abs(corr).mean()),'min_test_correlation':float(corr.min()),'max_test_correlation':float(corr.max()),'validation_selected_runs':sum(r['selected_threshold'] is not None for r in subset),'positive_selected_test_runs':sum(r['test_stats']['mean_net_return'] is not None and r['test_stats']['mean_net_return']>0 for r in subset)}
    gates=config['acceptance'];checks={'planted_ridge_detected':summary['planted_ridge']['mean_test_correlation']>=gates['planted_ridge_mean_test_correlation_min']}
    for name in ['ridge','tree']:
        s=summary['null_'+name];checks['null_'+name+'_correlation']=abs(s['mean_test_correlation'])<=gates['null_mean_absolute_signed_test_correlation_max'];checks['null_'+name+'_selection']=s['positive_selected_test_runs']/s['runs']<=gates['null_max_profitable_selected_test_fraction']
    result={'config':config,'train_rows_after_purge':int(train.sum()),'validation_rows_after_purge':int(val.sum()),'test_rows':int(test.sum()),'summary':summary,'acceptance_checks':checks,'all_acceptance_checks_pass':all(checks.values()),'runs':records,'input_hashes':hashes,'runtime':{'python':platform.python_version(),'numpy':np.__version__},'code_sha256':sha(Path(__file__)),'meaning':'Necessary synthetic component validation only. No evidence of a profitable market strategy or proof that all forms of leakage/overfitting are absent.'}
    atomic_write(OUT/'synthetic_results.json',encoded(result));print(json.dumps({'summary':summary,'checks':checks},indent=2),flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=4):main()
