import copy,sys,unittest,io,zipfile
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from causal_universe_v10 import Selector,parse
from entitlement_ledger_v10 import EntitlementLedger

class CausalTests(unittest.TestCase):
    def archive(self,text):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('prices.csv',text)
        return b.getvalue()
    def test_turnover_units_and_both_source_formats(self):
        legacy='SYMBOL,SERIES,ISIN,TIMESTAMP,OPEN,HIGH,LOW,CLOSE,TOTTRDQTY,TOTTRDVAL\nA,EQ,INE0001,01-Jan-2021,100,110,90,105,10,1000\n'
        modern='TckrSymb,SctySrs,ISIN,TradDt,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol,TtlTrfVal\nA,EQ,INE0001,2021-01-01,100,110,90,105,10,1000\n'
        a,issues=parse(self.archive(legacy),'2021-01-01');b,other=parse(self.archive(modern),'2021-01-01')
        pd.testing.assert_frame_equal(a,b);self.assertTrue(issues.empty and other.empty)
        invalid,bad=parse(self.archive(legacy.replace(',1000\n',',100000\n')),'2021-01-01')
        self.assertTrue(invalid.empty);self.assertEqual(len(bad),1)
    def frame(self,t,value=100):return pd.DataFrame([{'symbol':'A','isin':'INE0001','day':str(t),'traded_value':value}])
    def test_selection_requires_past_61_sessions_and_resets_on_gap(self):
        s=Selector()
        for t in range(60):self.assertEqual(s.update(self.frame(t),t),[])
        self.assertEqual(s.update(self.frame(60),60)[0]['mean_value20'],100)
        self.assertEqual(s.update(self.frame(62),62),[])
    def test_future_changes_cannot_revise_saved_membership(self):
        s=Selector()
        for t in range(61):r=s.update(self.frame(t),t)
        frozen=copy.deepcopy(r)
        for t in range(61,90):s.update(self.frame(t,1e12),t)
        self.assertEqual(r,frozen)
    def ledger(self):
        l=EntitlementLedger(1000,{},fee_calculator=lambda *a:0,settlement_lag=0)
        l.step(0,{'A':100},{'A':10},-1);return l
    def bonus(self,**kw):return dict(symbol='A',kind='bonus',verified=True,source='synthetic fixture',ex_step=1,numerator=2,denominator=1,**kw)
    def test_pending_bonus_not_sellable_but_marked(self):
        l=self.ledger();r=l.step(1,{'A':50},{},0,[self.bonus(tradable_step=3)])
        self.assertEqual(l.trades[-1]['quantity'],10);self.assertEqual(l.cash,500);self.assertEqual(r['equity'],1000)
        l.step(2,{'A':50},{},1);self.assertEqual(len(l.trades),2)
        l.step(3,{'A':50},{},2);self.assertEqual(l.cash,1000);self.assertEqual(l.pending_shares,[])
    def test_missing_tradability_rejected_atomically(self):
        l=self.ledger();before=copy.deepcopy(l.__dict__)
        with self.assertRaisesRegex(ValueError,'tradability'):l.step(1,{'A':50},actions=[self.bonus()])
        self.assertEqual(l.__dict__,before)
    def test_ex_date_buyer_does_not_receive_bonus(self):
        l=EntitlementLedger(1000,{},fee_calculator=lambda *a:0)
        l.step(1,{'A':50},{'A':10},0,[self.bonus(tradable_step=3)])
        self.assertEqual(l.pending_shares,[]);self.assertEqual(l.positions,{'A':10})

if __name__=='__main__':unittest.main()
