import io
import json
import sys
import zipfile
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nse_raw_v8 import parse_archive,archive_url,ROOT
from nse_reconcile_v8 import expected_share_ratio
from raw_execution_v8 import replay
from ledger_v7 import Ledger


def zipped(text):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:z.writestr('fixture.csv',text)
    return b.getvalue()


class RawTests(unittest.TestCase):
    def test_both_exchange_formats_preserve_original_units(self):
        legacy='SYMBOL,SERIES,ISIN,TIMESTAMP,OPEN,HIGH,LOW,CLOSE,TOTTRDQTY\nTEST,EQ,INE000000001,04-JAN-2024,100,102,99,101,123\n'
        modern='TckrSymb,SctySrs,ISIN,TradDt,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\nTEST,EQ,INE000000001,2024-01-04,100,102,99,101,123\n'
        a,issues=parse_archive(zipped(legacy),'2024-01-04',{'TEST'})
        b,_=parse_archive(zipped(modern),'2024-01-04',{'TEST'})
        self.assertEqual(a,b);self.assertEqual(a[0]['close'],101);self.assertEqual(issues,[])
        with self.assertRaises(ValueError):parse_archive(zipped(legacy),'2024-01-05',{'TEST'})

    def test_duplicate_symbol_rejected_and_bad_ohlc_quarantined(self):
        header='SYMBOL,SERIES,ISIN,TIMESTAMP,OPEN,HIGH,LOW,CLOSE,TOTTRDQTY\n'
        row='TEST,EQ,INE000000001,04-JAN-2024,100,90,99,101,123\n'
        rows,issues=parse_archive(zipped(header+row),'2024-01-04',{'TEST'})
        self.assertEqual(rows,[]);self.assertEqual(len(issues),1)
        with self.assertRaises(ValueError):parse_archive(zipped(header+row+row),'2024-01-04',{'TEST'})

    def test_format_transition_and_share_factors(self):
        self.assertIn('cm05JUL2024',archive_url('2024-07-05'))
        self.assertIn('BhavCopy_NSE_CM',archive_url('2024-07-08'))
        self.assertAlmostEqual(expected_share_ratio('Bonus 1:3'),4/3)
        self.assertEqual(expected_share_ratio('Face Value Split - From Rs 10/- Per Share To Re 1/- Per Share'),10)
        self.assertIsNone(expected_share_ratio('Rights 6:179 @ Premium Rs 1810/-'))

    def test_slippage_affects_fills_not_held_marks(self):
        config=json.loads((ROOT/'config/delivery_v6.json').read_text());zero={k:0 for k,v in config.items() if isinstance(v,(float,int))}
        l=Ledger(1000,zero,settlement_lag=0,slippage_bps=100)
        row=l.step(0,{'A':100},{'A':5},-1)
        self.assertEqual(l.trades[0]['price'],101);self.assertEqual(row['equity'],995)
        l.step(1,{'A':100},{},0);self.assertEqual(l.cash,990)

    def test_adjacent_batches_retain_positions(self):
        calendar=pd.date_range('2024-01-01',periods=12).strftime('%Y-%m-%d').tolist()
        raw=pd.DataFrame({'day':calendar,'symbol':'A','open':100.})
        sample=pd.DataFrame([{'day':calendar[0],'entry_day':calendar[1],'exit_day':calendar[6],'symbol':'A','ridge':1},{'day':calendar[5],'entry_day':calendar[6],'exit_day':calendar[11],'symbol':'A','ridge':1}])
        config=json.loads((ROOT/'config/delivery_v6.json').read_text())
        stats,_,orders=replay(sample,'ridge',raw,calendar,set(),config,1,5)
        self.assertEqual(stats['orders'],2)
        self.assertEqual(orders.side.tolist(),['buy','sell'])
        self.assertGreater(stats['unsettled_sale_receivables'],0)
        with self.assertRaises(ValueError):replay(sample,'ridge',raw,calendar,{('A',calendar[3])},config,1,5)


if __name__=='__main__':unittest.main()
