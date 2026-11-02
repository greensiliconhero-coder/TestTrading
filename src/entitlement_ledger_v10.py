"""Explicitly distinguish bonus entitlements from available-to-sell shares."""
from fractions import Fraction
import math
from ledger_v7 import Ledger

class EntitlementLedger(Ledger):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.pending_shares=[]

    def equity(self,prices):
        value=super().equity(prices)
        for r in self.pending_shares:
            p=prices.get(r['symbol'])
            if p is None or not math.isfinite(p) or p<=0:raise ValueError('Missing pending-entitlement mark')
            value+=r['quantity']*p
        return value

    def _step(self,step,prices,targets,signal_step,actions):
        if len({e['symbol'] for e in actions})!=len(actions):raise ValueError('Combined action ordering requires review')
        pending=[]
        for r in self.pending_shares:
            if r['tradable_step']<=step:self.positions[r['symbol']]=self.positions.get(r['symbol'],0)+r['quantity']
            else:pending.append(r)
        self.pending_shares=pending
        ordinary=[]
        for e in actions:
            if any(r['symbol']==e['symbol'] for r in pending):raise ValueError('Action on pending entitlement requires explicit ordering')
            if e['kind']!='bonus':ordinary.append(e);continue
            if e.get('verified') is not True or not e.get('source') or e.get('ex_step')!=step:raise ValueError('Missing verified bonus evidence')
            due=e.get('tradable_step')
            if type(due) is not int or due<step:raise ValueError('Verified bonus tradability session required')
            n,d=e.get('numerator'),e.get('denominator')
            if type(n) is not int or type(d) is not int or not n>d>0:raise ValueError('Invalid total-share bonus ratio')
            extra=Fraction(self.positions.get(e['symbol'],0)*(n-d),d)
            if extra.denominator!=1:raise ValueError('Fractional bonus settlement requires verification')
            if extra:
                if due==step:self.positions[e['symbol']]+=int(extra)
                else:self.pending_shares.append({'symbol':e['symbol'],'quantity':int(extra),'tradable_step':due,'source':e['source']})
        row=super()._step(step,prices,targets,signal_step,ordinary)
        row['pending_shares']=[dict(r) for r in self.pending_shares]
        return row
