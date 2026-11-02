"""Atomic verified compound split/bonus events with separately tradable bonus units."""
from fractions import Fraction
from entitlement_ledger_v10 import EntitlementLedger

class CompoundLedger(EntitlementLedger):
    def _step(self,step,prices,targets,signal_step,actions):
        if len({e['symbol'] for e in actions})!=len(actions):raise ValueError('Use one explicitly ordered compound event per symbol')
        converted=[]
        for e in actions:
            if e['kind']!='split_bonus':converted.append(e);continue
            if e.get('verified') is not True or not e.get('source') or e.get('ex_step')!=step:raise ValueError('Verified compound event evidence required')
            if e.get('ordering')!='split_then_bonus':raise ValueError('Verified compound ordering required')
            if any(r['symbol']==e['symbol'] for r in self.pending_shares):raise ValueError('Pre-existing pending shares require reconciliation')
            n,d=e.get('split_numerator'),e.get('split_denominator')
            if type(n) is not int or type(d) is not int or min(n,d)<=0:raise ValueError('Invalid split ratio')
            units=Fraction(self.positions.get(e['symbol'],0)*n,d)
            if units.denominator!=1:raise ValueError('Fractional split requires explicit policy')
            if units:self.positions[e['symbol']]=int(units)
            converted.append({**e,'kind':'bonus','numerator':e.get('bonus_numerator'),'denominator':e.get('bonus_denominator')})
        return super()._step(step,prices,targets,signal_step,converted)
