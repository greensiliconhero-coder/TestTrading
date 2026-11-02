"""Preserved v1 classifier definitions on audited v4 data; no test selection."""
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from research_v1 import ROOT, FEATURES, session_samples, trade_stats, sha
from context_features import add_time, complete
from neural_v2 import window_features
from kite_repair import atomic_write, encoded

DATA=ROOT/'data/classifiers_v4'
OUT=ROOT/'experiments/classifiers_v4'
MODELS=ROOT/'models/classifiers_v4'


def prepare():
    DATA.mkdir(parents=True,exist_ok=True)
    if (DATA/'dataset.json').exists():return
    inventory=pd.read_csv(ROOT/'experiments/five_year_v4/canonical_inventory.csv')
    quality=json.loads((ROOT/'experiments/five_year_v4/quality_policy.json').read_text())
    actions=json.loads((ROOT/'data/five_year_processing_v4/references/study_actions.json').read_text())
    exdates={(r['symbol'],pd.to_datetime(r['exDate'],format='%d-%b-%Y').strftime('%Y-%m-%d')) for r in actions}
    inventory=inventory.loc[(inventory.kind=='stock')&(inventory.interval=='minute')&~inventory.symbol.isin(quality['excluded_symbols'])]
    rows=[];meta=[];parts=[]
    for number,rec in enumerate(inventory.to_dict('records'),1):
        path=ROOT/rec['path']
        if sha(path)!=rec['sha256']:raise ValueError('Canonical input changed.')
        f=add_time(pd.read_csv(path));windows=[]
        for day,g in f.groupby('day',sort=True):
            if day in quality['quarantined_dates'] or (rec['symbol'],day) in exdates or not complete(g) or (g.volume<=0).any():continue
            g=g.reset_index(drop=True);samples=session_samples(g,rec['symbol'],day);rows.extend(samples)
            a=g[['open','high','low','close','volume']].to_numpy()
            for row in samples:
                if row['signal_minute']<615:continue
                t=row['signal_minute']-555
                windows.append(window_features(a[t-59:t+1]));meta.append(row)
        if windows:
            part=DATA/f'part_{number}.npy';np.save(part,np.stack(windows));parts.append(part)
        if number%20==0:print('Classifier preparation',number,'/',len(inventory),flush=True)
    pd.DataFrame(rows).to_csv(DATA/'samples.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(meta).to_csv(DATA/'metadata.csv',index=False)
    x=np.lib.format.open_memmap(DATA/'sequences.npy',mode='w+',dtype='float32',shape=(len(meta),5,60));offset=0
    for p in parts:
        a=np.load(p);x[offset:offset+len(a)]=a;offset+=len(a)
    x.flush();del x
    atomic_write(DATA/'dataset.json',encoded({'rows':len(rows),'sequence_rows':len(meta),'source_inventory_sha256':sha(ROOT/'experiments/five_year_v4/canonical_inventory.csv'),'samples_sha256':sha(DATA/'samples.csv.gz'),'sequences_sha256':sha(DATA/'sequences.npy'),'metadata_sha256':sha(DATA/'metadata.csv'),'quality_policy_sha256':sha(ROOT/'experiments/five_year_v4/quality_policy.json')}))


def train():
    OUT.mkdir(parents=True,exist_ok=True);MODELS.mkdir(parents=True,exist_ok=True)
    if (OUT/'results.json').exists():return
    data=pd.read_csv(DATA/'samples.csv.gz');desc=json.loads((DATA/'dataset.json').read_text())
    if sha(DATA/'samples.csv.gz')!=desc['samples_sha256']:raise ValueError('Inputs changed')
    train=data.loc[data.day.str[:4].isin(['2021','2022','2023'])];val=data.loc[data.day.str[:4]=='2024'];test=data.loc[data.day.str[:4]=='2025']
    models={'logistic':make_pipeline(StandardScaler(),LogisticRegression(max_iter=300,random_state=7)),'hist_gradient_boosting':HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=15,learning_rate=.05,l2_regularization=10,min_samples_leaf=100,early_stopping=False,random_state=7)}
    results={};choices={}
    for name,model in models.items():
        print('Training',name,flush=True);model.fit(train[FEATURES],train.future_return>0)
        joblib.dump(model,MODELS/f'{name}.joblib',compress=3)
        p=model.predict_proba(val[FEATURES])[:,1]
        q=joblib.load(MODELS/f'{name}.joblib').predict_proba(val[FEATURES].iloc[:32])[:,1]
        if not np.array_equal(p[:32],q):raise ValueError('Reload mismatch')
        candidates=[dict(threshold=t,**trade_stats(val,p>=t,20)) for t in [.5,.55,.6]]
        eligible=[r for r in candidates if r['trades']>0 and r['mean_net_bps']>0 and r['execution_zero_volume']==0]
        choices[name]=max(eligible,key=lambda r:r['mean_net_bps'])['threshold'] if eligible else None
        results[name]={'validation_auc':float(roc_auc_score(val.future_return>0,p)),'validation_thresholds':candidates,'model_sha256':sha(MODELS/f'{name}.joblib')}
    atomic_write(OUT/'locked_selection.json',encoded(choices))
    for name,model in models.items():
        p=model.predict_proba(test[FEATURES])[:,1];t=choices[name]
        results[name].update(test_auc=float(roc_auc_score(test.future_return>0,p)),selected_threshold=t,test_selected=None if t is None else trade_stats(test,p>=t,20),test_thresholds=[dict(threshold=t,**trade_stats(test,p>=t,20)) for t in [.5,.55,.6]])
        pred=test[['symbol','day','signal_minute','future_return']].copy();pred['probability']=p;pred.to_csv(DATA/f'{name}_test_predictions.csv.gz',index=False)
    atomic_write(OUT/'results.json',encoded({'models':results,'training_rows':len(train),'validation_rows':len(val),'test_rows':len(test),'dataset':desc,'deployment':'disabled','interpretation':'Idealized quote returns; threshold frozen on 2024, test 2025. Common retrospective quality screen limits inference.'}))


if __name__=='__main__':
    import sys
    prepare() if sys.argv[1]=='prepare' else train()
