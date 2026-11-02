"""Research cash ledger. Requires explicit raw-price basis and verified action inputs."""
import copy
import math
from fractions import Fraction
from delivery_v6 import fees


class Ledger:
    def __init__(self, cash, fee_config, settlement_lag=1, price_basis='unadjusted',slippage_bps=0,fee_calculator=fees):
        if price_basis!='unadjusted':raise ValueError('Action accounting requires verified unadjusted prices.')
        if not math.isfinite(cash) or cash<0 or type(settlement_lag) is not int or settlement_lag<0:raise ValueError('Invalid initial ledger.')
        self.cash=float(cash);self.fee_config=dict(fee_config);self.lag=settlement_lag
        if not math.isfinite(slippage_bps) or not 0<=slippage_bps<10000:raise ValueError('Invalid slippage.')
        self.slippage=slippage_bps/10000;self.fee_calculator=fee_calculator
        self.positions={};self.receivables=[];self.trades=[];self.history=[];self.last_step=-1

    def equity(self,prices):
        for symbol,qty in self.positions.items():
            if qty and (symbol not in prices or not math.isfinite(prices[symbol]) or prices[symbol]<=0):raise ValueError('Missing/invalid held-asset price: '+symbol)
        return self.cash+sum(r['amount'] for r in self.receivables)+sum(q*prices[s] for s,q in self.positions.items() if q)

    def _credit(self,amount,due,step,kind,symbol):
        if due<=step:self.cash+=amount
        else:self.receivables.append({'amount':amount,'due':due,'kind':kind,'symbol':symbol})

    def step(self,step,prices,targets=None,signal_step=None,actions=()):
        # All validation and calculations occur on a copy: rejected events do not
        # partly mutate cash or entitlements and cannot be accidentally retried twice.
        trial=copy.deepcopy(self)
        result=trial._step(step,prices,targets,signal_step,actions)
        self.__dict__.update(trial.__dict__)
        return result

    def _step(self,step,prices,targets,signal_step,actions):
        if type(step) is not int or step<=self.last_step:raise ValueError('Session steps must increase.')
        if targets is not None and (type(signal_step) is not int or signal_step>=step):raise ValueError('Signal must precede execution.')
        if targets is not None and any(type(q) is not int or q<0 for q in targets.values()):raise ValueError('Targets require nonnegative whole units.')
        if any(not math.isfinite(p) or p<=0 for p in prices.values()):raise ValueError('Invalid price.')
        # Check held marks before settling or processing actions.
        self.equity(prices)
        pending=[]
        for rec in self.receivables:
            if rec['due']<=step:self.cash+=rec['amount']
            else:pending.append(rec)
        self.receivables=pending
        if len({e['symbol'] for e in actions})!=len(actions):raise ValueError('Multiple same-symbol actions require verified combined ordering.')
        for event in actions:
            if event.get('verified') is not True or not event.get('source') or event.get('ex_step')!=step:raise ValueError('Action evidence or ex-session missing.')
            symbol=event['symbol'];qty=self.positions.get(symbol,0)
            if event['kind'] in {'split','bonus'}:
                if type(event.get('numerator')) is not int or type(event.get('denominator')) is not int or min(event['numerator'],event['denominator'])<=0:raise ValueError('Invalid action factor.')
                entitlement=Fraction(qty*event['numerator'],event['denominator'])
                if entitlement.denominator!=1:raise ValueError('Fractional action entitlement needs explicit processing.')
                if qty:self.positions[symbol]=int(entitlement)
            elif event['kind']=='dividend':
                amount=event.get('per_share');due=event.get('payment_step')
                if not isinstance(amount,(float,int)) or not math.isfinite(amount) or amount<0 or type(due) is not int or due<step:raise ValueError('Dividend amount/payment session missing.')
                if qty:self._credit(qty*amount,due,step,'dividend',symbol)
            else:raise ValueError('Unsupported action requires reconciliation: '+event['kind'])
        if targets is not None:
            symbols=sorted(set(self.positions)|set(targets))
            for s in symbols:
                if s not in prices:raise ValueError('Missing execution price: '+s)
            for side in ['sell','buy']:
                for s in symbols:
                    held=self.positions.get(s,0);desired=targets.get(s,0)
                    quantity=max(held-desired,0) if side=='sell' else max(desired-held,0)
                    if not quantity:continue
                    price=prices[s]*(1+self.slippage if side=='buy' else 1-self.slippage)
                    if side=='buy':
                        quantity=min(quantity,int(self.cash/price))
                        while quantity and quantity*price+self.fee_calculator(quantity*price,side,self.fee_config)>self.cash:quantity-=1
                    if not quantity:continue
                    notional=quantity*price;charge=self.fee_calculator(notional,side,self.fee_config)
                    if side=='sell':
                        # Fees incurred now; net proceeds settle after configured delay.
                        if charge>notional:raise ValueError('Fees exceed sale proceeds; explicit cash debit policy needed.')
                        self.positions[s]=held-quantity
                        self._credit(notional-charge,step+self.lag,step,'sale',s)
                    else:
                        self.cash-=notional+charge;self.positions[s]=held+quantity
                    self.trades.append({'step':step,'symbol':s,'side':side,'quantity':quantity,'price':price,'notional':notional,'fees':charge})
        self.positions={s:q for s,q in self.positions.items() if q}
        if self.cash < -1e-8:raise ValueError('Negative settled cash.')
        row={'step':step,'cash':self.cash,'receivables':sum(r['amount'] for r in self.receivables),'positions':dict(self.positions),'equity':self.equity(prices)}
        self.history.append(row);self.last_step=step
        return row


def purged_training_mask(signal_steps,exit_steps,validation_start):
    return (signal_steps<validation_start)&(exit_steps<validation_start)


def market_data_gate(manifest):
    """Separate evidence gate; engineering tests alone cannot certify market inputs."""
    reasons=[]
    if manifest.get('price_basis')!='unadjusted':reasons.append('Verified unadjusted execution prices required.')
    for field in ['execution_prices_verified','action_factors_verified','dividend_payment_dates_verified','historical_fee_schedule_verified','settlement_calendar_verified']:
        if manifest.get(field) is not True:reasons.append(field+' is not verified.')
    return {'passed':not reasons,'reasons':reasons}
