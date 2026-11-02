import sys
import json
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from delivery_v6 import fees,simulate,ROOT
from benchmark_v6 import etf_fee


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads((ROOT/'config/delivery_v6.json').read_text())
        self.f=pd.DataFrame([{'symbol':'A','day':'2024-01-01','entry_day':'2024-01-02','exit_day':'2024-01-09','entry_open':100.,'exit_open':110.,'ridge':1}])

    def test_stock_and_etf_fee_amounts(self):
        self.assertAlmostEqual(fees(10000,'buy',self.c),11.87406)
        self.assertAlmostEqual(fees(10000,'sell',self.c),25.71406)
        self.assertAlmostEqual(etf_fee(10000,'buy',self.c),1.87406)
        self.assertAlmostEqual(etf_fee(10000,'sell',self.c),15.81406)

    def test_whole_shares_and_cash_conservation(self):
        result,b,t=simulate(self.f,'ridge',self.c,5)
        self.assertEqual(t.quantity.iloc[0],99)
        self.assertAlmostEqual(t.net_pnl.sum(),result['final_cash']-50000)
        self.assertAlmostEqual(t.quote_pnl.sum()-t.slippage.sum()-t.fees.sum(),t.net_pnl.sum())

    def test_unaffordable_position_preserves_cash(self):
        self.f.entry_open=60000
        result,_,_=simulate(self.f,'ridge',self.c,5)
        self.assertEqual(result['trades'],0)
        self.assertEqual(result['final_cash'],50000)

    def test_fixed_dp_fee_penalizes_smaller_sales(self):
        small=fees(1000,'sell',self.c)/1000
        large=fees(10000,'sell',self.c)/10000
        self.assertGreater(small,large)
        self.assertEqual(fees(0,'sell',self.c),0)

    def test_more_slippage_reduces_same_size_trade_profit(self):
        a,_,ta=simulate(self.f,'ridge',self.c,5)
        b,_,tb=simulate(self.f,'ridge',self.c,10)
        self.assertEqual(ta.quantity.iloc[0],tb.quantity.iloc[0])
        self.assertGreater(a['net_return'],b['net_return'])


if __name__=='__main__':unittest.main()
