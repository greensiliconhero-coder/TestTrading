"""Compare raw NSE candles with the saved vendor snapshot, without fitting strategies."""
import json
import re
import pandas as pd
import numpy as np
from nse_raw_v8 import ROOT,DATA,OUT
from research_v1 import sha
from kite_repair import atomic_write,encoded


def expected_share_ratio(subject):
    bonus=re.search(r'bonus\s+(\d+)\s*:\s*(\d+)',subject,re.I)
    if bonus:return (int(bonus[1])+int(bonus[2]))/int(bonus[2])
    split=re.search(r'from\D*(\d+(?:\.\d+)?).*?to\D*(\d+(?:\.\d+)?)',subject,re.I)
    if 'split' in subject.lower() and split:return float(split[1])/float(split[2])
    return None


def main():
    acquisition=json.loads((OUT/'acquisition_summary.json').read_text())
    panel=DATA/'raw_price_panel.csv.gz'
    if sha(panel)!=acquisition['panel_sha256']:raise ValueError('Raw panel changed')
    raw=pd.read_csv(panel)
    if raw.duplicated(['symbol','day']).any():raise ValueError('Duplicate raw symbol/day')
    inventory=pd.read_csv(ROOT/'experiments/five_year_v4/canonical_inventory.csv')
    vendor=[]
    for rec in inventory.loc[(inventory.kind=='stock')&(inventory.interval=='day')].to_dict('records'):
        path=ROOT/rec['path']
        if sha(path)!=rec['sha256']:raise ValueError('Kite canonical changed')
        f=pd.read_csv(path);f['symbol']=rec['symbol'];f['day']=f.date.str[:10];vendor.append(f)
    k=pd.concat(vendor,ignore_index=True)
    k.loc[(k.symbol=='TATAMOTORS')&(k.day>='2025-10-24'),'symbol']='TMPV'
    comparison=raw.merge(k[['symbol','day','open','high','low','close','volume']],on=['symbol','day'],how='outer',suffixes=('_nse','_kite'),indicator=True,validate='one_to_one')
    comparison['close_factor']=comparison.close_nse/comparison.close_kite
    comparison['volume_factor']=comparison.volume_kite/comparison.volume_nse.replace(0,np.nan)
    comparison.to_csv(DATA/'vendor_comparison.csv.gz',index=False,compression={'method':'gzip','mtime':0,'compresslevel':1})
    actions=json.loads((ROOT/'data/five_year_processing_v4/references/study_actions.json').read_text());events=[];dividends=[]
    for a in actions:
        day=pd.to_datetime(a['exDate'],format='%d-%b-%Y').strftime('%Y-%m-%d');ratio=expected_share_ratio(a['subject'])
        if ratio:
            sub=comparison.loc[(comparison.symbol==a['symbol'])&(comparison['_merge']=='both')].sort_values('day')
            pre=sub.loc[sub.day<day].tail(1);post=sub.loc[sub.day==day]
            observed=None if pre.empty or post.empty else float(pre.close_factor.iloc[0]/post.close_factor.iloc[0])
            events.append({'symbol':a['symbol'],'ex_day':day,'subject':a['subject'],'expected_share_multiplier_from_exchange_ledger':ratio,'observed_adjustment_factor_change':observed,'within_0_2_percent':observed is not None and abs(observed/ratio-1)<=.002,'scope':'Diagnostic factor transition only, not full causal adjustment chain.'})
        if 'dividend' in a['subject'].lower():
            amounts=re.findall(r'(\d+(?:\.\d+)?)\s*(?:/-)?\s*per\s*share',a['subject'],re.I)
            dividends.append({'symbol':a['symbol'],'ex_day':day,'subject':a['subject'],'amount_candidates':[float(v) for v in amounts],'sum_candidate':sum(float(v) for v in amounts) if amounts else None,'payment_date':None,'publication_timestamp':a.get('caBroadcastDate'),'status':'parsed_candidate_requires_cashflow_verification'})
    atomic_write(OUT/'split_bonus_checks.json',encoded(events));atomic_write(DATA/'dividend_candidates.json',encoded(dividends))
    missing=comparison.loc[comparison['_merge']!='both',['symbol','day','_merge']]
    missing.to_csv(OUT/'coverage_differences.csv',index=False)
    matched=comparison.loc[comparison['_merge']=='both']
    summary={'raw_dates':raw.day.nunique(),'raw_rows':len(raw),'raw_symbols':raw.symbol.nunique(),'matched_vendor_rows':len(matched),'coverage_difference_rows':len(missing),'split_bonus_checks':len(events),'split_bonus_checks_within_tolerance':sum(r['within_0_2_percent'] for r in events),'dividend_candidates':len(dividends),'dividends_unparsed':sum(not d['amount_candidates'] for d in dividends),'raw_panel_sha256':sha(panel),'comparison_sha256':sha(DATA/'vendor_comparison.csv.gz'),'market_gate':'Raw prices acquired and checked; full corporate cashflows and historical fee/settlement assumptions still pending. Prior retrospective sample selection remains a limitation.'}
    atomic_write(OUT/'reconciliation_summary.json',encoded(summary));print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
