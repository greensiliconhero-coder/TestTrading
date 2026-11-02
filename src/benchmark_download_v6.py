"""Download daily NIFTYBEES candles for passive benchmark research only."""
import getpass
import json
from datetime import date
from pathlib import Path
from kite_login import login
from kite_repair import Client, instrument_map, atomic_write, encoded
from five_year_download import ranges, validate_response
from research_v1 import ROOT, sha


def main():
    folder=ROOT/'data/delivery_v6/benchmark';folder.mkdir(parents=True,exist_ok=True)
    key=getpass.getpass('Kite API KEY (hidden): ').strip()
    secret=getpass.getpass('Kite API SECRET (hidden): ').strip()
    client=Client(key,login(key,secret));secret=None
    body=client.get('/instruments/NSE');atomic_write(folder/'instruments.csv',body)
    mapping=instrument_map(body)
    if 'NIFTYBEES' not in mapping:raise ValueError('NIFTYBEES identity unresolved.')
    token=mapping['NIFTYBEES']['instrument_token'];records=[]
    for start,end in ranges(date(2021,1,1),date(2025,12,31),'day'):
        path=folder/f'NIFTYBEES_{start}_{end}.json'
        body=client.get(f'/instruments/historical/{token}/day',{'from':f'{start} 00:00:00','to':f'{end} 23:59:59','oi':0})
        rec={'from':str(start),'to':str(end),'interval':'day','symbol':'NIFTYBEES','instrument_token':token}
        result=validate_response(body,rec);atomic_write(path,body)
        records.append(dict(rec,**result,path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
        atomic_write(folder/'manifest.json',encoded(records));print(start,end,result['rows'],flush=True)
    print('Benchmark download complete; no orders placed.',flush=True)


if __name__=='__main__':main()
