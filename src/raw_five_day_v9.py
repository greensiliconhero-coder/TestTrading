"""Controlled corrected-input refit; preserves biased v5 sample selection explicitly."""
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from research_v1 import ROOT,sha
from five_day_v5 import features,FEATURES
from raw_execution_v8 import replay
from kite_repair import atomic_write,encoded

DATA=ROOT/'data/raw_five_day_v9'
OUT=ROOT/'experiments/raw_five_day_v9'
MODELS=ROOT/'models/raw_five_day_v9'

def build(raw,calendar):
    old=pd.read_csv(ROOT/'data/five_day_v5/samples_with_scores.csv')
    manifest=json.loads((ROOT/'experiments/five_year_v4/official_daily_manifest.json').read_text())
    parts=[];sources={}
    for r in manifest:
        if r['symbol']!='NIFTY 50':continue
        path=ROOT/r['path']
        if sha(path)!=r['sha256']:raise ValueError('Index source changed')
        sources[r['path']]=r['sha256']
        p=pd.DataFrame(json.loads(path.read_text()));p['day']=pd.to_datetime(p.HistoricalDate,format='%d %b %Y').dt.strftime('%Y-%m-%d');parts.append(p)
    idx=pd.concat(parts).set_index('day').CLOSE.astype(float).reindex(calendar)
    if idx.isna().any() or idx.index.duplicated().any():raise ValueError('Index calendar mismatch')
    rows=[]
    for symbol,g in old.groupby('symbol',sort=True):
        f=raw.loc[raw.symbol==symbol].set_index('day').reindex(calendar)
        feat=features(f,idx)
        for r in g.to_dict('records'):
            values=feat.loc[r['day']]
            if not np.isfinite(values.to_numpy()).all():raise ValueError('Missing feature; cannot change sample cohort')
            r.update(values.to_dict());r['entry_open']=float(f.loc[r['entry_day'],'open']);r['exit_open']=float(f.loc[r['exit_day'],'open'])
            r['future_return']=r['exit_open']/r['entry_open']-1
            for name in ['ridge','tree','benchmark_return']:r.pop(name,None)
            rows.append(r)
    data=pd.DataFrame(rows);data['momentum20']=data.ret20;data['reversal5']=-data.ret5
    keys=['symbol','day','entry_day','exit_day','split']
    if set(map(tuple,data[keys].to_numpy()))!=set(map(tuple,old[keys].to_numpy())) or len(data)!=len(old):raise ValueError('Sample identity changed')
    if not np.isfinite(data[FEATURES+['future_return']].to_numpy()).all():raise ValueError('Invalid sample')
    sources['data/five_day_v5/samples_with_scores.csv']=sha(ROOT/'data/five_day_v5/samples_with_scores.csv')
    sources['data/nse_raw_v8/raw_price_panel.csv.gz']=sha(ROOT/'data/nse_raw_v8/raw_price_panel.csv.gz')
    atomic_write(OUT/'sources.json',encoded(sources));data.to_csv(DATA/'samples.csv',index=False)
    return data

def main():
    if (OUT/'locked_selection.json').exists():raise ValueError('Preserve completed or partially evaluated run')
    for p in [DATA,OUT,MODELS]:p.mkdir(parents=True,exist_ok=True)
    path=ROOT/'data/nse_raw_v8/raw_price_panel.csv.gz'
    if sha(path)!=json.loads((ROOT/'experiments/nse_raw_v8/acquisition_summary.json').read_text())['panel_sha256']:raise ValueError('Raw panel changed')
    raw=pd.read_csv(path);calendar=json.loads((ROOT/'experiments/nse_raw_v8/plan.json').read_text())['days']
    data=build(raw,calendar);train=data.loc[data.split=='train']
    models={'ridge':make_pipeline(StandardScaler(),Ridge(alpha=100)),'tree':HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=15,learning_rate=.05,l2_regularization=10,min_samples_leaf=100,early_stopping=False,random_state=31)}
    for name,m in models.items():
        m.fit(train[FEATURES],train.future_return);joblib.dump(m,MODELS/f'{name}.joblib',compress=3)
        if not np.array_equal(m.predict(train[FEATURES].iloc[:32]),joblib.load(MODELS/f'{name}.joblib').predict(train[FEATURES].iloc[:32])):raise ValueError('Reload changed predictions')
    c=json.loads((ROOT/'config/delivery_v6.json').read_text())
    events=json.loads((ROOT/'data/five_year_processing_v4/references/study_actions.json').read_text())
    actions={(a['symbol'],pd.to_datetime(a['exDate'],format='%d-%b-%Y').strftime('%Y-%m-%d')) for a in events}
    results={};scored=[]
    for split in ['validation','development']:
        f=data.loc[data.split==split].copy()
        for name,m in models.items():f[name]=m.predict(f[FEATURES])
        scored.append(f);results[split]={}
        for name in ['equal_weight','momentum20','reversal5','ridge','tree','NIFTYBEES']:
            results[split][name]={}
            for lag in [1,0]:
                for slip in [5,10]:
                    key=f'lag{lag}_slip{slip}';stats,h,t=replay(f,name,raw,calendar,actions,c,lag,slip)
                    results[split][name][key]=stats
                    h.to_csv(DATA/f'{name}_{split}_{key}_account.csv',index=False);t.to_csv(DATA/f'{name}_{split}_{key}_orders.csv',index=False)
        if split=='validation':
            primary={n:r['lag1_slip5']['net_return'] for n,r in results[split].items()}
            eligible=[n for n in ['momentum20','reversal5','ridge','tree'] if primary[n]>max(0,primary['NIFTYBEES'])]
            selected=max(eligible,key=primary.get) if eligible else None
            atomic_write(OUT/'locked_selection.json',encoded({'selected':selected,'validation_primary_returns':primary,'protocol_sha256':sha(ROOT/'RAW_FIVE_DAY_V9.md')}))
        print(split,{n:round(r['lag1_slip5']['net_return'],6) for n,r in results[split].items()},flush=True)
    pd.concat(scored).to_csv(DATA/'evaluation_samples_with_scores.csv',index=False)
    atomic_write(OUT/'results.json',encoded({'selected':selected,'results':results,'split_rows':data.split.value_counts().to_dict(),'model_hashes':{n:sha(MODELS/f'{n}.joblib') for n in models},'samples_sha256':sha(DATA/'samples.csv'),'status':'Development diagnostic only; original hindsight eligibility retained; no deployment.'}))

if __name__=='__main__':main()
