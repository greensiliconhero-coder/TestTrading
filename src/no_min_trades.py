"""Post-hoc gate sensitivity using preserved models only. No fit calls."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import torch
from research_v1 import ROOT, FEATURES, sha, trade_stats
from neural_v2 import load_bundle, probabilities
from context_models import candidate_signals, simulate

OUT=ROOT/'experiments/no_min_trades'


def select_quote(rows):
    eligible=[r for r in rows if r['trades']>0 and r['mean_net_bps'] is not None and r['mean_net_bps']>0 and r['execution_zero_volume']==0]
    return max(eligible,key=lambda r:r['mean_net_bps']) if eligible else None


def select_portfolio(rows, minimum=None):
    eligible=[key for key,r in rows.items() if (minimum is None or r['trades']>=minimum) and r['net_total_return']>0 and r['exit_capacity_failures']==0]
    return max(eligible,key=lambda key:rows[key]['net_total_return']) if eligible else None


def main():
    if (OUT/'results.json').exists():
        raise ValueError('Sensitivity already completed; preserve this version.')
    OUT.mkdir(parents=True,exist_ok=True)
    model_paths=[ROOT/'models/research_v1.joblib',ROOT/'models/neural_v2/weights.pt',ROOT/'models/neural_v2/resume.pt',ROOT/'models/context_v3/candidates.joblib',ROOT/'models/context_v3/diagnostic_2021.joblib']
    before={p.relative_to(ROOT).as_posix():sha(p) for p in model_paths}
    result={'study':'Post-hoc minimum-trade-count sensitivity','retraining':False,'2025_used':False,'deployment':'disabled','config_sha256':sha(ROOT/'config/no_min_trades.json')}
    original_v1=json.loads((ROOT/'experiments/v1/model_results.json').read_text())
    # Only the preserved v1 tree can be replayed. Logistic validation summaries
    # remain valid historical records; its weights were not saved.
    frame=pd.read_pickle(ROOT/'work/research_v1_samples.pkl')
    if not set(frame.day.str[:4]).issubset({'2021','2022','2023','2024'}):raise ValueError('Unexpected period.')
    tree=joblib.load(ROOT/'models/research_v1.joblib')
    v1=[]
    for year in ['2023','2024']:
        part=frame.loc[frame.day.str[:4]==year]
        p=tree.predict_proba(part[FEATURES])[:,1]
        for threshold in [.5,.55,.6]:
            v1.append({'year':year,'threshold':threshold,**trade_stats(part,p>=threshold,20)})
    validation=[r for r in v1 if r['year']=='2023']
    cached_logistic=[r for r in original_v1['candidates'] if r['model']=='logistic']
    result['v1']={'tree_replayed':v1,'tree_selection_without_min':select_quote(validation),'logistic_historical_validation':cached_logistic,
        'logistic_selection_without_min':select_quote(cached_logistic),'logistic_weights_available':False,
        'units':'mean bps per idealized quote trade; no portfolio capital simulation'}
    print('V1 replay complete: no profitable validation-eligible classifier.',flush=True)
    torch.set_num_threads(4)
    model,mean,std,card=load_bundle()
    descriptor=json.loads((ROOT/'work/neural_v2/dataset.json').read_text())
    for name,key in [('sequences.npy','sequences_sha256'),('metadata.csv','metadata_sha256')]:
        if sha(ROOT/'work/neural_v2'/name)!=descriptor[key]:raise ValueError('Neural input changed.')
    x=np.load(ROOT/'work/neural_v2/sequences.npy',mmap_mode='r')
    meta=pd.read_csv(ROOT/'work/neural_v2/metadata.csv')
    if not set(meta.day.str[:4]).issubset({'2021','2022','2023','2024'}):raise ValueError('Unexpected neural period.')
    neural=[]
    for year in ['2023','2024']:
        idx=np.flatnonzero(meta.day.str[:4]==year)
        part=meta.iloc[idx]
        p=probabilities(model,x,idx,mean,std)
        for threshold in [.5,.55,.6]:
            mask=p>=threshold
            neural.append({'year':year,'threshold':threshold,**trade_stats(part,mask,20)})
            trades=part.loc[mask,['symbol','day','signal_minute','future_return']].copy()
            trades['predicted_probability']=p[mask]
            trades['net_quote_return']=trades.future_return-.002
            trades.to_csv(OUT/f'cnn_{year}_threshold_{threshold:.2f}_trades.csv',index=False)
    choice=select_quote([r for r in neural if r['year']=='2023'])
    later=next((r for r in neural if r['year']=='2024' and choice and r['threshold']==choice['threshold']),None)
    result['neural_v2']={'all_thresholds':neural,'selection_without_min':choice,'selected_2024_comparison':later,
        'original_selection':None,'units':'mean bps per idealized quote trade, not portfolio return or calibrated profit probability'}
    print('CNN no-min selection:',choice,'later:',later,flush=True)
    original=json.loads((ROOT/'experiments/v3/results.json').read_text())
    rows={key:value['validation_2023'] for key,value in original['candidates'].items()}
    selected=select_portfolio(rows)
    final=joblib.load(ROOT/'models/context_v3/candidates.joblib')
    inputs=pd.read_csv(ROOT/'data/context_training_v3/samples.csv.gz')
    desc=json.loads((ROOT/'data/context_training_v3/dataset.json').read_text())
    if sha(ROOT/'data/context_training_v3/samples.csv.gz')!=desc['dataset_sha256']:raise ValueError('Context inputs changed.')
    if not set(inputs.day.str[:4]).issubset({'2021','2022','2023','2024'}):raise ValueError('Unexpected context period.')
    result['context_v3_final']={'original_selection':original['selected_on_2023'],'selection_without_min':selected,
        'all_candidates':original['candidates'],'replay':{},'units':'portfolio return on illustrative INR 50000; estimated fees, capital and execution rules unchanged'}
    if selected:
        model=final['models'][selected];family=selected.rsplit('_',1)[0]
        for split in ['validation','development']:
            part=inputs.loc[inputs.split==split]
            signals=candidate_signals(part,model,family,final['features'],final['config'])
            stats,daily,trades=simulate(signals,sorted(part.day.unique()),final['config'])
            expected=original['candidates'][selected]['validation_2023' if split=='validation' else 'development_2024']
            assert abs(stats['net_total_return']-expected['net_total_return'])<1e-12
            assert stats['trades']==expected['trades']
            result['context_v3_final']['replay'][split]=stats
            daily.to_csv(OUT/f'context_final_selected_{split}_daily.csv',index=False)
            trades.to_csv(OUT/f'context_final_selected_{split}_trades.csv',index=False)
    print('Context final no-min selection:',selected,flush=True)
    # Earlier saved fits: hypothetical select-on-2022 comparison, not a new fit.
    warm=joblib.load(ROOT/'models/context_v3/diagnostic_2021.joblib')
    warm_rows={key:value['earlier_2022'] for key,value in original['candidates'].items()}
    warm_choice=select_portfolio(warm_rows)
    warm_results={}
    for key,model in warm['models'].items():
        warm_results[key]={'selection_period_2022':warm_rows[key]}
        for split,year in [('validation','2023'),('development','2024')]:
            part=inputs.loc[inputs.split==split]
            signals=candidate_signals(part,model,key.rsplit('_',1)[0],warm['features'],warm['config'])
            stats,daily,trades=simulate(signals,sorted(part.day.unique()),warm['config'])
            warm_results[key]['later_'+year]=stats
            if key==warm_choice:
                daily.to_csv(OUT/f'context_diagnostic_selected_{year}_daily.csv',index=False)
                trades.to_csv(OUT/f'context_diagnostic_selected_{year}_trades.csv',index=False)
        print('Earlier saved snapshot evaluated:',key,flush=True)
    result['context_v3_diagnostic']={'scope':'Fits trained on 2021, hypothetical selection on 2022; later 2023/2024 comparisons use the same unchanged earlier fits.',
        'selection_with_200_gate':select_portfolio(warm_rows,200),'selection_without_min':warm_choice,'all_candidates':warm_results}
    after={p.relative_to(ROOT).as_posix():sha(p) for p in model_paths}
    if before!=after:raise ValueError('A fitted-model file changed.')
    result['model_hashes_before_and_after']=before
    result['all_model_hashes_unchanged']=True
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Complete. All model weights unchanged; no training or 2025 access.',flush=True)


if __name__=='__main__':main()
