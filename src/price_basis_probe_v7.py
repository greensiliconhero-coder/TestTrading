"""Small official-exchange raw-price probe; never silently undo vendor adjustments."""
import io
import json
import zipfile
from datetime import datetime,timezone
from urllib import request,error
import pandas as pd
from research_v1 import ROOT,sha
from kite_repair import atomic_write,encoded


def main():
    folder=ROOT/'data/backtest_validation_v7/price_probe';folder.mkdir(parents=True,exist_ok=True)
    jobs=[('TATASTEEL','2022-07-27'),('TATASTEEL','2022-07-28'),('NESTLEIND','2024-01-04'),('NESTLEIND','2024-01-05')]
    records=[];comparison=[]
    for symbol,day in jobs:
        d=datetime.strptime(day,'%Y-%m-%d');name=f'cm{d:%d}{d:%b}{d:%Y}bhav.csv'.replace(d.strftime('%b'),d.strftime('%b').upper())
        url=f'https://nsearchives.nseindia.com/content/historical/EQUITIES/{d:%Y}/{d:%b}/{name}.zip'.replace('/'+d.strftime('%b')+'/', '/'+d.strftime('%b').upper()+'/')
        rec={'symbol':symbol,'day':day,'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat()}
        try:
            with request.urlopen(request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as response:body=response.read()
            path=folder/(name+'.zip');atomic_write(path,body)
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                if name not in z.namelist():raise ValueError('Unexpected exchange archive')
                f=pd.read_csv(io.BytesIO(z.read(name)))
            match=f.loc[(f.SYMBOL==symbol)&(f.SERIES=='EQ')]
            if len(match)!=1:raise ValueError('Ambiguous exchange symbol')
            row=match.iloc[0]
            if pd.to_datetime(row.TIMESTAMP).strftime('%Y-%m-%d')!=day:raise ValueError('Wrong exchange date')
            source=ROOT/f'data/five_year_processing_v4/canonical/stock/day/{symbol}_{d:%Y}.csv.gz'
            broker=pd.read_csv(source);broker=broker.loc[broker.date.str[:10]==day]
            if len(broker)!=1:raise ValueError('Missing broker overlap')
            b=broker.iloc[0]
            comparison.append({'symbol':symbol,'day':day,'exchange_close':float(row.CLOSE),'kite_snapshot_close':float(b.close),'exchange_over_kite_close':float(row.CLOSE/b.close),'exchange_volume':int(row.TOTTRDQTY),'kite_volume':float(b.volume),'exchange_source_sha256':sha(path),'kite_source_sha256':sha(source)})
            rec.update(status='downloaded',path=path.relative_to(ROOT).as_posix(),sha256=sha(path))
        except (OSError,ValueError,error.URLError,zipfile.BadZipFile) as exc:
            rec.update(status='unavailable',error_type=type(exc).__name__)
        records.append(rec)
    out=ROOT/'experiments/backtest_validation_v7'
    atomic_write(out/'price_probe_manifest.json',encoded(records))
    atomic_write(out/'price_basis_comparison.json',encoded({'comparisons':comparison,'interpretation':'Official traded-price sample versus current adjusted vendor snapshot. Observed ratios are diagnostics, not a complete verified adjustment history or authorization to rescale all records.'}))
    print(json.dumps(comparison,indent=2),flush=True)


if __name__=='__main__':main()
