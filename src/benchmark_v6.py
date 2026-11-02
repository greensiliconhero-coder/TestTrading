"""Passive NIFTYBEES market-price benchmark, with explicit distribution caveat."""
import json
import pandas as pd
from delivery_v6 import ROOT,OUT,DATA,fees
from research_v1 import sha
from kite_repair import atomic_write,encoded
from five_year_download import validate_response


def etf_fee(value,side,c):
    # Equity ETF delivery: no STT on purchase, 0.001% on sale.
    stock_stt=value*c['stt_fraction_buy_sell']
    return fees(value,side,c)-stock_stt+(value*.00001 if side=='sell' else 0)


def main():
    config=json.loads((ROOT/'config/delivery_v6.json').read_text())
    records=json.loads((DATA/'benchmark/manifest.json').read_text());rows=[]
    if len(records)!=6:raise ValueError('Benchmark download incomplete')
    for r in records:
        p=ROOT/r['path']
        if sha(p)!=r['sha256']:raise ValueError('Benchmark checksum mismatch')
        body=p.read_bytes();validate_response(body,r);rows.extend(json.loads(body)['data']['candles'])
    f=pd.DataFrame(rows,columns=['date','open','high','low','close','volume']);f['day']=f.date.str[:10]
    if f.day.duplicated().any():raise ValueError('Duplicate benchmark date')
    f=f.sort_values('day').set_index('day')
    f.to_csv(DATA/'benchmark/daily.csv')
    samples=pd.read_csv(DATA/'frozen_v5_samples_with_scores.csv');results={}
    for split in ['validation','development']:
        part=samples.loc[samples.split==split];entry=part.entry_day.min();exit_=part.exit_day.max()
        if entry not in f.index or exit_ not in f.index:raise ValueError('Missing benchmark endpoint')
        results[split]={}
        for slip in [5,10]:
            buyprice=float(f.loc[entry,'open'])*(1+slip/10000);sellprice=float(f.loc[exit_,'open'])*(1-slip/10000)
            cash=config['initial_capital'];quantity=int(cash/buyprice)
            while quantity*buyprice+etf_fee(quantity*buyprice,'buy',config)>cash:quantity-=1
            buy=quantity*buyprice;sell=quantity*sellprice;cost=etf_fee(buy,'buy',config)+etf_fee(sell,'sell',config)
            final=cash-buy+sell-cost
            results[split][str(slip)]={'entry_day':entry,'exit_day':exit_,'quantity':quantity,'final_cash':final,'net_return':final/cash-1,'fees':cost,'price_return':float(f.loc[exit_,'open']/f.loc[entry,'open']-1),'slippage_bps_per_side':slip}
    source_manifest=json.loads((ROOT/'experiments/five_year_v4/actions_manifest.json').read_text());actions=[]
    for r in source_manifest:
        p=ROOT/r['path']
        if sha(p)!=r['sha256']:raise ValueError('Action raw source changed')
        actions.extend(v for v in json.loads(p.read_bytes()) if v['symbol']=='NIFTYBEES')
    atomic_write(OUT/'benchmark_results.json',encoded({'symbol':'NIFTYBEES','daily_rows':len(f),'results':results,'equities_action_ledger_matches':actions,'limitations':'ETF market-price buy-and-hold proxy. Equities action ledger may not exhaust ETF distributions; not independently certified total return. Current fees applied counterfactually, cash earnings and personal income taxes excluded. Buy at first active entry date, sell at last active exit date; holds through intervening inactive periods.','etf_stt_source':'https://support.zerodha.com/category/account-opening/resident-individual/ri-charges/articles/stt-etfs'}))
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
