"""Cross-check broker index history against official Nifty daily reports."""
import csv
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib import request
import numpy as np
from context_sources import ROOT, STAGE, RECORDS


def collect(job):
    symbol, year = job
    display = symbol.replace('NIFTY FIN SERVICE','NIFTY FINANCIAL SERVICES').title()
    url = 'https://www.niftyindices.com/BackPage/getHistoricaldatatabletoString'
    cinfo = {'name':symbol,'startDate':f'01/01/{year}','endDate':f'12/31/{year}','indexName':display}
    rec = {'symbol':symbol,'year':year,'url':url,'request':cinfo}
    try:
        req = request.Request(url,data=json.dumps({'cinfo':json.dumps(cinfo)}).encode(),headers={
            'User-Agent':'Mozilla/5.0','Content-Type':'application/json; charset=utf-8',
            'Referer':'https://www.niftyindices.com/reports/historical-data'})
        with request.urlopen(req,timeout=20) as response:
            body = response.read()
        values = json.loads(body)
        if not isinstance(values,list) or len(values)<200:
            raise ValueError('Missing daily records.')
        for row in values:
            if datetime.strptime(row['HistoricalDate'],'%d %b %Y').year != year:
                raise ValueError('Wrong period.')
        digest = hashlib.sha256(body).hexdigest()
        path = STAGE/'official_daily'/f'{symbol.replace(" ","_")}_{year}_{digest[:16]}.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(body)
        rec.update(status='downloaded',rows=len(values),sha256=digest,path=path.relative_to(ROOT).as_posix())
    except Exception as exc:
        rec.update(status='unavailable',error=type(exc).__name__)
    time.sleep(.3)
    return rec


def main():
    names = [r['tradingsymbol'] for r in json.loads((RECORDS/'index_instruments.json').read_text())['indices']]
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(collect,[(symbol,year) for symbol in names for year in range(2021,2025)]))
    (RECORDS/'official_daily_manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    comparisons = []
    summary = {}
    kite = json.loads((RECORDS/'kite_manifest.json').read_text())['requests']
    for symbol in names:
        by_day = {}
        for rec in records:
            if rec['symbol']==symbol and rec['status']=='downloaded':
                for row in json.loads((ROOT/rec['path']).read_bytes()):
                    day = datetime.strptime(row['HistoricalDate'],'%d %b %Y').strftime('%Y-%m-%d')
                    by_day[day] = row
        bars = {}
        for rec in kite.values():
            if rec['symbol'] != symbol:
                continue
            for stamp,op,hi,lo,cl,vol in json.loads((ROOT/rec['path']).read_bytes())['data']['candles']:
                if not '09:15' <= stamp[11:16] <= '15:29':
                    continue
                day = stamp[:10]
                if day not in bars:
                    bars[day] = {'high':hi,'low':lo,'close':cl}
                else:
                    bars[day]['high']=max(bars[day]['high'],hi)
                    bars[day]['low']=min(bars[day]['low'],lo)
                    bars[day]['close']=cl
        differences = []
        for day in sorted(by_day.keys() & bars.keys()):
            row,bar = by_day[day],bars[day]
            high_diff = (bar['high']/float(row['HIGH'])-1)*10000
            low_diff = (bar['low']/float(row['LOW'])-1)*10000
            comparisons.append({'symbol':symbol,'day':day,'high_difference_bps':high_diff,'low_difference_bps':low_diff,
                'last_quote_minus_daily_close_bps':(bar['close']/float(row['CLOSE'])-1)*10000})
            differences.append(max(abs(high_diff),abs(low_diff)))
        summary[symbol] = {'official_daily_dates':len(by_day),'broker_regular_dates':len(bars),
            'matched_dates':len(differences),'official_dates_without_regular_broker_bars':sorted(by_day.keys()-bars.keys()),
            'broker_dates_not_in_official_daily':sorted(bars.keys()-by_day.keys()),
            'high_low_max_abs_difference_bps':max(differences) if differences else None,
            'high_low_p95_abs_difference_bps':float(np.quantile(differences,.95)) if differences else None,
            'high_low_dates_over_10bps':sum(x>10 for x in differences)}
    if comparisons:
        with (RECORDS/'official_daily_comparison.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(comparisons[0]));writer.writeheader();writer.writerows(comparisons)
    result = {'downloaded_year_series':sum(r['status']=='downloaded' for r in records),'requested_year_series':len(records),
        'series':summary,'interpretation':'Independent provider-download/calendar comparison; daily final close need not equal final minute quote. High/low differences require review, not automatic correction. No strategy tuning.'}
    (RECORDS/'official_daily_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    main()
