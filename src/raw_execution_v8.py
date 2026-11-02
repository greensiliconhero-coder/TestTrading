"""Frozen v5 selections replayed on raw NSE prices with net position changes."""
import json
import numpy as np
import pandas as pd
from ledger_v7 import Ledger
from delivery_v6 import fees,simulate as gross_replay
from benchmark_v6 import etf_fee
from nse_raw_v8 import ROOT,DATA,OUT
from research_v1 import sha
from kite_repair import atomic_write,encoded


def replay(frame,name,raw,calendar,actions,c,lag,slip):
    first,last=frame.entry_day.min(),frame.exit_day.max()
    schedule={day:g for day,g in frame.groupby('entry_day')};exits=set(frame.exit_day)
    clock={day:i for i,day in enumerate(calendar)}
    account=Ledger(c['initial_capital'],c,settlement_lag=lag,slippage_bps=slip,fee_calculator=etf_fee if name=='NIFTYBEES' else fees)
    for day in calendar:
        if not first<=day<=last:continue
        prices=raw.loc[raw.day==day].set_index('symbol').open.to_dict()
        held=set(account.positions)
        if any((s,day) in actions for s in held):raise ValueError('Held stock reaches an unresolved action: '+day)
        targets=None;signal=None
        if name=='NIFTYBEES':
            if day==first:targets={'NIFTYBEES':int(c['initial_capital']/(prices['NIFTYBEES']*(1+slip/10000)))};signal=clock[day]-1
            elif day==last:targets={};signal=clock[day]-1
        elif day in schedule:
            g=schedule[day];chosen=g.sort_values('symbol') if name=='equal_weight' else g.sort_values([name,'symbol'],ascending=[False,True]).head(5)
            equity=account.equity(prices);budget=equity/len(chosen)
            if name!='equal_weight':budget=min(budget,c['position_cap'])
            targets={s:int(budget/(prices[s]*(1+slip/10000))) for s in chosen.symbol}
            signal=clock[g.day.iloc[0]]
        elif day in exits:targets={};signal=clock[day]-1
        account.step(clock[day],prices,targets,signal)
        account.history[-1]['day']=day
    h=pd.DataFrame(account.history);t=pd.DataFrame(account.trades)
    if account.positions:raise ValueError('Final exit did not liquidate positions')
    values=np.r_[c['initial_capital'],h.equity.to_numpy()]
    stats={'net_return':float(values[-1]/c['initial_capital']-1),'final_equity':float(values[-1]),'settled_cash':account.cash,'unsettled_sale_receivables':sum(r['amount'] for r in account.receivables),'orders':len(t),'buy_orders':int((t.side=='buy').sum()) if len(t) else 0,'sell_orders':int((t.side=='sell').sum()) if len(t) else 0,'total_fees':float(t.fees.sum()) if len(t) else 0,'daily_open_max_drawdown':float((values/np.maximum.accumulate(values)-1).min()),'settlement_lag_sessions':lag,'slippage_bps_per_side':slip,'first_entry':first,'last_exit':last}
    return stats,h,t


def main():
    report=OUT/'raw_execution_results.json'
    if report.exists():raise ValueError('Preserve completed replay')
    summary=json.loads((OUT/'acquisition_summary.json').read_text());path=DATA/'raw_price_panel.csv.gz'
    if sha(path)!=summary['panel_sha256']:raise ValueError('Raw panel changed')
    raw=pd.read_csv(path);calendar=json.loads((OUT/'plan.json').read_text())['days']
    source=ROOT/'data/five_day_v5/samples_with_scores.csv';f=pd.read_csv(source)
    c=json.loads((ROOT/'config/delivery_v6.json').read_text())
    events=json.loads((ROOT/'data/five_year_processing_v4/references/study_actions.json').read_text())
    actions={(a['symbol'],pd.to_datetime(a['exDate'],format='%d-%b-%Y').strftime('%Y-%m-%d')) for a in events}
    # Paired control: change only execution price units in the old gross-leg replay.
    adjusted=f.copy()
    entry=raw[['symbol','day','open']].rename(columns={'day':'entry_day','open':'raw_entry_open'})
    exit_=raw[['symbol','day','open']].rename(columns={'day':'exit_day','open':'raw_exit_open'})
    adjusted=adjusted.merge(entry,on=['symbol','entry_day'],how='left',validate='many_to_one').merge(exit_,on=['symbol','exit_day'],how='left',validate='many_to_one')
    if adjusted[['raw_entry_open','raw_exit_open']].isna().any().any():raise ValueError('Missing raw sample execution endpoints; no silent dropping.')
    adjusted['raw_future_return']=adjusted.raw_exit_open/adjusted.raw_entry_open-1
    adjusted['return_difference_bps']=(adjusted.raw_future_return-adjusted.future_return)*10000
    adjusted.to_csv(DATA/'paired_sample_comparison.csv.gz',index=False)
    adjusted['entry_open']=adjusted.raw_entry_open;adjusted['exit_open']=adjusted.raw_exit_open
    gross_results={}
    for split in ['validation','development']:
        gross_results[split]={}
        for name in ['equal_weight','momentum20','reversal5','ridge','tree']:
            stats,_,_=gross_replay(adjusted.loc[adjusted.split==split],name,c,5)
            gross_results[split][name]=stats
    atomic_write(OUT/'raw_gross_control.json',encoded({'results':gross_results,'sample_count':len(adjusted),'max_abs_return_difference_bps':float(adjusted.return_difference_bps.abs().max()),'samples_over_5bps_return_difference':int((adjusted.return_difference_bps.abs()>5).sum()),'meaning':'Same v6 gross-roundtrip logic and frozen scores; only entry/exit price units changed to NSE raw.'}))
    results={}
    for split in ['validation','development']:
        results[split]={};frame=f.loc[f.split==split]
        for name in ['equal_weight','momentum20','reversal5','ridge','tree','NIFTYBEES']:
            results[split][name]={}
            for lag in [1,0]:
                for slip in [5,10]:
                    key=f'lag{lag}_slip{slip}';stats,h,t=replay(frame,name,raw,calendar,actions,c,lag,slip);results[split][name][key]=stats
                    dest=DATA/'replay';dest.mkdir(exist_ok=True)
                    h.to_csv(dest/f'{name}_{split}_{key}_account.csv',index=False);t.to_csv(dest/f'{name}_{split}_{key}_orders.csv',index=False)
            print(split,name,results[split][name]['lag1_slip5']['net_return'],flush=True)
    atomic_write(report,encoded({'results':results,'model_refit':False,'original_selection':'cash','frozen_scores_sha256':sha(source),'raw_panel_sha256':sha(path),'limits':['Original hindsight corporate-action exclusions and survivor cohort retained; no new strategy selection.','One-session versus zero-session sale-proceeds delay are sensitivity assumptions, not certified historical rules.','Current fee rates applied counterfactually.','Quantity sizing at observed open is an execution approximation; no bid/ask or auction fill proof.','Cash-constrained orders are reduced without automatic later retry.','Dividend/structural-action inputs are unresolved: replay aborts if any held asset reaches a listed action.','Pending sale proceeds contribute to final equity but are not spendable cash.','NIFTYBEES market-price buy-and-hold proxy; distributions not independently certified.','No new market profitability claim; 2025 remains development data.']}))


if __name__=='__main__':main()
