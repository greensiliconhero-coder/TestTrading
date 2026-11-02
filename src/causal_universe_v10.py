"""Build decision-time liquidity candidates independently of future prices/actions."""
import io,json,zipfile
from collections import deque
from pathlib import Path
import numpy as np
import pandas as pd
from research_v1 import ROOT,sha
from kite_repair import atomic_write,encoded
from nse_reconcile_v8 import expected_share_ratio,dividend_amounts

DATA=ROOT/'data/causal_universe_v10'
OUT=ROOT/'experiments/causal_universe_v10'

def parse(body,day):
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(names)!=1:raise ValueError('Ambiguous archive')
        f=pd.read_csv(io.BytesIO(z.read(names[0])),dtype=str)
    legacy='SYMBOL' in f
    fields={'symbol':'SYMBOL','series':'SERIES','isin':'ISIN','day':'TIMESTAMP','open':'OPEN','high':'HIGH','low':'LOW','close':'CLOSE','volume':'TOTTRDQTY','traded_value':'TOTTRDVAL'} if legacy else {'symbol':'TckrSymb','series':'SctySrs','isin':'ISIN','day':'TradDt','open':'OpnPric','high':'HghPric','low':'LwPric','close':'ClsPric','volume':'TtlTradgVol','traded_value':'TtlTrfVal'}
    f=f[list(fields.values())].rename(columns={v:k for k,v in fields.items()})
    dates=pd.to_datetime(f.day,format='%d-%b-%Y' if legacy else '%Y-%m-%d').dt.strftime('%Y-%m-%d')
    if set(dates)!={day}:raise ValueError('Archive date mismatch')
    f=f.loc[f.series.str.strip().eq('EQ') & f['isin'].str.startswith('INE',na=False)].copy();f['day']=day
    if f['isin'].duplicated().any():raise ValueError('Ambiguous same-day ISIN; requires review')
    cols=['open','high','low','close','volume','traded_value']
    for c in cols:f[c]=pd.to_numeric(f[c],errors='coerce')
    valid=np.isfinite(f[cols]).all(axis=1)&(f[cols]>0).all(axis=1)&(f.high>=f[['open','close','low']].max(axis=1))&(f.low<=f[['open','close','high']].min(axis=1))
    # Reported rupee turnover must imply a volume-weighted price within the range.
    vwap=f.traded_value/f.volume
    valid &= (vwap>=f.low-.011)&(vwap<=f.high+.011)
    issues=f.loc[~valid,['symbol','isin','day']].copy();issues['reason']='invalid_or_zero_ohlcv_turnover'
    return f.loc[valid].copy(),issues

class Selector:
    def __init__(self):self.hist={};self.last={}
    def update(self,frame,step):
        eligible=[]
        for r in frame.to_dict('records'):
            identity=r['isin']
            if self.last.get(identity)!=step-1:self.hist[identity]=deque(maxlen=61)
            self.hist[identity].append(r['traded_value']);self.last[identity]=step
            if len(self.hist[identity])==61:
                eligible.append({'symbol':r['symbol'],'isin':identity,'day':r['day'],'mean_value20':float(np.mean(list(self.hist[identity])[-20:])),'available_sessions':61})
        return sorted(eligible,key=lambda r:(-r['mean_value20'],r['isin']))[:36]

