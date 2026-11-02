import sys,copy,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from compound_ledger_v11 import CompoundLedger
from action_evidence_v11 import classify

class CompoundTests(unittest.TestCase):
    def ledger(self):
        l=CompoundLedger(1000,{},fee_calculator=lambda *a:0,settlement_lag=0)
        l.step(0,{'A':100},{'A':10},-1);return l
    def event(self,**extra):
        return dict(symbol='A',kind='split_bonus',verified=True,source='synthetic verified fixture',ex_step=1,ordering='split_then_bonus',split_numerator=5,split_denominator=1,bonus_numerator=2,bonus_denominator=1,**extra)
    def test_split_then_bonus_preserves_equity_without_selling_pending_bonus(self):
        l=self.ledger();r=l.step(1,{'A':10},{},0,[self.event(tradable_step=3)])
        self.assertEqual(r['equity'],1000);self.assertEqual(l.cash,500)
        self.assertEqual(l.trades[-1]['quantity'],50);self.assertEqual(l.pending_shares[0]['quantity'],50)
        l.step(3,{'A':10},{},2);self.assertEqual(l.cash,1000)
    def test_missing_bonus_timing_rolls_back_split(self):
        l=self.ledger();before=copy.deepcopy(l.__dict__)
        with self.assertRaises(ValueError):l.step(1,{'A':10},actions=[self.event()])
        self.assertEqual(l.__dict__,before)
    def test_unverified_ordering_rejected(self):
        l=self.ledger();e=self.event(tradable_step=3);e['ordering']='unknown'
        with self.assertRaises(ValueError):l.step(1,{'A':10},actions=[e])
        self.assertEqual(l.positions,{'A':10})
    def test_future_notice_not_used_before_effective_date(self):
        row={'status':'same_symbol_different_isin','symbol':'A','day':'2022-01-01','same_symbol_quotes':[{'isin':'NEW'}]}
        notice={'kind':'split_identity','status':'archived','symbol':'A','ex_day':'2022-01-02','new_isin':'NEW'}
        r=classify(row,[notice]);self.assertEqual(r['resolution'],'identity_notice_unresolved')
        self.assertFalse(r['execution_approved'])
    def test_ambiguous_same_isin_quotes_not_promoted(self):
        row={'status':'same_isin_other_series','symbol':'A','isin':'OLD','same_isin_quotes':[{'isin':'OLD'},{'isin':'OLD'}]}
        self.assertEqual(classify(row,[])['resolution'],'ambiguous_quotes')

if __name__=='__main__':unittest.main()
