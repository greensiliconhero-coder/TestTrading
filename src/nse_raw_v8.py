"""Resumable official NSE bhavcopy collection with original traded-price units."""
import io
import json
import math
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from urllib import request,error
from pathlib import Path
import pandas as pd
from research_v1 import ROOT,sha
from kite_repair import atomic_write,encoded

DATA=ROOT/'data/nse_raw_v8'
OUT=ROOT/'experiments/nse_raw_v8'
LOCK=threading.Lock()
LAST=[0.]


def archive_url(day):
    d=datetime.strptime(day,'%Y-%m-%d')
    if day>='2024-07-08':return f'https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip'
    month=d.strftime('%b').upper()
    return f'https://nsearchives.nseindia.com/content/historical/EQUITIES/{d:%Y}/{month}/cm{d:%d}{month}{d:%Y}bhav.csv.zip'


def parse_archive(body,day,wanted):
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        files=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(files)!=1:raise ValueError('Ambiguous bhavcopy archive')
        if z.getinfo(files[0]).file_size>30_000_000:raise ValueError('Unexpected archive size')
        f=pd.read_csv(io.BytesIO(z.read(files[0])),dtype=str)
    legacy='SYMBOL' in f
    fields={'symbol':'SYMBOL','series':'SERIES','isin':'ISIN','date':'TIMESTAMP','open':'OPEN','high':'HIGH','low':'LOW','close':'CLOSE','volume':'TOTTRDQTY'} if legacy else {'symbol':'TckrSymb','series':'SctySrs','isin':'ISIN','date':'TradDt','open':'OpnPric','high':'HghPric','low':'LwPric','close':'ClsPric','volume':'TtlTradgVol'}
    if not set(fields.values()).issubset(f.columns):raise ValueError('Missing bhavcopy fields')
    dates=set(f[fields['date']].dropna())
    parsed={datetime.strptime(d,'%d-%b-%Y').strftime('%Y-%m-%d') if legacy else str(d)[:10] for d in dates}
    if parsed!={day}:raise ValueError('Internal exchange date does not match request')
    f=f.loc[f[fields['series']].str.strip().eq('EQ') & f[fields['symbol']].isin(wanted)]
    if f[fields['symbol']].duplicated().any():raise ValueError('Duplicate requested EQ symbol')
    rows=[];issues=[]
    for raw in f.to_dict('records'):
        row={k:raw[v] for k,v in fields.items()};row['day']=day;row.pop('date')
        try:
            for field in ['open','high','low','close','volume']:row[field]=float(row[field])
            if not all(math.isfinite(row[k]) for k in ['open','high','low','close','volume']):raise ValueError('Nonfinite')
            if min(row[k] for k in ['open','high','low','close'])<=0 or row['high']<max(row['open'],row['low'],row['close']) or row['low']>min(row['open'],row['high'],row['close']) or row['volume']<0:raise ValueError('Invalid OHLCV')
        except ValueError:
            issues.append({'symbol':row['symbol'],'day':day,'reason':'invalid_ohlcv'});continue
        rows.append(row)
    return rows,issues


def fetch(day,wanted,old):
    path=DATA/'raw'/f'{day}.zip';url=archive_url(day)
    record={'day':day,'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat()}
    if old.get('status')=='downloaded' and path.exists() and sha(path)==old.get('sha256'):
        body=path.read_bytes();record=old
    else:
        for attempt in range(3):
            try:
                with LOCK:
                    time.sleep(max(0,.5-(time.monotonic()-LAST[0])));LAST[0]=time.monotonic()
                with request.urlopen(request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as response:body=response.read(10_000_001)
                if len(body)>10_000_000:raise ValueError('Unexpected response size')
                atomic_write(path,body);break
            except error.HTTPError as exc:
                if exc.code in [403,429]:raise RuntimeError(f'Exchange access/rate limit HTTP {exc.code}; stop collection.') from None
                if exc.code in [500,502,503,504] and attempt<2:time.sleep(2**attempt);continue
                return dict(record,status='unavailable',http_status=exc.code),[],[]
            except (OSError,TimeoutError):
                if attempt<2:time.sleep(2**attempt);continue
                return dict(record,status='unavailable',error='network'),[],[]
    try:
        rows,issues=parse_archive(body,day,wanted)
        record.update(status='downloaded',path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=len(body),selected_rows=len(rows),issues=len(issues))
        atomic_write(DATA/'selected'/f'{day}.json',encoded({'rows':rows,'issues':issues}))
        return record,rows,issues
    except (ValueError,zipfile.BadZipFile) as exc:
        return dict(record,status='quarantined',error=str(exc)),[],[]


def main():
    DATA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    config=json.loads((ROOT/'config/five_year_v4.json').read_text());wanted=set(config['stocks'])|{'TMPV','NIFTYBEES'}
    days=set()
    for rec in json.loads((ROOT/'experiments/five_year_v4/official_daily_manifest.json').read_text()):
        if rec['symbol']!='NIFTY 50':continue
        if rec['status']!='downloaded' or sha(ROOT/rec['path'])!=rec['sha256']:raise ValueError('Calendar source changed')
        days.update(datetime.strptime(r['HistoricalDate'],'%d %b %Y').strftime('%Y-%m-%d') for r in json.loads((ROOT/rec['path']).read_bytes()))
    atomic_write(OUT/'plan.json',encoded({'days':sorted(days),'wanted':sorted(wanted),'price_basis':'unadjusted official exchange traded prices','calendar_source':'Official NIFTY 50 daily dates; missing stock dates are reviewed, not filled.','requests':len(days),'format_change':'2024-07-08','concurrency':3,'minimum_request_spacing_seconds':.5}))
    log=OUT/'manifest.json';records=json.loads(log.read_text()) if log.exists() else {}
    all_rows=[];all_issues=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(fetch,day,wanted,records.get(day,{})):day for day in sorted(days)}
        for i,future in enumerate(as_completed(futures),1):
            day=futures[future]
            try:record,rows,issues=future.result()
            except RuntimeError:
                for f in futures:f.cancel()
                raise
            records[day]=record;all_rows.extend(rows);all_issues.extend(issues)
            atomic_write(log,encoded(records))
            if i%50==0 or record['status']!='downloaded':print(f'{i}/{len(days)} {day}: {record["status"]}',flush=True)
    if any(records[d]['status']!='downloaded' for d in days):
        print('Collection incomplete; inspect manifest before reconciliation.',flush=True);return
    frame=pd.DataFrame(all_rows).sort_values(['symbol','day']);frame.to_csv(DATA/'raw_price_panel.csv.gz',index=False,compression={'method':'gzip','compresslevel':1,'mtime':0})
    pd.DataFrame(all_issues).to_csv(OUT/'row_issues.csv',index=False)
    atomic_write(OUT/'acquisition_summary.json',encoded({'dates':len(days),'rows':len(frame),'symbols':sorted(frame.symbol.unique()),'invalid_selected_rows':len(all_issues),'panel_sha256':sha(DATA/'raw_price_panel.csv.gz'),'price_basis':'unadjusted','deployment':'disabled'}))
    print('Acquisition complete:',len(days),'dates;',len(frame),'rows',flush=True)


if __name__=='__main__':main()
