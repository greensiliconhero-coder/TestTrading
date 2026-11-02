import copy
import json
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from ledger_v7 import Ledger,purged_training_mask,market_data_gate
from research_v1 import ROOT
from delivery_v6 import fees


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'config/delivery_v6.json').read_text())
        self.zero={k:0 for k in self.config if isinstance(self.config[k],(float,int))}

    def action(self,kind,**extra):
        return dict(symbol='A',kind=kind,verified=True,source='synthetic_verified_fixture',ex_step=1,**extra)

    def test_retained_position_does_not_roundtrip(self):
        l=Ledger(50000,self.config)
        l.step(0,{'A':100},{'A':10},-1)
        first=l.cash
        l.step(1,{'A':110},{'A':10},0)
        self.assertEqual(len(l.trades),1);self.assertEqual(first,l.cash)
        self.assertAlmostEqual(l.history[-1]['equity']-l.history[0]['equity'],100)

    def test_partial_rebalance_only_trades_difference(self):
        l=Ledger(50000,self.config)
        l.step(0,{'A':100},{'A':10},-1)
        l.step(1,{'A':100},{'A':7},0)
        self.assertEqual(l.trades[-1]['quantity'],3)
        self.assertAlmostEqual(l.trades[-1]['fees'],fees(300,'sell',self.config))

    def test_unsettled_sales_cannot_fund_buys(self):
        l=Ledger(1000,self.zero,settlement_lag=1)
        l.step(0,{'A':100,'B':100},{'A':10},-1)
        row=l.step(1,{'A':100,'B':100},{'B':10},0)
        self.assertEqual(l.positions,{});self.assertEqual(row['cash'],0);self.assertEqual(row['receivables'],1000)
        l.step(2,{'B':100},{'B':10},1)
        self.assertEqual(l.positions,{'B':10});self.assertEqual(l.cash,0)

    def test_split_conserves_wealth(self):
        l=Ledger(1000,self.zero);l.step(0,{'A':100},{'A':10},-1)
        row=l.step(1,{'A':50},actions=[self.action('split',numerator=2,denominator=1)])
        self.assertEqual(l.positions['A'],20);self.assertEqual(row['equity'],1000)
        self.assertEqual(len(l.trades),1)

    def test_bonus_conserves_wealth(self):
        l=Ledger(1200,self.zero);l.step(0,{'A':100},{'A':12},-1)
        row=l.step(1,{'A':75},actions=[self.action('bonus',numerator=4,denominator=3)])
        self.assertEqual(l.positions['A'],16);self.assertEqual(row['equity'],1200)

    def test_dividend_receivable_not_spendable_until_payment(self):
        l=Ledger(1000,self.zero);l.step(0,{'A':100},{'A':10},-1)
        row=l.step(1,{'A':95},actions=[self.action('dividend',per_share=5,payment_step=3)])
        self.assertEqual(row['equity'],1000);self.assertEqual(l.cash,0);self.assertEqual(row['receivables'],50)
        l.step(2,{'A':95});self.assertEqual(l.cash,0)
        row=l.step(3,{'A':95});self.assertEqual(l.cash,50);self.assertEqual(row['receivables'],0)
        self.assertEqual(row['equity'],1000)

    def test_exdate_buy_does_not_receive_prior_entitlement(self):
        l=Ledger(1000,self.zero)
        l.step(1,{'A':95},{'A':10},0,actions=[self.action('dividend',per_share=5,payment_step=3)])
        self.assertEqual(l.receivables,[])

    def test_invalid_action_is_atomic_and_not_silently_ignored(self):
        for event in [self.action('rights'),self.action('dividend',per_share=5),self.action('split',numerator=4,denominator=3),dict(self.action('split',numerator=2,denominator=1),verified=False)]:
            l=Ledger(1000,self.zero);l.step(0,{'A':100},{'A':1},-1);before=copy.deepcopy(l.__dict__)
            with self.assertRaises(ValueError):l.step(1,{'A':100},actions=[event])
            self.assertEqual(l.__dict__,before)

    def test_adjusted_price_and_same_bar_signals_rejected(self):
        with self.assertRaises(ValueError):Ledger(1000,self.zero,price_basis='adjusted')
        l=Ledger(1000,self.zero)
        with self.assertRaises(ValueError):l.step(0,{'A':100},{'A':1},0)

    def test_missing_held_mark_rejected(self):
        l=Ledger(1000,self.zero);l.step(0,{'A':100},{'A':1},-1)
        with self.assertRaises(ValueError):l.step(1,{})

    def test_label_crossing_boundary_is_purged(self):
        signal=np.array([7,8,9,10]);exit_=np.array([9,10,11,12])
        np.testing.assert_array_equal(purged_training_mask(signal,exit_,10),[True,False,False,False])

    def test_tiny_account_never_borrows_for_fees(self):
        l=Ledger(100,self.config);l.step(0,{'A':100},{'A':1},-1)
        self.assertEqual(l.positions,{});self.assertEqual(l.cash,100)

    def test_missing_market_evidence_fails_closed(self):
        self.assertFalse(market_data_gate({})['passed'])
        self.assertFalse(market_data_gate({'price_basis':'adjusted'})['passed'])


if __name__=='__main__':unittest.main()
