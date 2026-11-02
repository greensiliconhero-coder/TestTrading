"""Resolve coverage questions into evidence queues, without changing membership."""
import io,json,zipfile
from collections import Counter
import pandas as pd
from causal_universe_v10 import ROOT,DATA,OUT
from research_v1 import sha
from kite_repair import atomic_write,encoded

def main():
    windows=pd.read_csv(DATA/'window_audit.csv');prices=pd.read_csv(DATA/'all_eq_ine_prices.csv.gz',usecols=['isin','day'])
    present=set(zip(prices['isin'],prices.day));cache={};review=[]
    for r in windows.loc[~windows.endpoints_present].to_dict('records'):
        if pd.isna(r['exit_day']):
            review.append({'symbol':r['symbol'],'signal_day':r['day'],'status':'right_censored_dataset_end'});continue
        for side in ['entry_day','exit_day']:
            day=r[side]
            if (r['isin'],day) in present:continue
            path=ROOT/'data/nse_raw_v8/raw'/f'{day}.zip'
            if day not in cache:
                with zipfile.ZipFile(path) as z:
                    f=pd.read_csv(io.BytesIO(z.read(z.namelist()[0])),dtype=str)
                fields={'SYMBOL':'symbol','SERIES':'series','ISIN':'isin','OPEN':'open','CLOSE':'close'} if 'SYMBOL' in f else {'TckrSymb':'symbol','SctySrs':'series','ISIN':'isin','OpnPric':'open','ClsPric':'close'}
                cache[day]=f[list(fields)].rename(columns=fields)
            f=cache[day];same=f.loc[f['isin']==r['isin']];symbol=f.loc[f.symbol==r['symbol']]
            status='same_isin_other_series' if len(same) else 'same_symbol_different_isin' if len(symbol) else 'no_same_isin_or_symbol'
            review.append({'symbol':r['symbol'],'isin':r['isin'],'signal_day':r['day'],'endpoint':side,'day':day,'status':status,'same_isin_quotes':same.to_dict('records'),'same_symbol_quotes':symbol.to_dict('records'),'source_path':str(path.relative_to(ROOT)),'source_sha256':sha(path),'auto_repaired':False})
    atomic_write(OUT/'endpoint_review.json',encoded(review))
    obligations=json.loads((OUT/'action_obligations.json').read_text());queue=[]
    for r in obligations:
        s=r['subject'].lower()
        kind=next((k for k in ['dividend','bonus','split','demerger','rights'] if k in s),'meeting' if 'general meeting' in s else 'buyback' if 'buyback' in s or 'buy back' in s else 'other')
        required={'dividend':['verified amount and entitlement','actual payment date'], 'bonus':['verified factor','record date','announcement date','actual tradability date','fractional entitlement policy'], 'split':['verified factor','ISIN mapping and effective tradability'], 'demerger':['successor identities','allocation ratio','listing/tradability dates','valuation before listing'], 'rights':['rights entitlement and trading dates','explicit participation or sale policy'], 'meeting':['classify as no automatic cash/share adjustment'], 'buyback':['document nonparticipation policy; verify no compulsory conversion']}.get(kind,['manual review'])
        queue.append({**r,'kind':kind,'required_evidence':required})
    atomic_write(OUT/'prioritized_action_queue.json',encoded(queue))
    summary={'endpoint_status_counts':dict(Counter(r['status'] for r in review)),'action_type_counts':dict(Counter(r['kind'] for r in queue)),'note':'Counts are audit records, not silently dropped candidates; endpoint counts can exceed window counts. Meetings/buybacks are not automatically cashflow events. All uncertain mappings remain unapproved.'}
    atomic_write(OUT/'obligation_summary.json',encoded(summary));print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
