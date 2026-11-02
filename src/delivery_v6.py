"""Itemized fee sensitivity on frozen v5 scores; action-source audit."""
import json
import re
from collections import Counter
import pandas as pd
from research_v1 import ROOT,sha
from kite_repair import atomic_write,encoded

OUT=ROOT/'experiments/delivery_v6'
DATA=ROOT/'data/delivery_v6'


def fees(notional,side,c):
    if notional<=0:return 0.
    turnover=notional*(c['exchange_fraction']+c['sebi_fraction'])
    return notional*c['stt_fraction_buy_sell']+turnover*(1+c['gst_fraction'])+(notional*c['stamp_fraction_buy'] if side=='buy' else c['dp_per_symbol_sell'])


def simulate(frame,name,c,slip):
    cash=float(c['initial_capital']);trades=[];batches=[]
    for day,g in frame.groupby('day',sort=True):
        selected=g.sort_values('symbol') if name=='equal_weight' else g.sort_values([name,'symbol'],ascending=[False,True]).head(5)
        allocation=cash/len(selected)
        if name!='equal_weight':allocation=min(allocation,c['position_cap'])
        positions=[];start=cash
        for r in selected.itertuples():
            price=r.entry_open*(1+slip/10000);budget=min(allocation,cash)
            qty=int(budget/price)
            while qty>0 and qty*price+fees(qty*price,'buy',c)>budget:qty-=1
            if qty==0:continue
            buy=qty*price;buy_fee=fees(buy,'buy',c);cash-=buy+buy_fee
            if cash < -1e-8:raise ValueError('Borrowed cash')
            positions.append((r,qty,buy,buy_fee))
        for r,qty,buy,buy_fee in positions:
            sell=qty*r.exit_open*(1-slip/10000);sell_fee=fees(sell,'sell',c);cash+=sell-sell_fee
            trades.append({'symbol':r.symbol,'day':day,'entry_day':r.entry_day,'exit_day':r.exit_day,'quantity':qty,'buy':buy,'sell':sell,'fees':buy_fee+sell_fee,'dp_fee':c['dp_per_symbol_sell'],'net_pnl':sell-buy-buy_fee-sell_fee,'quote_pnl':qty*(r.exit_open-r.entry_open),'slippage':qty*(r.entry_open+r.exit_open)*slip/10000})
        batches.append({'day':day,'start_cash':start,'end_cash':cash,'positions':len(positions)})
    t=pd.DataFrame(trades);b=pd.DataFrame(batches)
    totalfees=float(t.fees.sum()) if len(t) else 0
    pnl=float(t.net_pnl.sum()) if len(t) else 0
    if abs(cash-c['initial_capital']-pnl)>1e-6:raise ValueError('Ledger does not reconcile')
    return {'net_return':cash/c['initial_capital']-1,'final_cash':cash,'trades':len(t),'profitable_trades':int((t.net_pnl>0).sum()) if len(t) else 0,'total_fees':totalfees,'dp_fees':float(t.dp_fee.sum()) if len(t) else 0,'slippage':float(t.slippage.sum()) if len(t) else 0,'mean_position_notional':float(t.buy.mean()) if len(t) else 0},b,t


def audit_actions():
    source=ROOT/'data/five_year_processing_v4/references/study_actions.json'
    actions=json.loads(source.read_text());review=[]
    for r in actions:
        subject=r['subject'].lower()
        kind=next((k for k,token in [('dividend','dividend'),('split','split'),('bonus','bonus'),('rights','rights'),('demerger','demerger'),('buyback','buy'),('meeting','meeting')] if token in subject),'unclassified')
        amounts=re.findall(r'(?:rs\.?|re\.?)\s*([\d,]+(?:\.\d+)?)',subject)
        review.append(dict(symbol=r['symbol'],ex_date=r['exDate'],subject=r['subject'],kind=kind,publication_timestamp=r.get('caBroadcastDate'),amount_candidates=amounts,automatic_adjustment_applied=False))
    atomic_write(DATA/'action_review.json',encoded(review))
    result={'records':len(review),'types':dict(Counter(r['kind'] for r in review)),'missing_publication_timestamp':sum(not r['publication_timestamp'] for r in review),'source_sha256':sha(source),'structural_action_symbols':sorted({r['symbol'] for r in review if r['kind'] in ['split','bonus','rights','demerger']}),'adjustment_status':'Unresolved: ledger lacks verified price adjustment factors, full announcement timing and dividend payment dates. No automatic total-return or historical share-unit reconstruction performed.'}
    atomic_write(OUT/'action_audit.json',encoded(result));return result


def main():
    OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True)
    if (OUT/'results.json').exists():raise ValueError('Preserve completed replay')
    c=json.loads((ROOT/'config/delivery_v6.json').read_text());f=pd.read_csv(ROOT/'data/five_day_v5/samples_with_scores.csv')
    f.to_csv(DATA/'frozen_v5_samples_with_scores.csv',index=False)
    action=audit_actions();results={}
    for split in ['validation','development']:
        results[split]={}
        for name in ['equal_weight','momentum20','reversal5','ridge','tree']:
            results[split][name]={}
            for slip in [5,10]:
                stats,b,t=simulate(f.loc[f.split==split],name,c,slip);results[split][name][str(slip)]=stats
                b.to_csv(OUT/f'{name}_{split}_{slip}_batches.csv',index=False);t.to_csv(DATA/f'{name}_{split}_{slip}_trades.csv',index=False)
    source=ROOT/'data/five_day_v5/samples_with_scores.csv'
    atomic_write(OUT/'results.json',encoded({'config':c,'frozen_scores_sha256':sha(source),'results':results,'action_audit':action,'selection':'Original v5 cash decision preserved; no refit or re-selection.','benchmark_status':'ETF data acquisition pending validation'}))
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