def main():
    if (OUT/'summary.json').exists():raise ValueError('Preserve completed universe')
    DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    days=json.loads((ROOT/'experiments/nse_raw_v8/plan.json').read_text())['days']
    manifest=json.loads((ROOT/'experiments/nse_raw_v8/manifest.json').read_text())
    if isinstance(manifest,dict):manifest=list(manifest.values())
    records={r['day']:r for r in manifest};selector=Selector();selected=[];issues=[];panels=[]
    for step,day in enumerate(days):
        path=ROOT/'data/nse_raw_v8/raw'/f'{day}.zip'
        if sha(path)!=records[day]['sha256']:raise ValueError('Source changed: '+day)
        f,bad=parse(path.read_bytes(),day);panels.append(f);issues.append(bad)
        candidates=selector.update(f,step)
        if step>=60 and (step-60)%5==0:
            for rank,r in enumerate(candidates,1):r.update(rank=rank,signal_step=step);selected.append(r)
        if (step+1)%200==0:print('Parsed',step+1,'/',len(days),flush=True)
    panel=pd.concat(panels,ignore_index=True);candidates=pd.DataFrame(selected)
    panel.to_csv(DATA/'all_eq_ine_prices.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    candidates.to_csv(DATA/'candidates.csv',index=False);pd.concat(issues,ignore_index=True).to_csv(OUT/'row_issues.csv',index=False)
    # Future-dependent audit starts only AFTER decision-time membership is frozen.
    sources=json.loads((ROOT/'experiments/five_year_v4/actions_manifest.json').read_text());events=[]
    for rec in sources:
        path=ROOT/rec['path']
        if sha(path)!=rec['sha256']:raise ValueError('Action source changed')
        for j,a in enumerate(json.loads(path.read_text())):
            try:day=pd.to_datetime(a['exDate'],format='%d-%b-%Y').strftime('%Y-%m-%d')
            except (ValueError,KeyError,TypeError) as exc:raise ValueError('Unparseable action ex-date: '+rec['path']+' row '+str(j)) from exc
            subject=a.get('subject','');events.append({'symbol':a.get('symbol'),'isin':a.get('isin'),'ex_day':day,'subject':subject,'factor_candidate':expected_share_ratio(subject),'dividend_candidates':dividend_amounts(subject),'source_path':rec['path'],'source_row':j,'verified_for_execution':False})
    atomic_write(DATA/'all_market_action_candidates.json',encoded(events))
    by_symbol={};by_isin={}
    for e in events:
        by_symbol.setdefault(e['symbol'],[]).append(e)
        if e['isin']:by_isin.setdefault(e['isin'],[]).append(e)
    quotes=set(zip(panel['isin'],panel.day));obligations=[];windows=[]
    for r in selected:
        t=r['signal_step'];entry=days[t+1] if t+1<len(days) else None;exit_=days[t+6] if t+6<len(days) else None
        base={**r,'entry_day':entry,'exit_day':exit_,'endpoints_present':bool(entry and exit_ and (r['isin'],entry) in quotes and (r['isin'],exit_) in quotes)}
        hits=[]
        if entry and exit_:
            union={(e['source_path'],e['source_row']):e for e in by_symbol.get(r['symbol'],[])+by_isin.get(r['isin'],[])}
            hits=[e for e in union.values() if entry<e['ex_day']<=exit_]
        base['action_count']=len(hits);windows.append(base)
        for e in hits:obligations.append({**base,**e,'signal_day':r['day'],'candidate_symbol':r['symbol'],'candidate_isin':r['isin']})
    pd.DataFrame(windows).to_csv(DATA/'window_audit.csv',index=False)
    atomic_write(OUT/'action_obligations.json',encoded(obligations))
    old=pd.read_csv(ROOT/'data/five_day_v5/samples_with_scores.csv');w=pd.DataFrame(windows)
    summary={'price_rows':len(panel),'distinct_isins':int(panel['isin'].nunique()),'signal_dates':int(candidates.day.nunique()),'candidate_rows':len(candidates),'selected_isins':int(candidates['isin'].nunique()),'selected_symbols':int(candidates.symbol.nunique()),'candidates_outside_old_stock_list':int((~candidates.symbol.isin(old.symbol.unique())).sum()),'invalid_or_zero_rows':int(sum(len(x) for x in issues)),'windows_with_actions':int((w.action_count>0).sum()),'windows_without_both_endpoints':int((~w.endpoints_present).sum()),'action_obligation_rows':len(obligations),'candidate_sha256':sha(DATA/'candidates.csv'),'panel_sha256':sha(DATA/'all_eq_ine_prices.csv.gz'),'selection_uses_future_actions_or_prices':False,'trading_backtest_performed':False,'execution_gate':'Blocked pending verified relevant action entitlements, tradability/payment dates, identity transitions, historical fees/settlement and missing endpoints. Candidates are not deleted for these audit findings.'}
    atomic_write(OUT/'summary.json',encoded(summary));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()

