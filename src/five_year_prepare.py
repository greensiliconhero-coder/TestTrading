"""Preserve a verified raw snapshot and audit sessions before model preparation."""
import json
import shutil
from collections import Counter
from pathlib import Path
import pandas as pd
from five_year_download import ROOT, validate_response, jobs
from kite_repair import atomic_write, encoded
from research_v1 import sha

DEST = ROOT/'data/five_year_processing_v4'
REPORT = ROOT/'experiments/five_year_v4'


def main():
    config = json.loads((ROOT/'config/five_year_v4.json').read_text())
    manifest_path = REPORT/'download_manifest.json'
    manifest = json.loads(manifest_path.read_text())['requests']
    expected = {(j['kind'],j['symbol'],j['interval'],j['from'],j['to']) for j in jobs(config)}
    actual = {(j['kind'],j['symbol'],j['interval'],j['from'],j['to']) for j in manifest.values()}
    if actual != expected or any(r['status']!='staged_unverified' for r in manifest.values()):
        raise ValueError('Acquisition incomplete; do not prepare a partial training snapshot.')
    DEST.mkdir(parents=True,exist_ok=True)
    copied = []
    for i,(name,rec) in enumerate(manifest.items(),1):
        source = ROOT/rec['path']
        if sha(source)!=rec['sha256']:
            raise ValueError('Raw file checksum mismatch: '+name)
        target = DEST/'raw'/Path(rec['path']).relative_to('data/five_year_v4/raw')
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            shutil.copyfile(source,target)
        if sha(target)!=rec['sha256']:
            raise ValueError('Snapshot differs: '+name)
        copied.append(dict(rec,copy=target.relative_to(ROOT).as_posix()))
        if i%200==0:print(f'Copied and hash verified {i}/{len(manifest)}',flush=True)
    atomic_write(DEST/'source_manifest.json',encoded(copied))
    atomic_write(DEST/'download_manifest.json',manifest_path.read_bytes())
    atomic_write(DEST/'config.json',(ROOT/'config/five_year_v4.json').read_bytes())
    for source in (ROOT/'data/five_year_v4/instruments').glob('*.csv'):
        target=DEST/'instruments'/source.name
        atomic_write(target,source.read_bytes())
    sessions=[]; summary=[]; comparisons=[]
    for kind,symbol in sorted({(r['kind'],r['symbol']) for r in copied}):
        frames={}
        for interval in ['minute','day']:
            batches=[]
            for rec in copied:
                if (rec['kind'],rec['symbol'],rec['interval'])!=(kind,symbol,interval):continue
                body=(ROOT/rec['copy']).read_bytes()
                validate_response(body,rec)
                batches.extend(json.loads(body)['data']['candles'])
            frame=pd.DataFrame(batches,columns=['date','open','high','low','close','volume'])
            stamp=pd.to_datetime(frame.date,utc=True).dt.tz_convert('Asia/Kolkata')
            if stamp.duplicated().any():raise ValueError('Cross-chunk duplicate: '+symbol)
            frame['day']=stamp.dt.strftime('%Y-%m-%d');frame['minute']=stamp.dt.hour*60+stamp.dt.minute
            frame=frame.sort_values('date');frames[interval]=frame
            for year,part in frame.groupby(frame.day.str[:4]):
                path=DEST/'canonical'/kind/interval/f'{symbol.replace(" ","_")}_{year}.csv.gz'
                path.parent.mkdir(parents=True,exist_ok=True)
                part[['date','open','high','low','close','volume']].to_csv(path,index=False,compression={'method':'gzip','mtime':0,'compresslevel':1})
                summary.append(dict(kind=kind,symbol=symbol,interval=interval,year=year,rows=len(part),days=part.day.nunique(),path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
        regular=frames['minute'].loc[frames['minute'].minute.between(555,929)]
        daily=frames['day'].set_index('day')
        for day,g in regular.groupby('day'):
            complete=len(g)==375 and g.minute.tolist()==list(range(555,930))
            sessions.append(dict(kind=kind,symbol=symbol,day=day,rows=len(g),complete=complete,zero_volume_rows=int((g.volume==0).sum())))
            if day in daily.index:
                d=daily.loc[day]
                comparisons.append(dict(kind=kind,symbol=symbol,day=day,high_difference_bps=(g.high.max()/d.high-1)*10000,low_difference_bps=(g.low.min()/d.low-1)*10000))
        print('Audited',kind,symbol,flush=True)
    pd.DataFrame(summary).to_csv(REPORT/'canonical_inventory.csv',index=False)
    pd.DataFrame(sessions).to_csv(REPORT/'session_audit.csv',index=False)
    pd.DataFrame(comparisons).to_csv(REPORT/'same_provider_daily_comparison.csv',index=False)
    report={'raw_files':len(copied),'raw_bytes':sum(r['bytes'] for r in copied),'canonical_files':len(summary),'symbols':len(config['stocks']),'indices':len(config['indices']),'years':[2021,2022,2023,2024,2025],'complete_sessions':sum(r['complete'] for r in sessions),'incomplete_sessions':sum(not r['complete'] for r in sessions),'source_manifest_sha256':sha(DEST/'source_manifest.json'),'training_started':False,'limitations':'Structural and same-provider audit only. Corporate actions and independent index comparison pending. No return-based exclusions.'}
    atomic_write(REPORT/'snapshot_audit.json',encoded(report))
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
