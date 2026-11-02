"""Bounded five-session basket research; previously seen years are development only."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from research_v1 import ROOT,sha
from kite_repair import atomic_write,encoded

DATA=ROOT/'data/five_day_v5'
OUT=ROOT/'experiments/five_day_v5'
MODELS=ROOT/'models/five_day_v5'
FEATURES=['ret1','ret5','ret20','ret60','vol20','volume_ratio','index20','relative20']


def features(frame,index_close):
    c=frame.close
    f=pd.DataFrame(index=frame.index)
    for n in [1,5,20,60]:f[f'ret{n}']=c/c.shift(n)-1
    f['vol20']=np.log(c/c.shift(1)).rolling(20).std(ddof=0)
    f['volume_ratio']=frame.volume.rolling(5).mean()/frame.volume.rolling(20).mean()
    f['index20']=index_close/index_close.shift(20)-1
    f['relative20']=f.ret20-f.index20
    return f


def build():
    config=json.loads((ROOT/'config/five_day_v5.json').read_text())
    inventory=pd.read_csv(ROOT/'experiments/five_year_v4/canonical_inventory.csv')
    inventory=inventory.loc[inventory.interval=='day']
    def load(symbol,kind):
        batches=[]
        for r in inventory.loc[(inventory.symbol==symbol)&(inventory.kind==kind)].to_dict('records'):
            if sha(ROOT/r['path'])!=r['sha256']:raise ValueError('Source checksum mismatch')
            f=pd.read_csv(ROOT/r['path']);f['day']=f.date.str[:10];batches.append(f)
        f=pd.concat(batches).sort_values('day').set_index('day')
        if f.index.duplicated().any():raise ValueError('Duplicate session')
        return f
    benchmark=load('NIFTY 50','index');calendar=benchmark.index
    actions=json.loads((ROOT/'data/five_year_processing_v4/references/study_actions.json').read_text())
    exdates={}
    for r in actions:exdates.setdefault(r['symbol'],set()).add(pd.to_datetime(r['exDate'],format='%d-%b-%Y').strftime('%Y-%m-%d'))
    symbols=sorted(set(inventory.loc[inventory.kind=='stock','symbol'])-{'TATAMOTORS'})
    rows=[];omissions=[]
    for symbol in symbols:
        f=load(symbol,'stock').reindex(calendar);feat=features(f,benchmark.close)
        for t in range(60,len(calendar)-6,5):
            start,end=t+1,t+6
            window=f.iloc[t-60:end+1]
            if not np.isfinite(feat.iloc[t].to_numpy()).all() or window[['open','high','low','close','volume']].isna().any().any() or (window.volume<=0).any():
                omissions.append(dict(symbol=symbol,day=calendar[t],reason='missing_or_invalid_window'));continue
            if any(calendar[t-60]<=d<=calendar[end] for d in exdates.get(symbol,set())):
                omissions.append(dict(symbol=symbol,day=calendar[t],reason='retrospective_action_window'));continue
            rows.append(dict(symbol=symbol,day=calendar[t],entry_day=calendar[start],exit_day=calendar[end],entry_open=float(f.open.iloc[start]),exit_open=float(f.open.iloc[end]),future_return=float(f.open.iloc[end]/f.open.iloc[start]-1),benchmark_return=float(benchmark.open.iloc[end]/benchmark.open.iloc[start]-1),**feat.iloc[t].to_dict()))
    data=pd.DataFrame(rows)
    data=data.loc[data.groupby('day').symbol.transform('size')>=10].copy()
    data['split']=np.select([(data.day<'2024-01-01')&(data.exit_day<'2024-01-01'),(data.day.str[:4]=='2024')&(data.exit_day<'2025-01-01'),(data.day.str[:4]=='2025')&(data.exit_day<'2026-01-01')],['train','validation','development'],default='purged')
    DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    data.to_csv(DATA/'samples.csv',index=False)
    pd.DataFrame(omissions).to_csv(DATA/'omissions.csv',index=False)
    inventory.to_csv(DATA/'source_manifest.csv',index=False)
    atomic_write(OUT/'dataset.json',encoded({'rows':len(data),'split_rows':data.split.value_counts().to_dict(),'split_batches':data.groupby('split').day.nunique().to_dict(),'samples_sha256':sha(DATA/'samples.csv'),'config_sha256':sha(ROOT/'config/five_day_v5.json'),'retrospective_action_window_exclusions':sum(r['reason']=='retrospective_action_window' for r in omissions)}))
    return pd.read_csv(DATA/'samples.csv')


def evaluate(frame,score,cost,top=5):
    trades=[];batches=[]
    for day,g in frame.groupby('day',sort=True):
        selected=g if score=='equal_weight' else g.sort_values([score,'symbol'],ascending=[False,True]).head(top)
        net=selected.future_return-cost/10000
        batches.append(dict(day=day,exit_day=selected.exit_day.iloc[0],net_return=float(net.mean()),benchmark_return=float(g.benchmark_return.iloc[0])))
        for r,n in zip(selected.to_dict('records'),net):trades.append(dict(symbol=r['symbol'],day=day,exit_day=r['exit_day'],gross_return=r['future_return'],net_return=float(n)))
    b=pd.DataFrame(batches);t=pd.DataFrame(trades)
    equity=np.r_[1,np.cumprod(1+b.net_return.to_numpy())]
    result={'batches':len(b),'trades':len(t),'profitable_trades':int((t.net_return>0).sum()),'net_basket_return':float(equity[-1]-1),'batch_close_max_drawdown':float((equity/np.maximum.accumulate(equity)-1).min()),'mean_trade_net_bps':float(t.net_return.mean()*10000),'benchmark_price_return_same_windows':float(np.prod(1+b.benchmark_return)-1)}
    return result,b,t


def main():
    if (OUT/'results.json').exists():raise ValueError('Preserve completed experiment; use a new branch/version.')
    config=json.loads((ROOT/'config/five_day_v5.json').read_text());data=build()
    train=data.loc[data.split=='train'];MODELS.mkdir(parents=True,exist_ok=True)
    models={'ridge':make_pipeline(StandardScaler(),Ridge(alpha=100)), 'tree':HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=15,learning_rate=.05,l2_regularization=10,min_samples_leaf=100,early_stopping=False,random_state=31)}
    data['momentum20']=data.ret20;data['reversal5']=-data.ret5
    for name,model in models.items():
        model.fit(train[FEATURES],train.future_return);joblib.dump(model,MODELS/f'{name}.joblib',compress=3)
        data[name]=model.predict(data[FEATURES]);restored=joblib.load(MODELS/f'{name}.joblib')
        if not np.array_equal(data[name].to_numpy()[:32],restored.predict(data[FEATURES].iloc[:32])):raise ValueError('Reload mismatch')
    results={}
    for split in ['validation','development']:
        frame=data.loc[data.split==split]
        results[split]={}
        for name in config['candidates']:
            results[split][name]={}
            for cost in config['cost_bps']:
                stats,b,t=evaluate(frame,name,cost)
                results[split][name][str(cost)]=stats
                if cost==50:
                    b.to_csv(OUT/f'{name}_{split}_batches.csv',index=False);t.to_csv(DATA/f'{name}_{split}_trades.csv',index=False)
        if split=='validation':
            baseline=results[split]['equal_weight']['50']['net_basket_return']
            eligible=[n for n in config['candidates'] if n!='equal_weight' and results[split][n]['50']['net_basket_return']>max(0,baseline)]
            chosen=max(eligible,key=lambda n:results[split][n]['50']['net_basket_return']) if eligible else None
            atomic_write(OUT/'locked_selection.json',encoded({'selected':chosen}))
    data.to_csv(DATA/'samples_with_scores.csv',index=False)
    atomic_write(OUT/'results.json',encoded({'selected_on_2024':chosen,'results':results,'config':config,'model_hashes':{n:sha(MODELS/f'{n}.joblib') for n in models},'interpretation':'Exploratory fractional baskets on previously observed years, retrospective action screening; no deployment or profitability proof.'}))
    print(json.dumps({'selected':chosen,'results':results},indent=2))


if __name__=='__main__':main()
