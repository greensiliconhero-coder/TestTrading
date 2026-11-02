"""Outcome-blind daily-index comparison and corporate-action evidence."""
import json
from datetime import datetime
import pandas as pd
from five_year_prepare import ROOT, DEST, REPORT
from research_v1 import sha
from kite_repair import atomic_write, encoded


def main():
    config=json.loads((ROOT/'config/five_year_v4.json').read_text())
    actions=[]
    for rec in json.loads((REPORT/'actions_manifest.json').read_text()):
        if rec['status']!='staged_unverified' or sha(ROOT/rec['path'])!=rec['sha256']:raise ValueError('Action source unavailable or changed.')
        actions.extend(json.loads((ROOT/rec['path']).read_bytes()))
    symbols=set(config['stocks'])|{'TMPV'}
    selected=[r for r in actions if r['symbol'] in symbols]
    atomic_write(DEST/'references/study_actions.json',encoded(selected))
    official={}
    for rec in json.loads((REPORT/'official_daily_manifest.json').read_text()):
        if rec['status']!='downloaded' or sha(ROOT/rec['path'])!=rec['sha256']:raise ValueError('Official daily unavailable or changed.')
        for r in json.loads((ROOT/rec['path']).read_bytes()):
            official[(rec['symbol'],datetime.strptime(r['HistoricalDate'],'%d %b %Y').strftime('%Y-%m-%d'))]=r
    comparisons=[];missing=[]
    for symbol in config['indices']:
        for path in sorted((DEST/'canonical/index/minute').glob(symbol.replace(' ','_')+'_*.csv.gz')):
            f=pd.read_csv(path);f['day']=f.date.str[:10];f=f.loc[f.date.str[11:16].between('09:15','15:29')]
            for day,g in f.groupby('day'):
                r=official.get((symbol,day))
                if r is None:missing.append({'symbol':symbol,'day':day});continue
                comparisons.append(dict(symbol=symbol,day=day,high_difference_bps=(g.high.max()/float(r['HIGH'])-1)*10000,low_difference_bps=(g.low.min()/float(r['LOW'])-1)*10000))
    frame=pd.DataFrame(comparisons)
    frame.to_csv(REPORT/'independent_daily_comparison.csv',index=False)
    dates=sorted(frame.loc[frame[['high_difference_bps','low_difference_bps']].abs().max(axis=1)>10,'day'].unique())
    dates=sorted(set(dates)|{r['day'] for r in missing})
    report={'quarantined_dates':dates,'missing_official_matches':missing,'corporate_action_records':len(selected),'threshold_bps':10,'comparison_rows':len(frame),'retrospective_quality_screen':True,'excluded_symbols':{'TATAMOTORS':'2025 demerger changes economic continuity; preserve raw series but exclude all years from comparable model cohort pending adjustment review.'},'limitations':'Excluding entire dates on daily disagreement is retrospective and may remove volatile days. Not a deployable live-data filter; report this bias.'}
    atomic_write(REPORT/'quality_policy.json',encoded(report))
    print('Quality dates:',len(dates),'actions:',len(selected),flush=True)


if __name__=='__main__':main()
